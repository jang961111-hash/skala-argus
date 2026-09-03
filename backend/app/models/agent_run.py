from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    work_request_id: Mapped[str] = mapped_column(ForeignKey("work_requests.id"), index=True)
    overall_status: Mapped[str] = mapped_column(String(16), default="RUNNING", index=True)  # RUNNING | REVIEW | FAILED
    steps_json: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    approval_required_by: Mapped[str] = mapped_column(String(32), default="SAFETY_MANAGER")
    model_name: Mapped[str] = mapped_column(String(100), default="mock-v1", index=True)
    prompt_version: Mapped[str] = mapped_column(String(50), default="replaceflow-v0.1", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    work_request = relationship("WorkRequest", back_populates="runs")
    legal_findings: Mapped[list["LegalFinding"]] = relationship("LegalFinding", back_populates="run")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="run")


class LegalFinding(Base):
    __tablename__ = "legal_findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    law: Mapped[str | None] = mapped_column(String(200), nullable=True)
    article: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    procedure_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phase: Mapped[str | None] = mapped_column(String(16), nullable=True)  # BEFORE | DURING | AFTER
    required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    run = relationship("AgentRun", back_populates="legal_findings")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    agent_run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    type: Mapped[str] = mapped_column(String(32))  # WORK_PERMIT | RISK_ASSESSMENT | LOTO_CHECKLIST | RFQ
    body: Mapped[str] = mapped_column(Text, default="")
    missing_json: Mapped[list] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)

    run = relationship("AgentRun", back_populates="documents")
