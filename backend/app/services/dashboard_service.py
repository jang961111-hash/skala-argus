from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Approval, WorkRequest

AS_IS_BASELINE_HOURS = 168.0  # As-Is: 약 7일 (기획서)
IN_PROGRESS = ["REQUESTED", "RUNNING", "REVIEW", "PENDING_APPROVAL"]


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def summary(self) -> dict[str, Any]:
        wrs = list(self.db.scalars(select(WorkRequest)).all())
        approvals = list(self.db.scalars(select(Approval)).all())
        by_wr = {wr.id: wr for wr in wrs}

        in_progress = sum(1 for wr in wrs if wr.status in IN_PROGRESS)
        pending = sum(1 for wr in wrs if wr.status == "PENDING_APPROVAL")

        hours: list[float] = []
        for ap in approvals:
            if ap.decision == "APPROVE" and ap.work_request_id in by_wr:
                delta = _aware(ap.decided_at) - _aware(by_wr[ap.work_request_id].created_at)
                hours.append(delta.total_seconds() / 3600)
        avg = round(sum(hours) / len(hours), 1) if hours else 0.0

        now = datetime.now(timezone.utc)
        completed = sum(
            1
            for wr in wrs
            if wr.status in {"APPROVED", "DONE"} and _aware(wr.updated_at).year == now.year and _aware(wr.updated_at).month == now.month
        )

        reasons = Counter(_reason(ap.comment) for ap in approvals if ap.decision == "REJECT")
        top = [{"reason": r, "count": c} for r, c in reasons.most_common(5)]
        return {
            "in_progress": in_progress,
            "pending_approval": pending,
            "avg_approval_hours": avg,
            "as_is_baseline_hours": AS_IS_BASELINE_HOURS,
            "completed_this_month": completed,
            "reject_reasons_top": top,
        }


def _reason(comment: str | None) -> str:
    """Reject comment convention: '<사유>: <상세>' → 사유. Fallback '기타'."""
    if not comment:
        return "기타"
    return comment.split(":")[0].strip() or "기타"
