from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ProductType, WorkRequestStatus
from app.db.session import Base
from app.db.types import JSONB_, pg_enum, uuid_fk, uuid_pk


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WorkRequest(Base):
    """CONTRACT §5 table 2.

    대리키 `id`(UUID) 와 업무 식별자 `request_no`(WR-YYYYMMDD-NNN, 서버 채번) 를 분리한다.
    DRAFT 를 허용하려고 업무 컬럼은 DB NOT NULL 이 아니다 — `draft=false` 조건부 검증은
    서비스 계층(`WorkRequestService._require_complete`)이 맡는다.
    """

    __tablename__ = "work_requests"
    __table_args__ = (
        Index("ix_work_requests_requester_status", "requester_id", "status"),  # E_01 · E_05
        Index("ix_work_requests_status_submitted", "status", "submitted_at"),  # S_01
    )

    id: Mapped[str] = uuid_pk()
    request_no: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    requester_id: Mapped[str] = uuid_fk("users.id", index=True, nullable=False)

    equipment: Mapped[str | None] = mapped_column(String(80), nullable=True)
    line: Mapped[str | None] = mapped_column(String(50), nullable=True)
    substance: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # {"temperature": "...", "pressure": "..."} — 구조가 가변이라 jsonb
    operating_condition: Mapped[dict | None] = mapped_column(JSONB_, nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    product_type: Mapped[ProductType | None] = mapped_column(pg_enum(ProductType, "product_type"), nullable=True)
    spec_json: Mapped[dict | None] = mapped_column(JSONB_, nullable=True)
    symptom: Mapped[str | None] = mapped_column(Text, nullable=True)
    site_memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    engineer_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[WorkRequestStatus] = mapped_column(
        pg_enum(WorkRequestStatus, "work_request_status"), default=WorkRequestStatus.DRAFT, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    requester: Mapped["User"] = relationship("User", back_populates="work_requests")  # noqa: F821
    photos: Mapped[list["WorkRequestPhoto"]] = relationship(
        "WorkRequestPhoto", back_populates="work_request", order_by="WorkRequestPhoto.uploaded_at",
        cascade="all, delete-orphan",
    )
    # append-only: 재실행마다 행 추가, 화면에는 최신 1건
    runs: Mapped[list["AgentRun"]] = relationship(  # noqa: F821
        "AgentRun", back_populates="work_request", order_by="AgentRun.started_at", cascade="all, delete-orphan"
    )
    # append-only: 재제출 후 재결정도 행 추가
    approvals: Mapped[list["Approval"]] = relationship(  # noqa: F821
        "Approval", back_populates="work_request", order_by="Approval.decided_at", cascade="all, delete-orphan"
    )


class WorkRequestPhoto(Base):
    """CONTRACT §5 table 3. 원본과 320px 썸네일을 각각 저장하고 EXIF 는 제거한다."""

    __tablename__ = "work_request_photos"

    id: Mapped[str] = uuid_pk()
    work_request_id: Mapped[str] = uuid_fk("work_requests.id", index=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(500))
    thumbnail_key: Mapped[str] = mapped_column(String(500))
    size: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    work_request: Mapped[WorkRequest] = relationship("WorkRequest", back_populates="photos")
