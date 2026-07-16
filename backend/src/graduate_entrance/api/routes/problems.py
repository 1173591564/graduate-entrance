import re
from datetime import date
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.core.config import get_settings
from graduate_entrance.db.session import get_session
from graduate_entrance.problems.service import (
    MAX_IMAGES_PER_PROBLEM,
    add_solution,
    confirm_problem,
    create_problem,
    get_problem,
    list_due_reviews,
    list_pending,
    list_problems,
    reopen_problem,
    review_problem,
)
from graduate_entrance.schemas.problems import (
    ProblemConfirmRequest,
    ProblemKind,
    ProblemListResponse,
    ProblemPendingResponse,
    ProblemRead,
    ReviewDueResponse,
    ReviewRequest,
    ReviewResult,
    SolutionCreateRequest,
)

router = APIRouter(tags=["problems"])
Session = Annotated[AsyncSession, Depends(get_session)]

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
IMAGE_NAME_PATTERN = re.compile(r"^[0-9a-f]{32}\.(jpg|png|webp)$")
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def _images_dir() -> Path:
    directory = get_settings().problem_images_dir
    directory.mkdir(parents=True, exist_ok=True)
    return directory


async def _save_images(images: list[UploadFile]) -> list[str]:
    if len(images) > MAX_IMAGES_PER_PROBLEM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"at most {MAX_IMAGES_PER_PROBLEM} images per problem",
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


@router.post(
    "/problems",
    response_model=ProblemRead,
    status_code=status.HTTP_201_CREATED,
)
async def submit_problem(
    session: Session,
    subject_id: Annotated[UUID | None, Form()] = None,
    kind: Annotated[ProblemKind, Form()] = "wrong",
    content_md: Annotated[str, Form()] = "",
    source_ref: Annotated[str, Form()] = "",
    my_answer_md: Annotated[str, Form()] = "",
    note: Annotated[str, Form()] = "",
    images: Annotated[list[UploadFile] | None, File()] = None,
) -> ProblemRead:
    image_names = await _save_images(images or [])
    return await create_problem(
        session,
        subject_id=subject_id,
        kind=kind,
        content_md=content_md,
        source_ref=source_ref,
        my_answer_md=my_answer_md,
        note=note,
        image_names=image_names,
    )


@router.get("/problems/pending", response_model=ProblemPendingResponse)
async def read_pending_problems(session: Session) -> ProblemPendingResponse:
    return await list_pending(session)


@router.get("/problems/reviews/due", response_model=ReviewDueResponse)
async def read_due_reviews(
    session: Session,
    as_of: Annotated[date | None, Query()] = None,
    include_drafts: Annotated[bool, Query()] = True,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ReviewDueResponse:
    return await list_due_reviews(session, as_of or date.today(), include_drafts, limit)


@router.get("/problems/images/{image_name}")
async def read_problem_image(image_name: str) -> FileResponse:
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


@router.get("/problems", response_model=ProblemListResponse)
async def read_problems(
    session: Session,
    knowledge_point_id: Annotated[UUID | None, Query(alias="kp_id")] = None,
    subject_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ProblemListResponse:
    return await list_problems(session, knowledge_point_id, subject_id, limit)


@router.get("/problems/{problem_id}", response_model=ProblemRead)
async def read_problem(problem_id: UUID, session: Session) -> ProblemRead:
    return await get_problem(session, problem_id)


@router.post("/problems/{problem_id}/confirm", response_model=ProblemRead)
async def confirm_problem_endpoint(
    problem_id: UUID,
    payload: ProblemConfirmRequest,
    session: Session,
) -> ProblemRead:
    return await confirm_problem(session, problem_id, payload)


@router.post("/problems/{problem_id}/reopen", response_model=ProblemRead)
async def reopen_problem_endpoint(problem_id: UUID, session: Session) -> ProblemRead:
    return await reopen_problem(session, problem_id)


@router.post("/problems/{problem_id}/review", response_model=ReviewResult)
async def review_problem_endpoint(
    problem_id: UUID,
    payload: ReviewRequest,
    session: Session,
    as_of: Annotated[date | None, Query()] = None,
) -> ReviewResult:
    return await review_problem(session, problem_id, payload.grade, as_of or date.today())


@router.post(
    "/problems/{problem_id}/solutions",
    response_model=ProblemRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_solution_endpoint(
    problem_id: UUID,
    payload: SolutionCreateRequest,
    session: Session,
) -> ProblemRead:
    return await add_solution(session, problem_id, payload)
