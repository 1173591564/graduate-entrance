"""Rolling summary compression for ChatLearning conversations.

The chat payload only carries the last ``HISTORY_LIMIT`` messages verbatim.
Once a conversation grows past that window, older turns would silently drop off.
To keep long-running context, after each reply we asynchronously fold the turns
that fell out of the window (plus the previous summary) into a compact running
summary stored on the conversation. The next request injects that summary as a
system supplement so the model keeps earlier context without a huge payload.

The compression call is cheap (low reasoning effort) and best-effort: any
failure is logged and swallowed, degrading gracefully to plain truncation.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from graduate_entrance.ai.client import complete_chat, is_ai_configured
from graduate_entrance.core.config import Settings, get_settings
from graduate_entrance.db.session import session_factory
from graduate_entrance.models.chat import ChatConversation, ChatMessage

logger = logging.getLogger(__name__)

HISTORY_LIMIT = 20
SUMMARY_MAX_CHARS = 1500
MESSAGE_MAX_CHARS = 800

SUMMARY_PROMPT = (
    "你是考研 11408 学习对话的上下文压缩器。把「已有摘要」和「新增对话」合并成一份"
    "简洁的中文摘要，保留学生的关注点、已澄清的结论、遗留的疑问与个人化信息（如薄弱科目、"
    "偏好），丢弃寒暄与冗余。只输出摘要正文，不要加标题或解释，控制在 400 字以内。"
)


def _render(message: ChatMessage) -> str:
    role = "学生" if message.role == "user" else "助教"
    text = message.content_md.strip()
    if message.images:
        note = f"（附带 {len(message.images)} 张图片）"
        text = f"{text}{note}" if text else note
    return f"{role}：{text[:MESSAGE_MAX_CHARS]}"


async def summarize_conversation(
    conversation_id: UUID,
    settings: Settings | None = None,
) -> bool:
    """Fold turns that fell out of the recent window into the running summary.

    Returns ``True`` when the summary was updated, ``False`` otherwise (nothing
    to fold, AI unconfigured, or a swallowed failure).
    """
    settings = settings or get_settings()
    if not is_ai_configured(settings):
        return False
    try:
        async with session_factory() as session:
            conversation = (
                await session.execute(
                    select(ChatConversation)
                    .options(selectinload(ChatConversation.messages))
                    .where(ChatConversation.id == conversation_id)
                )
            ).scalar_one_or_none()
            if conversation is None:
                return False

            messages = list(conversation.messages)
            older = messages[:-HISTORY_LIMIT]
            if not older:
                return False

            already = 0
            if conversation.summary_upto_message_id is not None:
                for index, message in enumerate(messages):
                    if message.id == conversation.summary_upto_message_id:
                        already = index + 1
                        break
            pending = older[already:]
            if not pending:
                return False

            parts: list[str] = []
            if conversation.summary:
                parts.append(f"已有摘要：\n{conversation.summary}")
            dialogue = "\n".join(_render(message) for message in pending)
            parts.append(f"新增对话：\n{dialogue}")

            raw = await complete_chat(
                [
                    {"role": "system", "content": SUMMARY_PROMPT},
                    {"role": "user", "content": "\n\n".join(parts)},
                ],
                settings,
                reasoning_effort="low",
            )
            summary = raw.strip()
            if not summary:
                return False
            conversation.summary = summary[:SUMMARY_MAX_CHARS]
            conversation.summary_upto_message_id = older[-1].id
            await session.commit()
            return True
    except Exception:
        logger.exception("chat summary compression failed")
        return False
