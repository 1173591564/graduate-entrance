from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MasteryGap(BaseModel):
    knowledge_point_id: UUID
    knowledge_point_name: str
    subject_id: UUID
    subject_name: str
    mastery: float
    target: float
    gap: float
    studied: bool


class MasteryGapResponse(BaseModel):
    generated_at: datetime
    knowledge_point_total: int
    gap_count: int
    items: list[MasteryGap]


class MasteryRecomputeResponse(BaseModel):
    recomputed: int
