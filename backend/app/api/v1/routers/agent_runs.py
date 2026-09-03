from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_engineer
from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.models import User
from app.repositories.agent_repo import AgentRepository
from app.schemas.agent import AgentResultResponse, AgentResultUpdate, AgentRunCreate, AgentRunResponse
from app.schemas.base import ErrorResponse
from app.services.agent_service import AgentOrchestrator, result_to_schema, run_to_response
from app.services.work_request_service import WorkRequestService

router = APIRouter(prefix="/agent-runs", tags=["agent-runs"])
results_router = APIRouter(prefix="/agent-results", tags=["agent-runs"])

E = {code: {"model": ErrorResponse} for code in (400, 401, 403, 404, 409)}


def _err(*codes: int) -> dict:
    return {code: E[code] for code in codes}


@router.post(
    "",
    response_model=AgentRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=_err(400, 401, 403, 404, 409),
    summary="AI 실행 — body 는 {workRequestId} 뿐. 서버가 요청 전체 스냅샷을 구성해 에이전트에 넘긴다",
)
def create_agent_run(
    body: AgentRunCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    current: User = Depends(require_engineer),
):
    orchestrator = AgentOrchestrator(db)
    run = orchestrator.create_run(body.work_request_id, current)
    if get_settings().background_advance:
        background.add_task(orchestrator.advance_all_in_background, run.id)
    return run_to_response(db, run)


@router.get(
    "/{run_id}",
    response_model=AgentRunResponse,
    responses=_err(401, 403, 404),
    summary="폴링 — steps + allDone + pollIntervalMs. Mock 은 호출마다 다음 step 하나가 DONE (A1→A2→A3)",
)
def get_agent_run(run_id: str, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    repo = AgentRepository(db)
    run = repo.get_run(run_id)
    if run is None:
        raise AppError(ErrorCode.AGENT_RUN_NOT_FOUND, "AI 실행 정보를 찾을 수 없습니다")
    # 소유자·역할 게이트는 대상 work_request 기준으로 건다
    WorkRequestService(db).get_for(run.work_request_id, current)
    if not get_settings().background_advance:
        run = AgentOrchestrator(db).advance(run_id)
    return run_to_response(db, run)


@results_router.patch(
    "/{result_id}",
    response_model=AgentResultResponse,
    responses=_err(400, 401, 403, 404, 409),
    summary="결과 편집 — 전체 치환. 배열에 없는 id 는 삭제, id 없는 항목은 신규 추가(서버 채번)",
)
def patch_agent_result(
    result_id: str,
    body: AgentResultUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_engineer),
):
    result = AgentOrchestrator(db).edit_result(result_id, body, current)
    return result_to_schema(result, editable=True)
