from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories.master_repo import MasterRepository
from app.schemas.common import ErrorResponse
from app.schemas.master import AiConfig, AiConfigUpdate
from app.services.errors import Conflict, NotFound

router = APIRouter(prefix="/tenants", tags=["ai-config"])


@router.get("/{tenant_id}/ai-config", response_model=list[AiConfig], responses={404: {"model": ErrorResponse}})
def get_ai_config(tenant_id: str, db: Session = Depends(get_db)):
    repo = MasterRepository(db)
    if repo.get_tenant(tenant_id) is None:
        raise NotFound(f"tenant {tenant_id} not found")
    return repo.list_ai_configs(tenant_id)


@router.put(
    "/{tenant_id}/ai-config",
    response_model=list[AiConfig],
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="에이전트별 provider/model/egress 설정 — 외부 provider는 egress_allowed=true 필요",
)
def put_ai_config(tenant_id: str, body: list[AiConfigUpdate], db: Session = Depends(get_db)):
    repo = MasterRepository(db)
    if repo.get_tenant(tenant_id) is None:
        raise NotFound(f"tenant {tenant_id} not found")
    for item in body:
        if item.provider.value in {"OPENAI", "AX_PLATFORM"} and not item.egress_allowed:
            raise Conflict(f"{item.agent_type.value}: provider {item.provider.value} requires egress_allowed=true")
        repo.upsert_ai_config(
            tenant_id,
            item.agent_type.value,
            provider=item.provider.value,
            model_name=item.model_name,
            prompt_version=item.prompt_version,
            egress_allowed=item.egress_allowed,
        )
    db.commit()
    return repo.list_ai_configs(tenant_id)
