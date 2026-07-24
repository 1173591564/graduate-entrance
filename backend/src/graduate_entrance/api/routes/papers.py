import re
from datetime import date
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.core.config import get_settings
from graduate_entrance.db.session import get_session
from graduate_entrance.papers.service import (
    attach_file,
    create_annotation,
    delete_annotation,
    get_paper,
    list_annotations,
    list_papers,
    paper_stats,
    paper_today,
    read_content,
    sync_papers,
    update_annotation,
    update_status,
    upload_content,
)
from graduate_entrance.schemas.papers import (
    PaperAnnotationCreate,
    PaperAnnotationList,
    PaperAnnotationRead,
    PaperAnnotationUpdate,
    PaperContentResponse,
    PaperContentUpload,
    PaperListResponse,
    PaperRead,
    PaperStatsResponse,
    PaperStatusRequest,
    PaperStatusResult,
    PaperSyncRequest,
    PaperSyncResult,
    PaperTodayResponse,
)

router = APIRouter(tags=["papers"])
Session = Annotated[AsyncSession, Depends(get_session)]

MAX_PDF_BYTES = 50 * 1024 * 1024
STORED_NAME_PATTERN = re.compile(r"^[0-9a-f]{32}\.pdf$")


def _papers_dir() -> Path:
    directory = get_settings().papers_dir
    directory.mkdir(parents=True, exist_ok=True)
    return directory


@router.post("/papers/sync", response_model=PaperSyncResult)
async def sync_paper_pool(
    session: Session,
    payload: PaperSyncRequest,
) -> PaperSyncResult:
    return await sync_papers(session, payload.papers)


@router.get("/papers", response_model=PaperListResponse)
async def read_papers(session: Session) -> PaperListResponse:
    return await list_papers(session)


@router.get("/papers/today", response_model=PaperTodayResponse)
async def read_paper_today(
    session: Session,
    as_of: Annotated[date | None, Query()] = None,
) -> PaperTodayResponse:
    return await paper_today(session, as_of or date.today())


@router.get("/papers/stats", response_model=PaperStatsResponse)
async def read_paper_stats(session: Session) -> PaperStatsResponse:
    return await paper_stats(session)


@router.post("/papers/{paper_id}/status", response_model=PaperStatusResult)
async def set_paper_status(
    session: Session,
    paper_id: UUID,
    payload: PaperStatusRequest,
) -> PaperStatusResult:
    return await update_status(
        session, paper_id, payload.status, payload.as_of or date.today()
    )


@router.post("/papers/{paper_id}/file", response_model=PaperRead)
async def upload_paper_file(
    session: Session,
    paper_id: UUID,
    file: UploadFile,
) -> PaperRead:
    paper = await get_paper(session, paper_id)
    if (file.content_type or "") not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 PDF 文件",
        )
    data = await file.read()
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF 超过 50 MB 限制",
        )
    name = f"{paper.id.hex}.pdf"
    (_papers_dir() / name).write_bytes(data)
    return await attach_file(session, paper_id, name)


@router.get("/papers/{paper_id}/file")
async def read_paper_file(session: Session, paper_id: UUID) -> FileResponse:
    paper = await get_paper(session, paper_id)
    if paper.stored_filename is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF 未上传")
    if not STORED_NAME_PATTERN.fullmatch(paper.stored_filename):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF 未上传")
    path = _papers_dir() / paper.stored_filename
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF 未上传")
    return FileResponse(path, media_type="application/pdf", filename=f"{paper.title}.pdf")


@router.put("/papers/{paper_id}/content", response_model=PaperContentResponse)
async def put_paper_content(
    session: Session,
    paper_id: UUID,
    payload: PaperContentUpload,
) -> PaperContentResponse:
    return await upload_content(session, paper_id, payload)


@router.get("/papers/{paper_id}/content", response_model=PaperContentResponse)
async def read_paper_content(session: Session, paper_id: UUID) -> PaperContentResponse:
    return await read_content(session, paper_id)


@router.get("/papers/{paper_id}/annotations", response_model=PaperAnnotationList)
async def read_paper_annotations(
    session: Session,
    paper_id: UUID,
) -> PaperAnnotationList:
    return await list_annotations(session, paper_id)


@router.post(
    "/papers/{paper_id}/annotations",
    response_model=PaperAnnotationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_paper_annotation(
    session: Session,
    paper_id: UUID,
    payload: PaperAnnotationCreate,
) -> PaperAnnotationRead:
    return await create_annotation(session, paper_id, payload)


@router.patch(
    "/papers/annotations/{annotation_id}",
    response_model=PaperAnnotationRead,
)
async def patch_paper_annotation(
    session: Session,
    annotation_id: UUID,
    payload: PaperAnnotationUpdate,
) -> PaperAnnotationRead:
    return await update_annotation(session, annotation_id, payload)


@router.delete(
    "/papers/annotations/{annotation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_paper_annotation(session: Session, annotation_id: UUID) -> None:
    await delete_annotation(session, annotation_id)
