from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import RunStatus
from app.models import AgentResult, AgentRun, AgentStep


class AgentRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- runs ---------------------------------------------------------------
    def get_run(self, run_id: str) -> AgentRun | None:
        return self.db.get(AgentRun, run_id)

    def latest_run_for(self, wr_id: str) -> AgentRun | None:
        """append-only 이므로 최신 1건만 화면에 노출한다."""
        return self.db.scalars(
            select(AgentRun).where(AgentRun.work_request_id == wr_id).order_by(AgentRun.started_at.desc())
        ).first()

    def running_run_for(self, wr_id: str) -> AgentRun | None:
        return self.db.scalars(
            select(AgentRun)
            .where(AgentRun.work_request_id == wr_id, AgentRun.status == RunStatus.RUNNING)
            .order_by(AgentRun.started_at.desc())
        ).first()

    def save_run(self, run: AgentRun) -> AgentRun:
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    # --- steps / results ----------------------------------------------------
    def steps_for(self, run_id: str) -> list[AgentStep]:
        return list(
            self.db.scalars(
                select(AgentStep).where(AgentStep.run_id == run_id).order_by(AgentStep.agent_code)
            ).all()
        )

    def results_for(self, run_id: str) -> list[AgentResult]:
        return list(
            self.db.scalars(
                select(AgentResult).where(AgentResult.run_id == run_id).order_by(AgentResult.agent_code)
            ).all()
        )

    def get_result(self, result_id: str) -> AgentResult | None:
        return self.db.get(AgentResult, result_id)

    def save_result(self, result: AgentResult) -> AgentResult:
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result
