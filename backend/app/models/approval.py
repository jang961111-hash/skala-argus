from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ApprovalDecision
from app.db.session import Base
from app.db.types import pg_enum, uuid_fk, uuid_pk


class Approval(Base):
    """CONTRACT §5 table 7.

    append-only: 거절 → 재제출 → 재결정도 갱신이 아니라 행 추가다. 화면에는 최신 1건만 노출한다.
    `reason_category` 는 S_01 의 거절 사유 TOP5 집계 키라서 jsonb 가 아니라 컬럼이다.
    """

    __tablename__ = "approvals"
    __table_args__ = (
        Index("ix_approvals_wr_decided", "work_request_id", "decided_at"),
        Index("ix_approvals_decided_at", "decided_at"),
    )

    id: Mapped[str] = uuid_pk()
    work_request_id: Mapped[str] = uuid_fk("work_requests.id", index=True, nullable=False)
    approver_id: Mapped[str] = uuid_fk("users.id", nullable=False)
    decision: Mapped[ApprovalDecision] = mapped_column(pg_enum(ApprovalDecision, "approval_decision"))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason_category: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    work_request = relationship("WorkRequest", back_populates="approvals")
    approver = relationship("User", back_populates="approvals")
