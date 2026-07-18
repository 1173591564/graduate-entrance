from __future__ import annotations

import base64
import json
from typing import Any, cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from graduate_entrance.ai import client as ai_client
from graduate_entrance.ai import sandbox
from graduate_entrance.core.config import Settings, get_settings
from graduate_entrance.models.chat import ChatConversation, ChatMessage, utc_now
from graduate_entrance.schemas.chat import (
    ChatConversationListResponse,
    ChatConversationRead,
    ChatHistoryResponse,
    ChatMessageRead,
    ChatRole,
    ChatSendResponse,
    ChatStep,
)

SYSTEM_PROMPT = (
    "你是 ChatLearning，一名 11408 考研备考智能体，擅长数学一、英语一、政治与 408 计算机基础。"
    "用中文回答，数学公式用 $...$，回答尽量简洁、直接切入重点；"
    "题目求解时给出关键步骤与思路，不要长篇堆砌。"
    "遇到数学一或 408 的数值计算、符号运算、算法验证类问题时，"
    "先调用 run_python 工具（可用 sympy、numpy）执行代码验算，确认结果后再作答，不要凭空口算。"
)
RUN_PYTHON_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "run_python",
        "description": (
            "在受限沙箱中执行 Python 代码进行验算，可用 sympy、numpy。"
            "无网络、无文件写入、限时执行；通过 print 输出结果。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码，用 print 输出需要的结果。",
                }
            },
            "required": ["code"],
        },
    },
}
TOOLS: list[dict[str, Any]] = [RUN_PYTHON_TOOL]
MAX_TOOL_ROUNDS = 5
HISTORY_LIMIT = 20
TITLE_MAX_CHARS = 30
STEP_MAX_CHARS = 8192
IMAGE_MIME_TYPES = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def _conversation_read(conversation: ChatConversation) -> ChatConversationRead:
    return ChatConversationRead(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def _message_read(message: ChatMessage) -> ChatMessageRead:
    return ChatMessageRead(
        id=message.id,
        conversation_id=message.conversation_id,
        role=cast(ChatRole, message.role),
        content_md=message.content_md,
        images=message.images,
        steps=[ChatStep.model_validate(step) for step in (message.steps or [])],
        created_at=message.created_at,
    )


def _image_data_url(settings: Settings, image_name: str) -> str | None:
    path = settings.chat_images_dir / image_name
    if not path.is_file():
        return None
    mime = IMAGE_MIME_TYPES.get(path.suffix.lower())
    if mime is None:
        return None
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _history_entry(message: ChatMessage) -> dict[str, Any]:
    text = message.content_md
    if message.images:
        text = f"{text}\n（该消息附带 {len(message.images)} 张图片）" if text else "（图片消息）"
    return {"role": message.role, "content": text}


def _user_entry(settings: Settings, content: str, image_names: list[str]) -> dict[str, Any]:
    parts: list[dict[str, Any]] = [{"type": "text", "text": content}]
    for name in image_names:
        data_url = _image_data_url(settings, name)
        if data_url is not None:
            parts.append({"type": "image_url", "image_url": {"url": data_url}})
    if len(parts) == 1:
        return {"role": "user", "content": content}
    return {"role": "user", "content": parts}


def _truncate_step(text: str) -> str:
    if len(text) <= STEP_MAX_CHARS:
        return text
    return text[:STEP_MAX_CHARS] + "\n…[已截断]"


def _extract_code(tool_call: dict[str, Any]) -> str | None:
    function = tool_call.get("function")
    if not isinstance(function, dict):
        return None
    arguments = function.get("arguments")
    if isinstance(arguments, dict):
        code = arguments.get("code")
        return code if isinstance(code, str) else None
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except (ValueError, TypeError):
            return None
        code = parsed.get("code") if isinstance(parsed, dict) else None
        return code if isinstance(code, str) else None
    return None


async def _run_agent(
    payload: list[dict[str, Any]],
    settings: Settings,
) -> tuple[str, list[dict[str, str]]]:
    """Drive the tool-calling loop, returning the final reply and display steps."""
    steps: list[dict[str, str]] = []
    try:
        turn = await ai_client.complete_chat_with_tools(payload, TOOLS, settings)
    except ai_client.ToolsUnsupportedError:
        reply = await ai_client.complete_chat(payload, settings)
        return reply, steps

    for _ in range(MAX_TOOL_ROUNDS):
        if turn.reasoning.strip():
            steps.append({"type": "reasoning", "content": _truncate_step(turn.reasoning)})
        if not turn.tool_calls:
            if turn.content.strip():
                return turn.content, steps
            break

        payload.append(
            {
                "role": "assistant",
                "content": turn.content,
                "tool_calls": turn.tool_calls,
            }
        )
        for tool_call in turn.tool_calls:
            code = _extract_code(tool_call)
            call_id = tool_call.get("id") or ""
            if code is None:
                output = "工具参数解析失败：缺少可执行的 code。"
            else:
                steps.append({"type": "code", "content": _truncate_step(code)})
                result = await sandbox.run_python(code)
                output = result.output
                steps.append({"type": "output", "content": _truncate_step(output)})
            payload.append(
                {"role": "tool", "tool_call_id": call_id, "content": output}
            )

        turn = await ai_client.complete_chat_with_tools(payload, TOOLS, settings)

    # Rounds exhausted or empty final content: force a plain answer.
    payload.append(
        {
            "role": "system",
            "content": "已达到验算上限，请基于以上验算结果直接给出最终回答，不要再调用工具。",
        }
    )
    reply = await ai_client.complete_chat(payload, settings)
    return reply, steps


async def _load_conversation(session: AsyncSession, conversation_id: UUID) -> ChatConversation:
    conversation = (
        await session.execute(
            select(ChatConversation)
            .options(selectinload(ChatConversation.messages))
            .where(ChatConversation.id == conversation_id)
        )
    ).scalar_one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="conversation not found",
        )
    return conversation


async def list_conversations(session: AsyncSession) -> ChatConversationListResponse:
    conversations = (
        (
            await session.execute(
                select(ChatConversation).order_by(ChatConversation.updated_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return ChatConversationListResponse(
        total=len(conversations),
        conversations=[_conversation_read(item) for item in conversations],
    )


async def get_history(session: AsyncSession, conversation_id: UUID) -> ChatHistoryResponse:
    conversation = await _load_conversation(session, conversation_id)
    return ChatHistoryResponse(
        conversation=_conversation_read(conversation),
        messages=[_message_read(message) for message in conversation.messages],
    )


async def delete_conversation(session: AsyncSession, conversation_id: UUID) -> None:
    conversation = await _load_conversation(session, conversation_id)
    await session.delete(conversation)
    await session.commit()


async def send_message(
    session: AsyncSession,
    conversation_id: UUID | None,
    content: str,
    image_names: list[str],
    settings: Settings | None = None,
) -> ChatSendResponse:
    settings = settings or get_settings()
    content = content.strip()
    if not content and not image_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message must contain text or images",
        )
    if conversation_id is None:
        conversation = ChatConversation(title=content[:TITLE_MAX_CHARS] or "图片提问")
        session.add(conversation)
        await session.flush()
        history: list[ChatMessage] = []
    else:
        conversation = await _load_conversation(session, conversation_id)
        history = list(conversation.messages)[-HISTORY_LIMIT:]

    user_message = ChatMessage(
        conversation_id=conversation.id,
        role="user",
        content_md=content,
        images=image_names,
    )
    session.add(user_message)

    payload: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    payload.extend(_history_entry(message) for message in history)
    payload.append(_user_entry(settings, content, image_names))
    reply_text, steps = await _run_agent(payload, settings)

    reply = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content_md=reply_text,
        images=[],
        steps=steps,
    )
    session.add(reply)
    conversation.updated_at = utc_now()
    await session.commit()
    await session.refresh(conversation)
    await session.refresh(user_message)
    await session.refresh(reply)
    return ChatSendResponse(
        conversation=_conversation_read(conversation),
        user_message=_message_read(user_message),
        reply=_message_read(reply),
        model=settings.ai_model,
    )
