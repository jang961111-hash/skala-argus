from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import Role
from app.db.session import Base
from app.db.types import pg_enum, uuid_pk


class User(Base):
    """CONTRACT §5 table 1. 대리키 PK, 업무 식별자 `email` 은 UNIQUE."""

    __tablename__ = "users"

    id: Mapped[str] = uuid_pk()
    name: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    # bcrypt ($2b$…). 어떤 응답 스키마에도 이 필드는 존재하지 않는다.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # 타입명은 docs/06_erd/schema_postgres.sql 의 `CREATE TYPE user_role` 과 일치해야 한다.
    # SQLite 는 VARCHAR+CHECK 라 이름이 달라도 안 드러나고, PostgreSQL 에서만 터진다.
    role: Mapped[Role] = mapped_column(pg_enum(Role, "user_role"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    work_requests: Mapped[list["WorkRequest"]] = relationship(  # noqa: F821
        "WorkRequest", back_populates="requester"
    )
    approvals: Mapped[list["Approval"]] = relationship("Approval", back_populates="approver")  # noqa: F821
