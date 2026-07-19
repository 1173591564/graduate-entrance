"""Asynchronous topic tagging for ChatLearning conversations.

After an assistant reply is stored, a cheap low-effort model call labels which
subject/knowledge-point topics the exchange touched. Tags feed the learning
snapshot ("聊天高频主题") so planning and retro can see what the learner keeps
asking about. Failures are logged and swallowed — tagging must never affect
the chat flow.
"""

from __future__ import annotations

import json
import logging
from uuid import UUID

from graduate_entrance.ai.client import complete_chat, is_ai_configured
from graduate_entrance.core.config import Settings, get_settings
from graduate_entrance.db.session import session_factory
from graduate_entrance.models.chat import ChatTopicTag

logger = logging.getLogger(__name__)

MAX_TAGS = 3
MAX_INPUT_CHARS = 2000

TAGGING_PROMPT = (
    "你是考研 11408 学习记录标注器。根据一轮问答，判断学生在问哪些科目/知识点。"
    "科目只能是：数学一、408、英语一、政治。"
    '只输出 JSON 数组，例如 [{"subject": "数学一", "topic": "泰勒公式"}]，'
    "最多 3 条；闲聊或无法判断时输出 []。"
)


def _parse_tags(raw: str) -> list[tuple[str, str]]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.removeprefix("json").strip()
    try:
        data = json.loads(text)
    except ValueError:
        return []
    if not isinstance(data, list):
        return []
    tags: list[tuple[str, str]] = []
    for entry in data[:MAX_TAGS]:
        if not isinstance(entry, dict):
            continue
        subject = entry.get("subject")
        topic = entry.get("topic")
        if isinstance(subject, str) and isinstance(topic, str) and subject and topic:
            tags.append((subject[:80], topic[:160]))
    return tags


async def tag_message_topics(
    message_id: UUID,
    question: str,
    answer: str,
    settings: Settings | None = None,
) -> int:
    """Tag one Q/A exchange with subject/topic labels. Returns tags written."""
    settings = settings or get_settings()
    if not is_ai_configured(settings):
        return 0
    try:
        raw = await complete_chat(
            [
                {"role": "system", "content": TAGGING_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"问：{question[:MAX_INPUT_CHARS]}\n\n"
                        f"答：{answer[:MAX_INPUT_CHARS]}"
                    ),
                },
            ],
            settings,
            reasoning_effort="low",
        )
    except Exception:
        logger.exception("chat topic tagging failed")
        return 0
    tags = _parse_tags(raw)
    if not tags:
        return 0
    try:
        async with session_factory() as session:
            for subject, topic in tags:
                session.add(
                    ChatTopicTag(message_id=message_id, subject=subject, topic=topic)
                )
            await session.commit()
    except Exception:
        logger.exception("chat topic tag persistence failed")
        return 0
    return len(tags)
