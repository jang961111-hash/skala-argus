from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.schemas.agent_run import AgentRunAccepted
from app.schemas.approval import Approval, ApprovalCreate
from app.schemas.common import ErrorResponse, WorkRequestStatus
from app.schemas.work_request import (
    SubmitApprovalBody,
    WorkRequest,
    WorkRequestCreate,
    WorkRequestDetail,
    WorkRequestList,
)
from app.services.approval_service import ApprovalService, approval_to_schema
from app.services.orchestrator import AgentOrchestrator
from app.services.work_request_service import WorkRequestService

router = APIRouter(prefix="/work-requests", tags=["work-requests"])

E404 = {404: {"model": ErrorResponse}}
E409 = {409: {"model": ErrorResponse}}
E422 = {422: {"model": ErrorResponse}}


@router.get("", response_model=WorkRequestList)
def list_work_requests(
    status_: WorkRequestStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return WorkRequestService(db).list(status_.value if status_ else None, page, size)


@router.post("", response_model=WorkRequest, status_code=status.HTTP_201_CREATED, responses=E422)
def create_work_request(body: WorkRequestCreate, db: Session = Depends(get_db)):
    return WorkRequestService(db).create(body)


@router.get("/{wr_id}", response_model=WorkRequestDetail, responses=E404)
def get_work_request(wr_id: str, db: Session = Depends(get_db)):
    return WorkRequestService(db).detail(wr_id)


@router.post(
    "/{wr_id}/agent-runs",
    response_model=AgentRunAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    responses={**E404, **E409},
    summary="에이전트 실행(비동기) — 202 + run_id, steps 4개 PENDING",
)
def start_agent_run(wr_id: str, background: BackgroundTasks, db: Session = Depends(get_db)):
    orchestrator = AgentOrchestrator(db)
    run = orchestrator.create_run(wr_id)
    if get_settings().background_advance:
        background.add_task(orchestrator.advance_all_in_background, run.id)
    return {"run_id": run.id, "overall_status": run.overall_status}


@router.patch(
    "/{wr_id}/submit-approval",
    response_model=WorkRequest,
    responses={**E404, **E409, **E422},
    summary="승인 요청 — REVIEW → PENDING_APPROVAL (누락 정보 422, run 미완료 409)",
)
def submit_approval(wr_id: str, body: SubmitApprovalBody | None = None, db: Session = Depends(get_db)):
    return WorkRequestService(db).submit_approval(wr_id, body)


@router.post(
    "/{wr_id}/approvals",
    response_model=Approval,
    status_code=status.HTTP_201_CREATED,
    responses={**E404, **E409},
    summary="승인/반려/보완요청 — 체크리스트 4항목 미완료 상태의 APPROVE는 409",
)
def create_approval(wr_id: str, body: ApprovalCreate, db: Session = Depends(get_db)):
    return approval_to_schema(ApprovalService(db).decide(wr_id, body))


@router.patch("/{wr_id}/complete", response_model=WorkRequest, responses={**E404, **E409}, summary="작업 완료 보고 — APPROVED → DONE")
def complete_work_request(wr_id: str, user_id: str | None = None, db: Session = Depends(get_db)):
    return WorkRequestService(db).complete(wr_id, user_id)
