from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import AgentCode, AgentStepStatus, RunStatus
from app.db.session import Base
from app.db.types import JSONB_, pg_enum, uuid_fk, uuid_pk


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AgentRun(Base):
    """CONTRACT §5 table 4. 재실행은 갱신이 아니라 행 추가(append-only)."""

    __tablename__ = "agent_runs"

    id: Mapped[str] = uuid_pk()
    work_request_id: Mapped[str] = uuid_fk("work_requests.id", index=True, nullable=False)
    status: Mapped[RunStatus] = mapped_column(pg_enum(RunStatus, "run_status"), default=RunStatus.RUNNING)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # [제안] 실행 시점의 요청 스냅샷 — 이후 요청이 수정돼도 무엇을 넣고 돌렸는지 남는다
    input_snapshot: Mapped[dict | None] = mapped_column(JSONB_, nullable=True)

    work_request = relationship("WorkRequest", back_populates="runs")
    steps: Mapped[list["AgentStep"]] = relationship(
        "AgentStep", back_populates="run", order_by="AgentStep.agent_code", cascade="all, delete-orphan"
    )
    results: Mapped[list["AgentResult"]] = relationship(
        "AgentResult", back_populates="run", order_by="AgentResult.agent_code", cascade="all, delete-orphan"
    )


class AgentStep(Base):
    """CONTRACT §5 table 5 — 진행 상태 전용.

    결과(`agent_results`)와 테이블을 나눈 이유: 폴링이 일으키는 UPDATE 와 엔지니어 편집이
    일으키는 UPDATE 가 같은 행을 경합하지 않게 하려는 것이다.
    """

    __tablename__ = "agent_steps"
    __table_args__ = (UniqueConstraint("run_id", "agent_code", name="uq_agent_steps_run_agent"),)

    id: Mapped[str] = uuid_pk()
    run_id: Mapped[str] = uuid_fk("agent_runs.id", index=True, nullable=False)
    agent_code: Mapped[AgentCode] = mapped_column(pg_enum(AgentCode, "agent_code"))
    status: Mapped[AgentStepStatus] = mapped_column(
        pg_enum(AgentStepStatus, "agent_step_status"), default=AgentStepStatus.WAITING
    )
    message: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    run: Mapped[AgentRun] = relationship("AgentRun", back_populates="steps")


class AgentResult(Base):
    """CONTRACT §5 table 6 — 결과 전용.

    `payload_json` 통일 구조: A1·A2 는 `{"items":[…]}`, A3 는 `{"documents":[…]}`.
    `original_json` 은 AI 원본 스냅샷이라 항목별 `edited` 를 서버가 판정할 수 있다.
    """

    __tablename__ = "agent_results"
    __table_args__ = (UniqueConstraint("run_id", "agent_code", name="uq_agent_results_run_agent"),)

    id: Mapped[str] = uuid_pk()
    run_id: Mapped[str] = uuid_fk("agent_runs.id", index=True, nullable=False)
    agent_code: Mapped[AgentCode] = mapped_column(pg_enum(AgentCode, "agent_code"))
    payload_json: Mapped[dict] = mapped_column(JSONB_, default=dict)
    edited: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    # [제안] AI 원본 — 편집 후에도 원본과 대조할 수 있게 남긴다
    original_json: Mapped[dict | None] = mapped_column(JSONB_, nullable=True)

    run: Mapped[AgentRun] = relationship("AgentRun", back_populates="results")
