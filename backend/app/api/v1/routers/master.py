from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories.master_repo import MasterRepository
from app.schemas.common import ErrorResponse
from app.schemas.master import Equipment, Part, PartCompatibility
from app.services.errors import NotFound

router = APIRouter(tags=["master-data"])


@router.get("/equipments", response_model=list[Equipment])
def list_equipments(db: Session = Depends(get_db)):
    return MasterRepository(db).list_equipments()


@router.get("/parts", response_model=list[Part])
def list_parts(db: Session = Depends(get_db)):
    return MasterRepository(db).list_parts()


@router.get("/parts/{part_id}/compatibility", response_model=PartCompatibility, responses={404: {"model": ErrorResponse}})
def part_compatibility(part_id: str, db: Session = Depends(get_db)):
    repo = MasterRepository(db)
    part = repo.get_part(part_id)
    if part is None:
        raise NotFound(f"part {part_id} not found")
    alternatives = [
        {
            "part_id": alt.id,
            "part_no": alt.part_no,
            "name": alt.name,
            "grade": alt.grade,
            "diff": pc.diff,
            "allowed_for_toxic_gas": pc.allowed_for_toxic_gas,
            "stock": alt.stock,
        }
        for pc, alt in repo.alternatives(part_id)
    ]
    return {"part": part, "alternatives": alternatives}
