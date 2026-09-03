from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Approval


class ApprovalRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, approval: Approval) -> Approval:
        self.db.add(approval)
        self.db.commit()
        self.db.refresh(approval)
        return approval

    def list_for(self, wr_id: str) -> list[Approval]:
        return list(
            self.db.scalars(
                select(Approval).where(Approval.work_request_id == wr_id).order_by(Approval.decided_at)
            ).all()
        )

    def latest_for(self, wr_id: str) -> Approval | None:
        """append-only 이력 중 최신 1건. 미처리면 None."""
        return self.db.scalars(
            select(Approval).where(Approval.work_request_id == wr_id).order_by(Approval.decided_at.desc())
        ).first()

    def decided_between(self, start: datetime, end: datetime) -> list[Approval]:
        return list(
            self.db.scalars(
                select(Approval).where(Approval.decided_at >= start, Approval.decided_at < end)
            ).all()
        )

    def all(self) -> list[Approval]:
        return list(self.db.scalars(select(Approval)).all())
