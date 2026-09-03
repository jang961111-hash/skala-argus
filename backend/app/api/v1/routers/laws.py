from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories.master_repo import MasterRepository
from app.schemas.master import LawSearchResult

router = APIRouter(prefix="/laws", tags=["laws"])


@router.get("/search", response_model=LawSearchResult, summary="법령 인덱스 검색 (사내 사전 적재, 외부 전송 없음)")
def search_laws(
    q: str | None = Query(default=None),
    equipment_type: str | None = Query(default=None, alias="equipmentType"),
    substance: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return {"items": MasterRepository(db).search_laws(q, equipment_type, substance)}
