import base64
import json
import re
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.ai import client as ai_client
from graduate_entrance.core.config import Settings, get_settings
from graduate_entrance.models.syllabus import Chapter, KnowledgePoint, Subject, SyllabusModule
from graduate_entrance.problems.service import _load_problem
from graduate_entrance.schemas.problems import (
    ExtractedKnowledgePoint,
    ExtractedSolution,
    ProblemExtractionResult,
)

MAX_SUGGESTED_KNOWLEDGE_POINTS = 3
IMAGE_MIME_TYPES = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
JSON_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)

SYSTEM_PROMPT = (
    "你是一名 11408 考研备考助手。根据题目图片和/或题面文本，输出严格的 JSON 对象"
    "（不要用 Markdown 代码块包裹），字段如下：\n"
    '{"content_md": "完整题面（Markdown，数学公式用 $...$）",\n'
    ' "knowledge_points": [{"knowledge_point_id": "候选清单中的 id", "weight": 0.6}],\n'
    ' "solution": {"content_md": "解题过程（Markdown）", "method_tag": "方法名"}}\n'
    "要求：knowledge_points 从候选清单中选出最相关的至多 "
    f"{MAX_SUGGESTED_KNOWLEDGE_POINTS} 个，按相关度降序，weight 之和为 1；"
    "无法解答时 solution 置为 null。"
)


async def _knowledge_point_catalog(
    session: AsyncSession, subject_id: UUID | None
) -> dict[UUID, str]:
    query = (
        select(KnowledgePoint.id, Subject.name, Chapter.name, KnowledgePoint.name)
        .join(Chapter, KnowledgePoint.chapter_id == Chapter.id)
        .join(SyllabusModule, Chapter.module_id == SyllabusModule.id)
        .join(Subject, SyllabusModule.subject_id == Subject.id)
        .order_by(Subject.order, KnowledgePoint.order)
    )
    if subject_id is not None:
        query = query.where(Subject.id == subject_id)
    rows = (await session.execute(query)).all()
    return {
        point_id: f"{subject_name} / {chapter_name} / {point_name}"
        for point_id, subject_name, chapter_name, point_name in rows
    }


def _image_data_url(settings: Settings, image_name: str) -> str | None:
    path = settings.problem_images_dir / image_name
    if not path.is_file():
        return None
    mime = IMAGE_MIME_TYPES.get(path.suffix.lower())
    if mime is None:
        return None
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _parse_extraction_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    match = JSON_FENCE_PATTERN.match(text)
    if match:
        text = match.group(1)
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI extraction returned invalid JSON",
        ) from exc
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI extraction returned invalid JSON",
        )
    return data


def _normalize_knowledge_points(
    entries: Any, catalog: dict[UUID, str]
) -> list[ExtractedKnowledgePoint]:
    if not isinstance(entries, list):
        return []
    picked: list[tuple[UUID, float]] = []
    seen: set[UUID] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        try:
            point_id = UUID(str(entry.get("knowledge_point_id")))
        except ValueError:
            continue
        if point_id not in catalog or point_id in seen:
            continue
        try:
            weight = float(entry.get("weight", 0.0))
        except (TypeError, ValueError):
            weight = 0.0
        seen.add(point_id)
        picked.append((point_id, max(weight, 0.0)))
        if len(picked) >= MAX_SUGGESTED_KNOWLEDGE_POINTS:
            break
    if not picked:
        return []
    total = sum(weight for _, weight in picked)
    if total <= 0:
        picked = [(point_id, 1.0) for point_id, _ in picked]
        total = float(len(picked))
    normalized = [round(weight / total, 3) for _, weight in picked]
    normalized[0] = round(1.0 - sum(normalized[1:]), 3)
    return [
        ExtractedKnowledgePoint(
            knowledge_point_id=point_id,
            knowledge_point_name=catalog[point_id],
            role="primary" if index == 0 else "secondary",
            weight=normalized[index],
        )
        for index, (point_id, _) in enumerate(picked)
    ]


def _normalize_solution(entry: Any) -> ExtractedSolution | None:
    if not isinstance(entry, dict):
        return None
    content = entry.get("content_md")
    if not isinstance(content, str) or not content.strip():
        return None
    method_tag = entry.get("method_tag")
    return ExtractedSolution(
        content_md=content.strip(),
        method_tag=method_tag.strip() if isinstance(method_tag, str) else "",
    )


async def extract_problem(
    session: AsyncSession,
    problem_id: UUID,
    settings: Settings | None = None,
) -> ProblemExtractionResult:
    settings = settings or get_settings()
    problem = await _load_problem(session, problem_id)
    catalog = await _knowledge_point_catalog(session, problem.subject_id)
    catalog_lines = "\n".join(f"{point_id} | {label}" for point_id, label in catalog.items())
    user_content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                "请识别下面的题目并输出 JSON。\n"
                f"已有题面文本（可能为空）：\n{problem.content_md or '（无）'}\n\n"
                f"知识点候选清单（id | 科目 / 章 / 知识点）：\n{catalog_lines}"
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
    data = _parse_extraction_json(raw)
    content_md = data.get("content_md")
    if not isinstance(content_md, str) or not content_md.strip():
        content_md = problem.content_md
    return ProblemExtractionResult(
        problem_id=problem.id,
        model=settings.ai_model,
        content_md=content_md.strip(),
        knowledge_points=_normalize_knowledge_points(data.get("knowledge_points"), catalog),
        solution=_normalize_solution(data.get("solution")),
    )
