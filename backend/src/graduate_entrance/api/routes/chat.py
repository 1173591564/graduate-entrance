import re
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.chat.service import (
    delete_conversation,
    get_history,
    list_conversations,
    send_message,
)
from graduate_entrance.core.config import get_settings
from graduate_entrance.db.session import get_session
from graduate_entrance.schemas.chat import (
    ChatConversationListResponse,
    ChatHistoryResponse,
    ChatSendResponse,
)

router = APIRouter(tags=["chat"])
Session = Annotated[AsyncSession, Depends(get_session)]

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
IMAGE_NAME_PATTERN = re.compile(r"^[0-9a-f]{32}\.(jpg|png|webp)$")
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGES_PER_MESSAGE = 4


def _images_dir() -> Path:
    directory = get_settings().chat_images_dir
    directory.mkdir(parents=True, exist_ok=True)
    return directory


async def _save_images(images: list[UploadFile]) -> list[str]:
    if len(images) > MAX_IMAGES_PER_MESSAGE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"at most {MAX_IMAGES_PER_MESSAGE} images per message",
        )
    directory = _images_dir()
    names: list[str] = []
    for image in images:
        extension = ALLOWED_IMAGE_TYPES.get(image.content_type or "")
        if extension is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="unsupported image type; use JPEG, PNG, or WebP",
            )
        data = await image.read()
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="image exceeds 10 MB limit",
            )
        name = f"{uuid4().hex}{extension}"
        (directory / name).write_bytes(data)
        names.append(name)
    return names


@router.get("/chat/conversations", response_model=ChatConversationListResponse)
async def read_conversations(session: Session) -> ChatConversationListResponse:
    return await list_conversations(session)


@router.get("/chat/conversations/{conversation_id}", response_model=ChatHistoryResponse)
async def read_conversation(
    session: Session,
    conversation_id: UUID,
) -> ChatHistoryResponse:
    return await get_history(session, conversation_id)


@router.delete(
    "/chat/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_conversation(session: Session, conversation_id: UUID) -> None:
    await delete_conversation(session, conversation_id)


@router.post("/chat/messages", response_model=ChatSendResponse)
async def send_chat_message(
    session: Session,
    conversation_id: Annotated[UUID | None, Form()] = None,
    content: Annotated[str, Form()] = "",
    images: Annotated[list[UploadFile] | None, File()] = None,
) -> ChatSendResponse:
    image_names = await _save_images(images or [])
    return await send_message(session, conversation_id, content, image_names)


@router.get("/chat/images/{image_name}")
async def read_chat_image(image_name: str) -> FileResponse:
    if not IMAGE_NAME_PATTERN.fullmatch(image_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="image not found",
        )
    path = _images_dir() / image_name
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="image not found",
        )
    return FileResponse(path)
