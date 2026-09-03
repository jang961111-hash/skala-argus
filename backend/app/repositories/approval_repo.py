from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Approval


class ApprovalRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, ap: Approval) -> Approval:
        self.db.add(ap)
        self.db.commit()
        self.db.refresh(ap)
        return ap

    def list_for(self, wr_id: str) -> list[Approval]:
        return list(
            self.db.scalars(select(Approval).where(Approval.work_request_id == wr_id).order_by(Approval.decided_at)).all()
        )

    def all(self) -> list[Approval]:
        return list(self.db.scalars(select(Approval)).all())
