from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import WorkRequest


class WorkRequestRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, wr_id: str) -> WorkRequest | None:
        return self.db.get(WorkRequest, wr_id)

    def list(self, status: str | None, page: int, size: int) -> tuple[list[WorkRequest], int]:
        stmt = select(WorkRequest)
        if status:
            stmt = stmt.where(WorkRequest.status == status)
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = self.db.scalars(
            stmt.order_by(WorkRequest.created_at.desc()).offset((page - 1) * size).limit(size)
        ).all()
        return list(rows), total

    def add(self, wr: WorkRequest) -> WorkRequest:
        self.db.add(wr)
        self.db.commit()
        self.db.refresh(wr)
        return wr

    def save(self, wr: WorkRequest) -> WorkRequest:
        self.db.add(wr)
        self.db.commit()
        self.db.refresh(wr)
        return wr

    def count_by_status(self, statuses: list[str]) -> int:
        return self.db.scalar(
            select(func.count()).select_from(WorkRequest).where(WorkRequest.status.in_(statuses))
        ) or 0
