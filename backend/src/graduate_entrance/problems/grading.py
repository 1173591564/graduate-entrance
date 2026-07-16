import base64
import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.ai import client as ai_client
from graduate_entrance.core.config import Settings, get_settings
from graduate_entrance.models.syllabus import Subject
from graduate_entrance.problems.service import _load_problem
from graduate_entrance.schemas.problems import GradeResult

GRADABLE_SUBJECT_KEYWORDS = ("英语", "政治")
IMAGE_MIME_TYPES = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
JSON_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)

SYSTEM_PROMPT = (
    "你是一名 11408 考研主观题阅卷老师（英语作文/翻译、政治分析题）。"
    "根据题目和考生作答，输出严格的 JSON 对象（不要用 Markdown 代码块包裹）：\n"
    '{"score": 0 到 100 的数字（按百分制折算）,\n'
    ' "feedback_md": "判卷讲评（Markdown）：按采分点逐条说明得分与扣分原因，'
    "指出语言/逻辑/要点覆盖问题\",\n"
    ' "suggestions": ["改进建议 1", "改进建议 2"]}\n'
    "要求：评分严格贴近真实考研阅卷标准，宁紧勿松；suggestions 给 2-4 条可操作建议。"
)


def is_gradable_subject(subject_name: str | None) -> bool:
    if not subject_name:
        return False
    return any(keyword in subject_name for keyword in GRADABLE_SUBJECT_KEYWORDS)


def _image_data_url(settings: Settings, image_name: str) -> str | None:
    path = settings.problem_images_dir / image_name
    if not path.is_file():
        return None
    mime = IMAGE_MIME_TYPES.get(path.suffix.lower())
    if mime is None:
        return None
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _parse_grade_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    match = JSON_FENCE_PATTERN.match(text)
    if match:
        text = match.group(1)
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI grading returned invalid JSON",
        ) from exc
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI grading returned invalid JSON",
        )
    return data


def _normalize_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI grading returned an invalid score",
        ) from exc
    return min(max(score, 0.0), 100.0)


def _normalize_suggestions(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


async def grade_problem(
    session: AsyncSession,
    problem_id: UUID,
    answer_md: str,
    settings: Settings | None = None,
) -> GradeResult:
    settings = settings or get_settings()
    problem = await _load_problem(session, problem_id)
    subject_name: str | None = None
    if problem.subject_id is not None:
        subject = await session.get(Subject, problem.subject_id)
        subject_name = subject.name if subject is not None else None
    if not is_gradable_subject(subject_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AI 判卷仅支持英语、政治主观题",
        )
    answer = answer_md.strip() or problem.my_answer_md.strip()
    if not answer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有可判卷的作答内容",
        )
    user_content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                f"科目：{subject_name}\n\n"
                f"题目：\n{problem.content_md or '（见图片）'}\n\n"
                f"考生作答：\n{answer}"
            ),
        }
    ]
    for image_name in problem.images:
        data_url = _image_data_url(settings, image_name)
        if data_url is not None:
            user_content.append({"type": "image_url", "image_url": {"url": data_url}})
    raw = await ai_client.complete_chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        settings,
    )
    data = _parse_grade_json(raw)
    score = _normalize_score(data.get("score"))
    feedback = data.get("feedback_md")
    feedback_md = feedback.strip() if isinstance(feedback, str) else ""
    graded_at = datetime.now(UTC)
    if answer_md.strip():
        problem.my_answer_md = answer_md.strip()
    problem.ai_score = score
    problem.ai_feedback_md = feedback_md
    problem.ai_graded_at = graded_at
    await session.commit()
    return GradeResult(
        problem_id=problem.id,
        model=settings.ai_model,
        score=score,
        feedback_md=feedback_md,
        suggestions=_normalize_suggestions(data.get("suggestions")),
        graded_at=graded_at,
    )
