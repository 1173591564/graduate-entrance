from __future__ import annotations

import csv
import hashlib
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.core.config import get_settings
from graduate_entrance.db.session import session_factory
from graduate_entrance.models import (
    Chapter,
    ExamBlueprint,
    ExamSection,
    KnowledgePoint,
    Section,
    Subject,
    SyllabusModule,
    SyllabusVersion,
)

SYLLABUS_NAMESPACE = uuid.UUID("4f15ba50-1f47-51b4-a97a-0ab8a8d2fd2e")
SUBJECT_ORDER = {"数学一": 1, "408": 2, "英语一": 3, "政治": 4}
REQUIRED_HEADERS = ("科目", "模块", "章", "节", "知识点", "考纲要求", "常见考法", "备注")
REQUIRED_VALUES = ("科目", "模块", "章", "知识点", "考纲要求")


@dataclass(frozen=True)
class SyllabusImportData:
    versions: list[SyllabusVersion]
    subjects: list[Subject]
    modules: list[SyllabusModule]
    chapters: list[Chapter]
    sections: list[Section]
    knowledge_points: list[KnowledgePoint]
    exam_blueprints: list[ExamBlueprint]
    exam_sections: list[ExamSection]
    source_row_count: int


@dataclass(frozen=True)
class SyllabusImportSummary:
    source_row_count: int
    subject_count: int
    module_count: int
    chapter_count: int
    section_count: int
    knowledge_point_count: int
    exam_blueprint_count: int
    exam_section_count: int


def deterministic_id(kind: str, *parts: str) -> uuid.UUID:
    normalized = "|".join(part.strip() for part in parts)
    return uuid.uuid5(SYLLABUS_NAMESPACE, f"{kind}:{normalized}")


def stable_slug(kind: str, *parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{kind}-{digest}"


def normalize_requirement_level(requirement: str) -> str:
    if "掌握" in requirement:
        return "mastery"
    if "会" in requirement:
        return "application"
    if "理解" in requirement:
        return "understanding"
    return "awareness"


def normalize_requirement_actions(requirement: str) -> list[str]:
    action_markers = [
        ("calculate", ("求", "算", "计算")),
        ("apply", ("用",)),
        ("solve", ("解",)),
        ("judge", ("判断",)),
        ("expand", ("展开",)),
        ("lookup", ("查表",)),
        ("read", ("读",)),
    ]
    return [
        action
        for action, markers in action_markers
        if any(marker in requirement for marker in markers)
    ]


def parse_total_score(text: str) -> int | None:
    after_equals = re.search(r"=(\d+)分", text)
    if after_equals is not None:
        return int(after_equals.group(1))
    scores = [int(match) for match in re.findall(r"(\d+)分", text)]
    if not scores:
        return None
    return max(scores)


def parse_duration_minutes(text: str) -> int | None:
    duration = re.search(r"(\d+)分钟", text)
    if duration is None:
        return None
    return int(duration.group(1))


def read_source_rows(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as source_file:
        reader = csv.DictReader(source_file)
        if tuple(reader.fieldnames or ()) != REQUIRED_HEADERS:
            raise ValueError(f"{path.name} has an invalid header")
        for row_number, row in enumerate(reader, start=2):
            normalized = {key: (value or "").strip() for key, value in row.items()}
            missing = [key for key in REQUIRED_VALUES if not normalized[key]]
            if missing:
                raise ValueError(
                    f"{path.name}:{row_number} is missing required values: {', '.join(missing)}"
                )
            rows.append(normalized)
    return rows


def parse_syllabus_sources(raw_dir: Path) -> SyllabusImportData:
    versions: list[SyllabusVersion] = []
    subjects: dict[str, Subject] = {}
    modules: dict[uuid.UUID, SyllabusModule] = {}
    chapters: dict[uuid.UUID, Chapter] = {}
    sections: dict[uuid.UUID, Section] = {}
    knowledge_points: list[KnowledgePoint] = []
    exam_blueprints: dict[uuid.UUID, ExamBlueprint] = {}
    exam_sections: list[ExamSection] = []
    module_order: defaultdict[str, int] = defaultdict(int)
    chapter_order: defaultdict[uuid.UUID, int] = defaultdict(int)
    section_order: defaultdict[uuid.UUID, int] = defaultdict(int)
    knowledge_order: defaultdict[uuid.UUID, int] = defaultdict(int)
    exam_section_order: defaultdict[uuid.UUID, int] = defaultdict(int)
    source_row_count = 0

    source_paths = sorted(raw_dir.glob("*.csv"))
    if not source_paths:
        raise FileNotFoundError(f"No syllabus CSV files found in {raw_dir}")

    for path in source_paths:
        file_bytes = path.read_bytes()
        checksum = hashlib.sha256(file_bytes).hexdigest()
        rows = read_source_rows(path)

        version_id = deterministic_id("syllabus-version", path.name, checksum)
        versions.append(
            SyllabusVersion(
                id=version_id,
                source_name=path.name,
                source_checksum=checksum,
                row_count=len(rows),
                imported_at=datetime.now(UTC),
            )
        )
        source_row_count += len(rows)

        for row in rows:
            subject_name = row["科目"]
            subject = subjects.get(subject_name)
            if subject is None:
                subject = Subject(
                    id=deterministic_id("subject", subject_name),
                    code=subject_name,
                    name=subject_name,
                    order=SUBJECT_ORDER.get(subject_name, len(SUBJECT_ORDER) + len(subjects) + 1),
                )
                subjects[subject_name] = subject

            module_name = row["模块"]
            if module_name == "考试形式":
                blueprint_id = deterministic_id("exam-blueprint", subject_name, row["章"])
                blueprint = exam_blueprints.get(blueprint_id)
                combined_text = " ".join([row["知识点"], row["常见考法"], row["备注"]])
                if blueprint is None:
                    blueprint = ExamBlueprint(
                        id=blueprint_id,
                        subject_id=subject.id,
                        syllabus_version_id=version_id,
                        name=row["章"],
                        slug=stable_slug("exam-blueprint", subject_name, row["章"]),
                        total_score=parse_total_score(combined_text),
                        duration_minutes=parse_duration_minutes(combined_text),
                        description=row["备注"],
                    )
                    exam_blueprints[blueprint_id] = blueprint
                exam_section_order[blueprint_id] += 1
                exam_sections.append(
                    ExamSection(
                        id=deterministic_id("exam-section", subject_name, row["章"], row["知识点"]),
                        blueprint_id=blueprint.id,
                        name=row["知识点"],
                        score=parse_total_score(row["知识点"]),
                        duration_minutes=parse_duration_minutes(combined_text),
                        description=row["常见考法"] or row["备注"],
                        order=exam_section_order[blueprint_id],
                    )
                )
                continue

            module_id = deterministic_id("module", subject_name, module_name)
            if module_id not in modules:
                module_order[subject_name] += 1
                modules[module_id] = SyllabusModule(
                    id=module_id,
                    subject_id=subject.id,
                    name=module_name,
                    slug=stable_slug("module", subject_name, module_name),
                    order=module_order[subject_name],
                )

            chapter_name = row["章"]
            chapter_id = deterministic_id("chapter", subject_name, module_name, chapter_name)
            if chapter_id not in chapters:
                chapter_order[module_id] += 1
                chapters[chapter_id] = Chapter(
                    id=chapter_id,
                    module_id=module_id,
                    name=chapter_name,
                    slug=stable_slug("chapter", subject_name, module_name, chapter_name),
                    order=chapter_order[module_id],
                )

            section_id: uuid.UUID | None = None
            section_name = row["节"]
            if section_name:
                section_id = deterministic_id(
                    "section", subject_name, module_name, chapter_name, section_name
                )
                if section_id not in sections:
                    section_order[chapter_id] += 1
                    sections[section_id] = Section(
                        id=section_id,
                        chapter_id=chapter_id,
                        name=section_name,
                        slug=stable_slug(
                            "section", subject_name, module_name, chapter_name, section_name
                        ),
                        order=section_order[chapter_id],
                    )

            knowledge_order[chapter_id] += 1
            requirement_raw = row["考纲要求"]
            knowledge_points.append(
                KnowledgePoint(
                    id=deterministic_id(
                        "knowledge-point",
                        subject_name,
                        module_name,
                        chapter_name,
                        section_name,
                        row["知识点"],
                    ),
                    chapter_id=chapter_id,
                    section_id=section_id,
                    syllabus_version_id=version_id,
                    name=row["知识点"],
                    slug=stable_slug(
                        "knowledge-point",
                        subject_name,
                        module_name,
                        chapter_name,
                        section_name,
                        row["知识点"],
                    ),
                    requirement_raw=requirement_raw,
                    requirement_level=normalize_requirement_level(requirement_raw),
                    requirement_actions=normalize_requirement_actions(requirement_raw),
                    common_exam_style=row["常见考法"],
                    note=row["备注"],
                    weight=None,
                    est_minutes=None,
                    order=knowledge_order[chapter_id],
                )
            )

    return SyllabusImportData(
        versions=versions,
        subjects=sorted(subjects.values(), key=lambda subject: subject.order),
        modules=list(modules.values()),
        chapters=list(chapters.values()),
        sections=list(sections.values()),
        knowledge_points=knowledge_points,
        exam_blueprints=list(exam_blueprints.values()),
        exam_sections=exam_sections,
        source_row_count=source_row_count,
    )


async def import_syllabus(session: AsyncSession, raw_dir: Path) -> SyllabusImportSummary:
    data = parse_syllabus_sources(raw_dir)
    for version in data.versions:
        await session.merge(version)
    for subject in data.subjects:
        await session.merge(subject)
    for module in data.modules:
        await session.merge(module)
    for chapter in data.chapters:
        await session.merge(chapter)
    for section in data.sections:
        await session.merge(section)
    for knowledge_point in data.knowledge_points:
        await session.merge(knowledge_point)
    for blueprint in data.exam_blueprints:
        await session.merge(blueprint)
    for exam_section in data.exam_sections:
        await session.merge(exam_section)
    await session.commit()
    return SyllabusImportSummary(
        source_row_count=data.source_row_count,
        subject_count=len(data.subjects),
        module_count=len(data.modules),
        chapter_count=len(data.chapters),
        section_count=len(data.sections),
        knowledge_point_count=len(data.knowledge_points),
        exam_blueprint_count=len(data.exam_blueprints),
        exam_section_count=len(data.exam_sections),
    )


async def import_configured_syllabus() -> SyllabusImportSummary:
    async with session_factory() as session:
        return await import_syllabus(session, get_settings().syllabus_raw_dir)


def main() -> None:
    import asyncio

    summary = asyncio.run(import_configured_syllabus())
    print(
        "Imported "
        f"{summary.source_row_count} source rows, "
        f"{summary.knowledge_point_count} knowledge points, "
        f"{summary.exam_blueprint_count} exam blueprints."
    )


if __name__ == "__main__":
    main()
