from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.repositories.agent_run_repo import AgentRunRepository
from app.schemas.agent_run import AgentRun
from app.schemas.common import ErrorResponse
from app.services.errors import NotFound
from app.services.orchestrator import AgentOrchestrator, to_schema

router = APIRouter(prefix="/agent-runs", tags=["agent-runs"])


@router.get(
    "/{run_id}",
    response_model=AgentRun,
    responses={404: {"model": ErrorResponse}},
    summary="실행 상태 폴링 — Mock: 호출마다 다음 step 하나가 DONE (SPEC→LEGAL→SAFETY_DOC→VENDOR)",
)
def get_agent_run(run_id: str, db: Session = Depends(get_db)):
    if get_settings().background_advance:
        run = AgentRunRepository(db).get(run_id)
        if run is None:
            raise NotFound(f"agent run {run_id} not found")
    else:
        run = AgentOrchestrator(db).advance(run_id)
    return to_schema(run)
