from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import WorkRequestStatus
from app.models import WorkRequest, WorkRequestPhoto

#: `sort=필드,asc|desc` 로 지정할 수 있는 필드 (CONTRACT §1)
SORTABLE = {
    "createdAt": WorkRequest.created_at,
    "updatedAt": WorkRequest.updated_at,
    "submittedAt": WorkRequest.submitted_at,
    "requestNo": WorkRequest.request_no,
    "status": WorkRequest.status,
}


class WorkRequestRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, wr_id: str) -> WorkRequest | None:
        return self.db.get(WorkRequest, wr_id)

    def list(
        self,
        *,
        statuses: list[WorkRequestStatus] | None,
        requester_id: str | None,
        visible_statuses: frozenset[WorkRequestStatus] | None,
        page: int,
        size: int,
        sort_field: str,
        sort_desc: bool,
    ) -> tuple[list[WorkRequest], int]:
        stmt = select(WorkRequest)
        if requester_id:
            stmt = stmt.where(WorkRequest.requester_id == requester_id)
        if visible_statuses is not None:
            stmt = stmt.where(WorkRequest.status.in_(list(visible_statuses)))
        if statuses:
            stmt = stmt.where(WorkRequest.status.in_(statuses))

        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        column = SORTABLE.get(sort_field, WorkRequest.created_at)
        order = column.desc() if sort_desc else column.asc()
        rows = self.db.scalars(
            stmt.order_by(order, WorkRequest.request_no.desc()).offset(page * size).limit(size)
        ).all()
        return list(rows), total

    def count_by_status(self, requester_id: str | None = None) -> dict[WorkRequestStatus, int]:
        stmt = select(WorkRequest.status, func.count()).group_by(WorkRequest.status)
        if requester_id:
            stmt = stmt.where(WorkRequest.requester_id == requester_id)
        return {status: count for status, count in self.db.execute(stmt).all()}

    def save(self, wr: WorkRequest) -> WorkRequest:
        self.db.add(wr)
        self.db.commit()
        self.db.refresh(wr)
        return wr

    # --- photos -------------------------------------------------------------
    def photos_for(self, wr_id: str) -> list[WorkRequestPhoto]:
        return list(
            self.db.scalars(
                select(WorkRequestPhoto)
                .where(WorkRequestPhoto.work_request_id == wr_id)
                .order_by(WorkRequestPhoto.uploaded_at)
            ).all()
        )

    def count_photos(self, wr_id: str) -> int:
        return self.db.scalar(
            select(func.count()).select_from(WorkRequestPhoto).where(WorkRequestPhoto.work_request_id == wr_id)
        ) or 0
