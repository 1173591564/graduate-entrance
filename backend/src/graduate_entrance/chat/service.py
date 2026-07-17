from __future__ import annotations

import base64
from typing import Any, cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from graduate_entrance.ai import client as ai_client
from graduate_entrance.core.config import Settings, get_settings
from graduate_entrance.models.chat import ChatConversation, ChatMessage, utc_now
from graduate_entrance.schemas.chat import (
    ChatConversationListResponse,
    ChatConversationRead,
    ChatHistoryResponse,
    ChatMessageRead,
    ChatRole,
    ChatSendResponse,
)

SYSTEM_PROMPT = (
    "你是 ChatLearning，一名 11408 考研备考智能体，擅长数学一、英语一、政治与 408 计算机基础。"
    "用中文回答，数学公式用 $...$，回答尽量简洁、直接切入重点；"
    "题目求解时给出关键步骤与思路，不要长篇堆砌。"
)
HISTORY_LIMIT = 20
TITLE_MAX_CHARS = 30
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
    reply_text = await ai_client.complete_chat(payload, settings)

    reply = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content_md=reply_text,
        images=[],
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
