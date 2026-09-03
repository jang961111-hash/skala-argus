"""`work_requests.request_no` 채번 — `WR-YYYYMMDD-NNN`, 서버가 매긴다 (CONTRACT §5).

당일 최대 일련번호 + 1 이라 동시 생성이 겹칠 수 있다. ERD 문서가 "시퀀스 또는 행 잠금"을
요구하므로, PostgreSQL 에서는 조회 시 `FOR UPDATE` 로 당일 행을 잠그고, 어느 DB 에서든
UNIQUE 제약 위반(IntegrityError)을 잡아 재시도한다. UNIQUE 인덱스가 최종 방어선이다.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

KST = timezone(timedelta(hours=9))
MAX_ATTEMPTS = 5


def _prefix(now: datetime) -> str:
    return f"WR-{now.astimezone(KST).strftime('%Y%m%d')}-"


def next_request_no(db: Session, now: datetime | None = None) -> str:
    from app.models import WorkRequest

    prefix = _prefix(now or datetime.now(timezone.utc))
    stmt = select(func.max(WorkRequest.request_no)).where(WorkRequest.request_no.like(f"{prefix}%"))
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        # 같은 날짜 묶음을 잠가 동시 채번이 같은 번호를 읽지 못하게 한다
        db.execute(
            select(WorkRequest.id)
            .where(WorkRequest.request_no.like(f"{prefix}%"))
            .with_for_update()
        ).all()
    latest = db.scalar(stmt)
    seq = int(latest[len(prefix):]) + 1 if latest else 1
    return f"{prefix}{seq:03d}"


def insert_with_request_no(db: Session, work_request, now: datetime | None = None):
    """UNIQUE 충돌 시 번호를 다시 따서 재시도한다."""
    for attempt in range(MAX_ATTEMPTS):
        work_request.request_no = next_request_no(db, now)
        savepoint = db.begin_nested()
        try:
            db.add(work_request)
            savepoint.commit()
            db.commit()
            db.refresh(work_request)
            return work_request
        except IntegrityError:
            savepoint.rollback()
            if attempt == MAX_ATTEMPTS - 1:
                raise
    raise RuntimeError("unreachable")
