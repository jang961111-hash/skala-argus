"""AgentOrchestrator — creates a run with 4 PENDING steps and advances them.

CONTRACT mock behaviour: after POST /work-requests/{id}/agent-runs all steps are
PENDING; every GET /agent-runs/{runId} completes the next step in order
SPEC → LEGAL → SAFETY_DOC → VENDOR. When all 4 are DONE the run becomes
REVIEW and the work request status becomes REVIEW.

If Settings.background_advance is true, the router instead schedules
`advance_all_in_background` with FastAPI BackgroundTasks and GET is read-only.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AgentRun, WorkRequest
from app.repositories.agent_run_repo import AgentRunRepository
from app.repositories.ids import next_run_id
from app.repositories.master_repo import MasterRepository
from app.repositories.work_request_repo import WorkRequestRepository
from app.schemas.common import AGENT_ORDER
from app.services.agents import AgentContext, get_agent
from app.services.errors import Conflict, NotFound

log = logging.getLogger("replaceflow.orchestrator")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


class AgentOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.runs = AgentRunRepository(db)
        self.work_requests = WorkRequestRepository(db)
        self.master = MasterRepository(db)
        self.settings = get_settings()

    # ------------------------------------------------------------------ create
    def create_run(self, wr_id: str) -> AgentRun:
        wr = self.work_requests.get(wr_id)
        if wr is None:
            raise NotFound(f"work request {wr_id} not found")
        if wr.status in {"APPROVED", "DONE"}:
            raise Conflict(f"work request {wr_id} is already {wr.status}; cannot re-run agents")
        latest = self.runs.latest_for(wr_id)
        if latest is not None and latest.overall_status == "RUNNING":
            raise Conflict(f"work request {wr_id} already has running run {latest.id}")

        cfgs = {c.agent_type: c for c in self.master.list_ai_configs(wr.tenant_id)}
        model_name = "mock-v1" if self.settings.ai_provider == "MOCK" else (cfgs.get("LEGAL").model_name if cfgs.get("LEGAL") else "unknown")
        prompt_version = cfgs.get("LEGAL").prompt_version if cfgs.get("LEGAL") else "replaceflow-v0.1"

        now = _now()
        run = AgentRun(
            id=next_run_id(self.db),
            work_request_id=wr.id,
            overall_status="RUNNING",
            steps_json=[
                {"agent": a.value, "status": "PENDING", "started_at": None, "completed_at": None, "result": None}
                for a in AGENT_ORDER
            ],
            summary=None,
            approval_required_by="SAFETY_MANAGER",
            model_name=model_name,
            prompt_version=prompt_version,
            created_at=now,
        )
        wr.status = "RUNNING"
        wr.updated_at = now
        self.db.add(wr)
        return self.runs.add(run)

    # ----------------------------------------------------------------- advance
    def advance(self, run_id: str) -> AgentRun:
        """Complete the next PENDING step (mock polling semantics). Idempotent once REVIEW/FAILED."""
        run = self.runs.get(run_id)
        if run is None:
            raise NotFound(f"agent run {run_id} not found")
        if run.overall_status != "RUNNING":
            return run

        steps: list[dict[str, Any]] = [dict(s) for s in run.steps_json]
        idx = next((i for i, s in enumerate(steps) if s["status"] in {"PENDING", "RUNNING"}), None)
        if idx is None:
            return self._finish(run, steps)

        step = steps[idx]
        wr = self.work_requests.get(run.work_request_id)
        ctx = AgentContext(
            db=self.db,
            run=run,
            work_request=wr,
            equipment=self.master.get_equipment(wr.equipment_id),
            part=self.master.get_part(wr.part_id),
            prior_results={s["agent"]: s["result"] for s in steps[:idx] if s.get("result")},
        )
        started = _now()
        step["status"] = "RUNNING"
        step["started_at"] = _iso(started)
        try:
            provider = None  # MOCK from settings
            if self.settings.ai_provider != "MOCK":
                # per-tenant, per-agent provider (ai_configs) overrides the global setting
                cfg = self.master.get_ai_config(wr.tenant_id, step["agent"])
                provider = cfg.provider if cfg else self.settings.ai_provider
            agent = get_agent(step["agent"], provider)
            step["result"] = agent.run(ctx)
            step["status"] = "DONE"
            step["completed_at"] = _iso(_now())
        except Exception as exc:  # noqa: BLE001 — any agent failure marks the run FAILED
            log.exception("agent %s failed", step["agent"])
            step["status"] = "FAILED"
            step["error"] = str(exc)
            step["completed_at"] = _iso(_now())
            run.steps_json = steps
            run.overall_status = "FAILED"
            run.completed_at = _now()
            return self.runs.save(run)

        run.steps_json = steps
        if all(s["status"] == "DONE" for s in steps):
            return self._finish(run, steps)
        return self.runs.save(run)

    def _finish(self, run: AgentRun, steps: list[dict[str, Any]]) -> AgentRun:
        run.steps_json = steps
        run.overall_status = "REVIEW"
        run.completed_at = _now()
        run.summary = self._summarize(steps)
        wr = self.work_requests.get(run.work_request_id)
        if wr is not None and wr.status == "RUNNING":
            wr.status = "REVIEW"
            wr.updated_at = run.completed_at
            self.db.add(wr)
        return self.runs.save(run)

    @staticmethod
    def _summarize(steps: list[dict[str, Any]]) -> str:
        results = {s["agent"]: s.get("result") or {} for s in steps}
        spec = results.get("SPEC", {})
        docs = results.get("SAFETY_DOC", {}).get("documents", [])
        missing = [m for d in docs for m in d.get("missing", [])]
        toxic_blocked = any(not a.get("allowed_for_toxic_gas", True) for a in spec.get("alternatives", []))
        parts = [
            "OEM 동일 규격 밸브 교체." if spec.get("spec_match") else "규격 불일치 — 엔지니어 확인 필요.",
            "유독가스 라인이라 호환품 불가." if toxic_blocked else "호환품 사용 가능.",
            "작업허가·위험성평가·LOTO 필수.",
            f"서류 초안 {len(docs)}건 생성, " + (f"{', '.join(missing)}만 보완 필요." if missing else "누락 항목 없음."),
        ]
        return " ".join(parts)

    # ------------------------------------------------------- background variant
    def advance_all_in_background(self, run_id: str, delay_sec: float = 2.0) -> None:
        """BackgroundTasks variant (Settings.background_advance=true): completes one step every `delay_sec`."""
        from app.db.session import SessionLocal

        for _ in AGENT_ORDER:
            time.sleep(delay_sec)
            db = SessionLocal()
            try:
                AgentOrchestrator(db).advance(run_id)
            finally:
                db.close()


def to_schema(run: AgentRun) -> dict[str, Any]:
    return {
        "run_id": run.id,
        "work_request_id": run.work_request_id,
        "overall_status": run.overall_status,
        "steps": run.steps_json,
        "summary": run.summary,
        "approval_required_by": run.approval_required_by,
        "model_name": run.model_name,
        "prompt_version": run.prompt_version,
        "created_at": run.created_at,
        "completed_at": run.completed_at,
    }
