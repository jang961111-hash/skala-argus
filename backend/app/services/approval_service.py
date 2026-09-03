"""ApprovalService — 승인/거절 (CONTRACT §4-15).

체크리스트 blocking 은 없다. 승인은 사유 없이 즉시, 거절만 `reason` 10자 이상 필수.
append-only 이력이라 거절 → 재제출 → 재결정도 행을 추가한다. 상태가 PENDING 이 아닐 때
이미 결정 이력이 있으면 `ALREADY_DECIDED`, 아직 한 번도 결정되지 않았으면 `NOT_PENDING` 이다.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.enums import ApprovalDecision, WorkRequestStatus
from app.core.errors import AppError, ErrorCode
from app.models import Approval, User
from app.repositories.approval_repo import ApprovalRepository
from app.repositories.user_repo import UserRepository
from app.repositories.work_request_repo import WorkRequestRepository
from app.schemas.approval import REJECT_REASON_MIN_LEN, ApprovalCreate

DECISION_TO_STATUS = {
    ApprovalDecision.APPROVE: WorkRequestStatus.APPROVED,
    ApprovalDecision.REJECT: WorkRequestStatus.REJECTED,
}


def approval_to_schema(approval: Approval, approver: User | None = None) -> dict[str, Any]:
    return {
        "id": approval.id,
        "approvalId": approval.id,
        "workRequestId": approval.work_request_id,
        "approverId": approval.approver_id,
        "approverName": approver.name if approver else None,
        "decision": approval.decision,
        "reason": approval.reason,
        "reasonCategory": approval.reason_category,
        "decidedAt": approval.decided_at,
    }


class ApprovalService:
    def __init__(self, db: Session):
        self.db = db
        self.work_requests = WorkRequestRepository(db)
        self.approvals = ApprovalRepository(db)
        self.users = UserRepository(db)

    def decide(self, body: ApprovalCreate, approver: User) -> Approval:
        wr = self.work_requests.get(body.work_request_id)
        if wr is None:
            raise AppError(ErrorCode.WORK_REQUEST_NOT_FOUND, "작업요청을 찾을 수 없습니다")
        if wr.status is not WorkRequestStatus.PENDING:
            if self.approvals.latest_for(wr.id) is not None:
                raise AppError(ErrorCode.ALREADY_DECIDED, "이미 결정된 요청입니다")
            raise AppError(ErrorCode.NOT_PENDING, f"{wr.status.value} 상태의 요청은 결정할 수 없습니다")

        reason = (body.reason or "").strip() or None
        if body.decision is ApprovalDecision.REJECT and (reason is None or len(reason) < REJECT_REASON_MIN_LEN):
            raise AppError(
                ErrorCode.REJECT_REASON_REQUIRED,
                f"거절 사유는 {REJECT_REASON_MIN_LEN}자 이상 입력해야 합니다",
                [{"field": "reason", "message": f"{REJECT_REASON_MIN_LEN}자 이상"}],
            )

        now = datetime.now(timezone.utc)
        approval = Approval(
            work_request_id=wr.id,
            approver_id=approver.id,
            decision=body.decision,
            reason=reason,
            reason_category=(body.reason_category or "").strip() or None,
            decided_at=now,
        )
        wr.status = DECISION_TO_STATUS[body.decision]
        wr.updated_at = now
        self.db.add(wr)
        return self.approvals.add(approval)
