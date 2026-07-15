from datetime import datetime

from pydantic import BaseModel


class SyllabusVersionRead(BaseModel):
    id: str
    source_name: str
    source_checksum: str
    row_count: int
    imported_at: datetime


class KnowledgePointRead(BaseModel):
    id: str
    name: str
    requirement_raw: str
    requirement_level: str
    requirement_actions: list[str]
    common_exam_style: str
    note: str
    order: int


class SectionRead(BaseModel):
    id: str
    name: str
    order: int
    knowledge_points: list[KnowledgePointRead]


class ChapterRead(BaseModel):
    id: str
    name: str
    order: int
    sections: list[SectionRead]
    knowledge_points: list[KnowledgePointRead]


class ModuleRead(BaseModel):
    id: str
    name: str
    order: int
    chapters: list[ChapterRead]


class ExamSectionRead(BaseModel):
    id: str
    name: str
    score: int | None
    duration_minutes: int | None
    description: str
    order: int


class ExamBlueprintRead(BaseModel):
    id: str
    name: str
    total_score: int | None
    duration_minutes: int | None
    description: str
    sections: list[ExamSectionRead]


class SubjectRead(BaseModel):
    id: str
    code: str
    name: str
    order: int
    modules: list[ModuleRead]
    exam_blueprints: list[ExamBlueprintRead]
    source_row_count: int
    knowledge_point_count: int


class SyllabusTreeResponse(BaseModel):
    source_row_count: int
    knowledge_point_count: int
    exam_blueprint_count: int
    versions: list[SyllabusVersionRead]
    subjects: list[SubjectRead]
