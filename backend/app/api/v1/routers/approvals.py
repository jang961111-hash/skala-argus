from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_safety_manager
from app.models import User
from app.schemas.approval import ApprovalCreate, ApprovalResponse
from app.schemas.base import ErrorResponse
from app.services.approval_service import ApprovalService, approval_to_schema

router = APIRouter(prefix="/approvals", tags=["approvals"])

E = {code: {"model": ErrorResponse} for code in (400, 401, 403, 404, 409)}


@router.post(
    "",
    response_model=ApprovalResponse,
    status_code=status.HTTP_201_CREATED,
    responses=E,
    summary="승인/거절 — 최상위 경로, body 에 workRequestId. 승인은 사유 없이, 거절은 reason 10자 이상 필수",
)
def create_approval(
    body: ApprovalCreate, db: Session = Depends(get_db), current: User = Depends(require_safety_manager)
):
    return approval_to_schema(ApprovalService(db).decide(body, current), current)
