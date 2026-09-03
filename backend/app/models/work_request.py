from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class WorkRequest(Base):
    __tablename__ = "work_requests"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"))
    equipment_id: Mapped[str] = mapped_column(ForeignKey("equipments.id"))
    part_id: Mapped[str] = mapped_column(ForeignKey("parts.id"))
    symptom: Mapped[str] = mapped_column(Text)
    site_check_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    # REQUESTED → RUNNING → REVIEW → PENDING_APPROVAL → APPROVED | REJECTED → DONE
    status: Mapped[str] = mapped_column(String(32), default="REQUESTED", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    runs: Mapped[list["AgentRun"]] = relationship(  # noqa: F821
        "AgentRun", back_populates="work_request", order_by="AgentRun.created_at"
    )
    approvals: Mapped[list["Approval"]] = relationship(
        "Approval", back_populates="work_request", order_by="Approval.decided_at"
    )


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    work_request_id: Mapped[str] = mapped_column(ForeignKey("work_requests.id"), index=True)
    approver_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(16))  # APPROVE | REJECT | REQUEST_INFO
    checklist_json: Mapped[dict] = mapped_column(JSON, default=dict)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    work_request: Mapped[WorkRequest] = relationship("WorkRequest", back_populates="approvals")
