from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, WorkRequest
from app.repositories.agent_run_repo import AgentRunRepository
from app.repositories.approval_repo import ApprovalRepository
from app.repositories.ids import next_work_request_id
from app.repositories.master_repo import MasterRepository
from app.repositories.work_request_repo import WorkRequestRepository
from app.schemas.work_request import SubmitApprovalBody, WorkRequestCreate
from app.services.approval_service import approval_to_schema
from app.services.errors import Conflict, NotFound, Unprocessable
from app.services.orchestrator import to_schema as run_to_schema


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WorkRequestService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = WorkRequestRepository(db)
        self.runs = AgentRunRepository(db)
        self.approvals = ApprovalRepository(db)
        self.master = MasterRepository(db)

    # ---------------------------------------------------------------- create
    def create(self, body: WorkRequestCreate) -> WorkRequest:
        if self.master.get_tenant(body.tenant_id) is None:
            raise Unprocessable(f"tenant {body.tenant_id} not found")
        if self.master.get_equipment(body.equipment_id) is None:
            raise Unprocessable(f"equipment {body.equipment_id} not found")
        if self.master.get_part(body.part_id) is None:
            raise Unprocessable(f"part {body.part_id} not found")
        if self.master.get_user(body.requested_by) is None:
            raise Unprocessable(f"user {body.requested_by} not found")
        now = _now()
        wr = WorkRequest(
            id=next_work_request_id(self.db, now),
            tenant_id=body.tenant_id,
            equipment_id=body.equipment_id,
            part_id=body.part_id,
            symptom=body.symptom,
            site_check_note=body.site_check_note,
            requested_by=body.requested_by,
            status="REQUESTED",
            created_at=now,
            updated_at=now,
        )
        self.db.add(AuditLog(user_id=body.requested_by, entity="work_request", entity_id=wr.id, action="CREATE", after_json={"status": "REQUESTED"}))
        return self.repo.add(wr)

    # ------------------------------------------------------------------ read
    def get(self, wr_id: str) -> WorkRequest:
        wr = self.repo.get(wr_id)
        if wr is None:
            raise NotFound(f"work request {wr_id} not found")
        return wr

    def list(self, status: str | None, page: int, size: int) -> dict[str, Any]:
        rows, total = self.repo.list(status, page, size)
        return {"items": [self.summary(wr) for wr in rows], "total": total}

    def summary(self, wr: WorkRequest) -> dict[str, Any]:
        run = self.runs.latest_for(wr.id)
        progress = sum(1 for s in (run.steps_json if run else []) if s.get("status") == "DONE")
        eq = self.master.get_equipment(wr.equipment_id)
        part = self.master.get_part(wr.part_id)
        aps = self.approvals.list_for(wr.id)
        return {
            "id": wr.id,
            "equipment_id": wr.equipment_id,
            "equipment_name": eq.name if eq else None,
            "part_id": wr.part_id,
            "part_no": part.part_no if part else None,
            "symptom": wr.symptom,
            "status": wr.status,
            "requested_by": wr.requested_by,
            "agent_progress": {"done": progress, "total": 4},
            "approver_id": aps[-1].approver_id if aps else None,
            "created_at": wr.created_at,
            "updated_at": wr.updated_at,
        }

    def detail(self, wr_id: str) -> dict[str, Any]:
        wr = self.get(wr_id)
        run = self.runs.latest_for(wr.id)
        eq = self.master.get_equipment(wr.equipment_id)
        part = self.master.get_part(wr.part_id)
        return {
            **{c: getattr(wr, c) for c in ("id", "tenant_id", "equipment_id", "part_id", "symptom", "site_check_note", "requested_by", "status", "created_at", "updated_at")},
            "equipment_name": eq.name if eq else None,
            "part_no": part.part_no if part else None,
            "latest_run": run_to_schema(run) if run else None,
            "approvals": [approval_to_schema(a) for a in self.approvals.list_for(wr.id)],
        }

    # ------------------------------------------------------- submit approval
    def submit_approval(self, wr_id: str, body: SubmitApprovalBody | None) -> WorkRequest:
        """REVIEW → PENDING_APPROVAL. 409 if latest run is not REVIEW; 422 if documents still have missing items."""
        wr = self.get(wr_id)
        run = self.runs.latest_for(wr.id)
        if run is None or run.overall_status != "REVIEW":
            raise Conflict(f"agent run for {wr_id} is not complete (status={run.overall_status if run else 'NONE'})")
        if wr.status not in {"REVIEW", "PENDING_APPROVAL", "REJECTED"}:
            raise Conflict(f"work request {wr_id} is {wr.status}; expected REVIEW")

        body = body or SubmitApprovalBody()
        if body.site_check_note:
            wr.site_check_note = body.site_check_note

        # Fill missing items on generated documents from body.missing_info
        provided = body.missing_info or {}
        still_missing: list[str] = []
        for doc in run.documents:
            missing = [m for m in (doc.missing_json or []) if m not in provided]
            if missing != list(doc.missing_json or []):
                for k, v in provided.items():
                    doc.body = doc.body.replace(f"(누락) {k}", v)
                doc.missing_json = missing
                doc.version += 1
                self.db.add(doc)
            still_missing.extend(missing)
        # keep steps_json in sync with documents so FE sees the same picture
        steps = [dict(s) for s in run.steps_json]
        for s in steps:
            if s["agent"] == "SAFETY_DOC" and s.get("result"):
                by_id = {d.id: d for d in run.documents}
                s["result"]["documents"] = [
                    {**d, "missing": list(by_id[d["doc_id"]].missing_json) if d["doc_id"] in by_id else d["missing"]}
                    for d in s["result"]["documents"]
                ]
        run.steps_json = steps
        self.db.add(run)

        if still_missing:
            self.db.commit()
            raise Unprocessable("missing information: " + ", ".join(still_missing))

        before = wr.status
        wr.status = "PENDING_APPROVAL"
        wr.updated_at = _now()
        self.db.add(AuditLog(user_id=wr.requested_by, entity="work_request", entity_id=wr.id, action="SUBMIT_APPROVAL", before_json={"status": before}, after_json={"status": wr.status}))
        return self.repo.save(wr)

    # ----------------------------------------------------------------- done
    def complete(self, wr_id: str, user_id: str | None = None) -> WorkRequest:
        wr = self.get(wr_id)
        if wr.status != "APPROVED":
            raise Conflict(f"work request {wr_id} is {wr.status}; only APPROVED can be completed")
        wr.status = "DONE"
        wr.updated_at = _now()
        self.db.add(AuditLog(user_id=user_id, entity="work_request", entity_id=wr.id, action="COMPLETE", before_json={"status": "APPROVED"}, after_json={"status": "DONE"}))
        return self.repo.save(wr)
