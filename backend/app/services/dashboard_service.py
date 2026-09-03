"""DashboardService — 역할별 KPI (CONTRACT §4-4).

`role` 은 필수이고 토큰 역할과 다르면 403 `FORBIDDEN_ROLE`.
엔지니어 KPI 는 **본인 요청 기준**이다(E_01 은 개인 화면이고 §1 권한 규약도 본인 것만 허용).
'오늘'·'이번 달'은 KST 기준으로 센다.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import ApprovalDecision, Role, WorkRequestStatus
from app.core.errors import AppError, ErrorCode
from app.models import Approval, User, WorkRequest
from app.repositories.approval_repo import ApprovalRepository
from app.repositories.work_request_repo import WorkRequestRepository

KST = timezone(timedelta(hours=9))


def _to_kst(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(KST)


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.work_requests = WorkRequestRepository(db)
        self.approvals = ApprovalRepository(db)

    def summary(self, role: str, current: User) -> dict[str, Any]:
        expected = Role.ENGINEER if role == "engineer" else Role.SAFETY_MANAGER
        if current.role is not expected:
            raise AppError(ErrorCode.FORBIDDEN_ROLE, "토큰 역할과 요청한 대시보드 역할이 다릅니다")
        return self._engineer(current) if expected is Role.ENGINEER else self._safety()

    def _engineer(self, current: User) -> dict[str, Any]:
        counts = self.work_requests.count_by_status(requester_id=current.id)
        return {
            "draft": counts.get(WorkRequestStatus.DRAFT, 0),
            "aiRunning": counts.get(WorkRequestStatus.AI_RUNNING, 0),
            "pending": counts.get(WorkRequestStatus.PENDING, 0),
            "rejected": counts.get(WorkRequestStatus.REJECTED, 0),
        }

    def _safety(self) -> dict[str, Any]:
        pending = self.db.scalar(
            select(func.count()).select_from(WorkRequest).where(WorkRequest.status == WorkRequestStatus.PENDING)
        ) or 0

        now = _to_kst(datetime.now(timezone.utc))
        approvals = self.approvals.all()
        today = sum(1 for a in approvals if _to_kst(a.decided_at).date() == now.date())
        this_month = [
            a for a in approvals
            if _to_kst(a.decided_at).year == now.year and _to_kst(a.decided_at).month == now.month
        ]
        reasons = Counter(_reason_key(a) for a in approvals if a.decision is ApprovalDecision.REJECT)
        return {
            "pending": pending,
            "todayProcessed": today,
            "monthApproved": sum(1 for a in this_month if a.decision is ApprovalDecision.APPROVE),
            "monthRejected": sum(1 for a in this_month if a.decision is ApprovalDecision.REJECT),
            "rejectReasonsTop": [{"reason": r, "count": c} for r, c in reasons.most_common(5)],
        }


def _reason_key(approval: Approval) -> str:
    """집계 키는 `reason_category` 가 우선이다. 없으면 사유 앞머리(`분류: 상세`)를 쓴다."""
    if approval.reason_category:
        return approval.reason_category
    text = approval.reason or ""
    return text.split(":")[0].strip()[:30] or "기타"
