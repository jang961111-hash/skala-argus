from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentRun, Document, LegalFinding


class AgentRunRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, run_id: str) -> AgentRun | None:
        return self.db.get(AgentRun, run_id)

    def latest_for(self, wr_id: str) -> AgentRun | None:
        return self.db.scalars(
            select(AgentRun).where(AgentRun.work_request_id == wr_id).order_by(AgentRun.created_at.desc())
        ).first()

    def add(self, run: AgentRun) -> AgentRun:
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def save(self, run: AgentRun) -> AgentRun:
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def add_documents(self, docs: list[Document]) -> None:
        self.db.add_all(docs)
        self.db.flush()

    def add_legal_findings(self, findings: list[LegalFinding]) -> None:
        self.db.add_all(findings)
        self.db.flush()

    def get_document(self, doc_id: str) -> Document | None:
        return self.db.get(Document, doc_id)
