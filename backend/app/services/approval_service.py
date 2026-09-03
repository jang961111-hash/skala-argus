"""ApprovalService — state machine + checklist gate (Human-in-the-loop).

Transitions:
  PENDING_APPROVAL --APPROVE (checklist all true)--> APPROVED
  PENDING_APPROVAL --APPROVE (checklist incomplete)--> 409
  PENDING_APPROVAL --REJECT--> REJECTED
  PENDING_APPROVAL --REQUEST_INFO--> REVIEW  (엔지니어가 보완 후 다시 submit-approval)
Any other source status → 409.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import Approval, AuditLog
from app.repositories.approval_repo import ApprovalRepository
from app.repositories.ids import next_approval_id
from app.repositories.master_repo import MasterRepository
from app.repositories.work_request_repo import WorkRequestRepository
from app.schemas.approval import ApprovalCreate
from app.schemas.common import CHECKLIST_KEYS
from app.services.errors import Conflict, NotFound, Unprocessable

ALLOWED_SOURCE = {"PENDING_APPROVAL"}
TRANSITIONS = {"APPROVE": "APPROVED", "REJECT": "REJECTED", "REQUEST_INFO": "REVIEW"}


def approval_to_schema(ap: Approval) -> dict[str, Any]:
    checklist = {k: bool((ap.checklist_json or {}).get(k, False)) for k in CHECKLIST_KEYS}
    return {
        "approval_id": ap.id,
        "work_request_id": ap.work_request_id,
        "approver_id": ap.approver_id,
        "decision": ap.decision,
        "checklist": checklist,
        "comment": ap.comment,
        "decided_at": ap.decided_at,
    }


class ApprovalService:
    def __init__(self, db: Session):
        self.db = db
        self.work_requests = WorkRequestRepository(db)
        self.approvals = ApprovalRepository(db)
        self.master = MasterRepository(db)

    def decide(self, wr_id: str, body: ApprovalCreate) -> Approval:
        wr = self.work_requests.get(wr_id)
        if wr is None:
            raise NotFound(f"work request {wr_id} not found")
        approver = self.master.get_user(body.approver_id)
        if approver is None:
            raise Unprocessable(f"approver {body.approver_id} not found")
        if approver.role not in {"SAFETY_MANAGER", "ADMIN"}:
            raise Conflict(f"user {approver.id} ({approver.role}) is not allowed to approve")
        if wr.status not in ALLOWED_SOURCE:
            raise Conflict(f"work request {wr_id} is {wr.status}; approvals only allowed in PENDING_APPROVAL")

        decision = body.decision.value
        checklist = body.checklist.model_dump()
        if decision == "APPROVE" and not all(checklist.get(k) for k in CHECKLIST_KEYS):
            unchecked = [k for k in CHECKLIST_KEYS if not checklist.get(k)]
            raise Conflict("checklist incomplete: " + ", ".join(unchecked))

        now = datetime.now(timezone.utc)
        ap = Approval(
            id=next_approval_id(self.db),
            work_request_id=wr.id,
            approver_id=body.approver_id,
            decision=decision,
            checklist_json=checklist,
            comment=body.comment,
            decided_at=now,
        )
        before = wr.status
        wr.status = TRANSITIONS[decision]
        wr.updated_at = now
        self.db.add(wr)
        self.db.add(
            AuditLog(
                user_id=body.approver_id,
                entity="work_request",
                entity_id=wr.id,
                action=f"APPROVAL_{decision}",
                before_json={"status": before},
                after_json={"status": wr.status, "checklist": checklist},
            )
        )
        return self.approvals.add(ap)
