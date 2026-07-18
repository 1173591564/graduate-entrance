from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ChatRole = Literal["user", "assistant"]


StepType = Literal["reasoning", "code", "output"]


class ChatStep(BaseModel):
    type: StepType
    content: str


class ChatMessageRead(BaseModel):
    id: UUID
    conversation_id: UUID
    role: ChatRole
    content_md: str
    images: list[str]
    steps: list[ChatStep]
    created_at: datetime


class ChatConversationRead(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ChatConversationListResponse(BaseModel):
    total: int
    conversations: list[ChatConversationRead]


class ChatHistoryResponse(BaseModel):
    conversation: ChatConversationRead
    messages: list[ChatMessageRead]


class ChatSendResponse(BaseModel):
    conversation: ChatConversationRead
    user_message: ChatMessageRead
    reply: ChatMessageRead
    model: str
