from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories.agent_run_repo import AgentRunRepository
from app.schemas.common import ErrorResponse
from app.schemas.master import Document
from app.services.errors import NotFound

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{doc_id}", response_model=Document, responses={404: {"model": ErrorResponse}})
def get_document(doc_id: str, db: Session = Depends(get_db)):
    doc = AgentRunRepository(db).get_document(doc_id)
    if doc is None:
        raise NotFound(f"document {doc_id} not found")
    return {
        "doc_id": doc.id,
        "agent_run_id": doc.agent_run_id,
        "type": doc.type,
        "body": doc.body,
        "missing": list(doc.missing_json or []),
        "version": doc.version,
    }
