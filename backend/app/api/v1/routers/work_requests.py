from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_engineer
from app.models import User
from app.schemas.base import ErrorResponse
from app.schemas.page import Page
from app.schemas.work_request import (
    PhotoResponse,
    WorkRequestCreate,
    WorkRequestDetail,
    WorkRequestPatch,
    WorkRequestSummary,
)
from app.services.photo_service import PhotoService, photo_to_schema
from app.services.work_request_service import WorkRequestService

router = APIRouter(prefix="/work-requests", tags=["work-requests"])

E = {code: {"model": ErrorResponse} for code in (400, 401, 403, 404, 409, 413, 422)}


def _err(*codes: int) -> dict:
    return {code: E[code] for code in codes}


@router.post(
    "",
    response_model=WorkRequestDetail,
    status_code=status.HTTP_201_CREATED,
    responses=_err(400, 401, 403),
    summary="요청 등록 — draft=true 면 임시저장(검증 생략), false 면 필수값·스펙 스키마 검증",
)
def create_work_request(
    body: WorkRequestCreate,
    draft: bool | None = Query(default=None, description="쿼리로 줘도 되고 body.draft 로 줘도 된다"),
    db: Session = Depends(get_db),
    current: User = Depends(require_engineer),
):
    if draft is not None:
        body = body.model_copy(update={"draft": draft})
    service = WorkRequestService(db)
    return service.to_detail(service.create(body, current), current)


@router.get(
    "",
    response_model=Page[WorkRequestSummary],
    responses=_err(400, 401),
    summary="목록 — status 콤마 다중 지정 가능, 항목마다 서버가 계산한 nextAction 포함",
)
def list_work_requests(
    mine: bool = Query(default=False, description="true 면 토큰 사용자가 등록한 요청만"),
    status_param: str | None = Query(default=None, alias="status", description="콤마 다중 지정 (예: REJECTED,DRAFT)"),
    page: int = Query(default=0, ge=0, description="0-base"),
    size: int = Query(default=20, ge=1, le=100),
    sort: str = Query(default="createdAt,desc"),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    return WorkRequestService(db).list(
        current=current, mine=mine, status_param=status_param, page=page, size=size, sort=sort
    )


@router.get(
    "/{wr_id}",
    response_model=WorkRequestDetail,
    responses=_err(401, 403, 404),
    summary="상세 — agentRun(steps·results) + 최신 approval 1건. 안전관리자 조회 시 results[].editable 은 항상 false",
)
def get_work_request(wr_id: str, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    service = WorkRequestService(db)
    return service.to_detail(service.get_for(wr_id, current), current)


@router.patch(
    "/{wr_id}",
    response_model=WorkRequestDetail,
    responses=_err(400, 401, 403, 404, 409),
    summary="부분 수정 — PENDING·APPROVED 는 409 IMMUTABLE_STATUS",
)
def patch_work_request(
    wr_id: str,
    body: WorkRequestPatch,
    db: Session = Depends(get_db),
    current: User = Depends(require_engineer),
):
    service = WorkRequestService(db)
    return service.to_detail(service.patch(wr_id, body, current), current)


@router.patch(
    "/{wr_id}/submit-approval",
    response_model=WorkRequestDetail,
    responses=_err(401, 403, 404, 422),
    summary="승인 제출 — 3종 결과·engineerNote·A2 법령 1건 이상·상태(AI_DONE|REJECTED) 검증. 재제출도 같은 API",
)
def submit_approval(wr_id: str, db: Session = Depends(get_db), current: User = Depends(require_engineer)):
    service = WorkRequestService(db)
    return service.to_detail(service.submit_approval(wr_id, current), current)


# ------------------------------------------------------------------- photos
@router.post(
    "/{wr_id}/photos",
    response_model=list[PhotoResponse],
    status_code=status.HTTP_201_CREATED,
    responses=_err(400, 401, 403, 404, 409, 413),
    summary="사진 업로드 — multipart/form-data, 파트명 files(배열). jpg·png·webp · 파일당 10MB · 요청당 5장",
)
async def upload_photos(
    wr_id: str,
    files: list[UploadFile] = File(..., description="jpg · png · webp"),
    db: Session = Depends(get_db),
    current: User = Depends(require_engineer),
):
    uploads = [(f.filename, f.content_type, await f.read()) for f in files]
    return [photo_to_schema(p) for p in PhotoService(db).upload(wr_id, uploads, current)]


@router.get(
    "/{wr_id}/photos",
    response_model=list[PhotoResponse],
    responses=_err(401, 403, 404),
    summary="사진 목록",
)
def list_photos(wr_id: str, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return [photo_to_schema(p) for p in PhotoService(db).list(wr_id, current)]
