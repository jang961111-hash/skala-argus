"""ID generators matching the CONTRACT sample format (WR-YYYYMMDD-NNN, RUN-NNNN, AP-NNNN, DOC-NNNN)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session


def next_work_request_id(db: Session, now: datetime) -> str:
    from app.models import WorkRequest

    prefix = f"WR-{now.strftime('%Y%m%d')}-"
    count = db.scalar(select(func.count()).select_from(WorkRequest).where(WorkRequest.id.like(prefix + "%"))) or 0
    return f"{prefix}{count + 1:03d}"


def _next_seq(db: Session, model, column, prefix: str, width: int) -> str:
    ids = db.scalars(select(column).where(column.like(prefix + "%"))).all()
    max_n = 0
    for i in ids:
        try:
            max_n = max(max_n, int(i[len(prefix):]))
        except ValueError:
            continue
    return f"{prefix}{max_n + 1:0{width}d}"


def next_run_id(db: Session) -> str:
    from app.models import AgentRun

    return _next_seq(db, AgentRun, AgentRun.id, "RUN-", 4)


def next_approval_id(db: Session) -> str:
    from app.models import Approval

    return _next_seq(db, Approval, Approval.id, "AP-", 4)


def next_document_id(db: Session) -> str:
    from app.models import Document

    return _next_seq(db, Document, Document.id, "DOC-", 4)
