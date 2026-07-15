from collections import defaultdict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from graduate_entrance.models import (
    Chapter,
    ExamBlueprint,
    KnowledgePoint,
    Section,
    Subject,
    SyllabusModule,
    SyllabusVersion,
)
from graduate_entrance.schemas.syllabus import (
    ChapterRead,
    ExamBlueprintRead,
    ExamSectionRead,
    KnowledgePointRead,
    ModuleRead,
    SectionRead,
    SubjectRead,
    SyllabusTreeResponse,
    SyllabusVersionRead,
)


def read_knowledge_point(knowledge_point: KnowledgePoint) -> KnowledgePointRead:
    return KnowledgePointRead(
        id=str(knowledge_point.id),
        name=knowledge_point.name,
        requirement_raw=knowledge_point.requirement_raw,
        requirement_level=knowledge_point.requirement_level,
        requirement_actions=knowledge_point.requirement_actions,
        common_exam_style=knowledge_point.common_exam_style,
        note=knowledge_point.note,
        order=knowledge_point.order,
    )


async def get_syllabus_tree(session: AsyncSession) -> SyllabusTreeResponse:
    versions = (
        await session.scalars(select(SyllabusVersion).order_by(SyllabusVersion.source_name))
    ).all()
    subjects = (
        await session.scalars(
            select(Subject)
            .options(
                selectinload(Subject.modules)
                .selectinload(SyllabusModule.chapters)
                .selectinload(Chapter.sections)
                .selectinload(Section.knowledge_points),
                selectinload(Subject.modules)
                .selectinload(SyllabusModule.chapters)
                .selectinload(Chapter.knowledge_points),
            )
            .order_by(Subject.order)
        )
    ).all()
    exam_blueprints = (
        await session.scalars(
            select(ExamBlueprint)
            .options(selectinload(ExamBlueprint.sections))
            .order_by(ExamBlueprint.name)
        )
    ).all()
    exam_blueprints_by_subject: defaultdict[UUID, list[ExamBlueprint]] = defaultdict(list)
    for blueprint in exam_blueprints:
        exam_blueprints_by_subject[blueprint.subject_id].append(blueprint)

    source_row_count_rows = (
        await session.execute(
            select(Subject.id, func.count(KnowledgePoint.id))
            .join(Subject.modules)
            .join(SyllabusModule.chapters)
            .join(Chapter.knowledge_points)
            .group_by(Subject.id)
        )
    ).all()
    source_row_counts = {subject_id: int(count) for subject_id, count in source_row_count_rows}
    exam_row_counts = {
        subject_id: sum(len(blueprint.sections) for blueprint in blueprints)
        for subject_id, blueprints in exam_blueprints_by_subject.items()
    }

    subject_responses: list[SubjectRead] = []
    for subject in subjects:
        module_responses: list[ModuleRead] = []
        for module in subject.modules:
            chapter_responses: list[ChapterRead] = []
            for chapter in module.chapters:
                section_responses = [
                    SectionRead(
                        id=str(section.id),
                        name=section.name,
                        order=section.order,
                        knowledge_points=[
                            read_knowledge_point(knowledge_point)
                            for knowledge_point in section.knowledge_points
                        ],
                    )
                    for section in chapter.sections
                ]
                section_knowledge_point_ids = {
                    knowledge_point.id
                    for section in chapter.sections
                    for knowledge_point in section.knowledge_points
                }
                chapter_responses.append(
                    ChapterRead(
                        id=str(chapter.id),
                        name=chapter.name,
                        order=chapter.order,
                        sections=section_responses,
                        knowledge_points=[
                            read_knowledge_point(knowledge_point)
                            for knowledge_point in chapter.knowledge_points
                            if knowledge_point.id not in section_knowledge_point_ids
                        ],
                    )
                )
            module_responses.append(
                ModuleRead(
                    id=str(module.id),
                    name=module.name,
                    order=module.order,
                    chapters=chapter_responses,
                )
            )

        exam_blueprint_responses = [
            ExamBlueprintRead(
                id=str(blueprint.id),
                name=blueprint.name,
                total_score=blueprint.total_score,
                duration_minutes=blueprint.duration_minutes,
                description=blueprint.description,
                sections=[
                    ExamSectionRead(
                        id=str(section.id),
                        name=section.name,
                        score=section.score,
                        duration_minutes=section.duration_minutes,
                        description=section.description,
                        order=section.order,
                    )
                    for section in blueprint.sections
                ],
            )
            for blueprint in exam_blueprints_by_subject[subject.id]
        ]
        knowledge_point_count = int(source_row_counts.get(subject.id, 0))
        subject_responses.append(
            SubjectRead(
                id=str(subject.id),
                code=subject.code,
                name=subject.name,
                order=subject.order,
                modules=module_responses,
                exam_blueprints=exam_blueprint_responses,
                source_row_count=knowledge_point_count + exam_row_counts.get(subject.id, 0),
                knowledge_point_count=knowledge_point_count,
            )
        )

    knowledge_point_count = sum(subject.knowledge_point_count for subject in subject_responses)
    exam_blueprint_count = sum(len(subject.exam_blueprints) for subject in subject_responses)
    exam_row_count = sum(
        len(blueprint.sections)
        for subject in subject_responses
        for blueprint in subject.exam_blueprints
    )
    return SyllabusTreeResponse(
        source_row_count=knowledge_point_count + exam_row_count,
        knowledge_point_count=knowledge_point_count,
        exam_blueprint_count=exam_blueprint_count,
        versions=[
            SyllabusVersionRead(
                id=str(version.id),
                source_name=version.source_name,
                source_checksum=version.source_checksum,
                row_count=version.row_count,
                imported_at=version.imported_at,
            )
            for version in versions
        ],
        subjects=subject_responses,
    )
