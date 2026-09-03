from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import AgentType, AiProvider, DocumentType, ORMModel, PartGrade


class Equipment(ORMModel):
    id: str
    tenant_id: str
    name: str
    type: str
    line: str | None = None
    substances: list[str] = []


class Part(ORMModel):
    id: str
    tenant_id: str
    part_no: str
    name: str
    spec: dict[str, Any] = {}
    grade: PartGrade
    toxic_gas_allowed: bool
    stock: int


class PartAlternative(BaseModel):
    part_id: str
    part_no: str
    name: str
    grade: PartGrade
    diff: str | None = None
    allowed_for_toxic_gas: bool
    stock: int


class PartCompatibility(BaseModel):
    part: Part
    alternatives: list[PartAlternative]


class Document(BaseModel):
    doc_id: str
    agent_run_id: str
    type: DocumentType
    body: str
    missing: list[str] = []
    version: int = 1


class LawArticle(ORMModel):
    id: str
    law: str
    article: str
    title: str | None = None
    text: str
    effective_date: str | None = None
    source_uri: str | None = None


class LawSearchResult(BaseModel):
    items: list[LawArticle]


class RejectReason(BaseModel):
    reason: str
    count: int


class DashboardSummary(BaseModel):
    in_progress: int
    pending_approval: int
    avg_approval_hours: float
    as_is_baseline_hours: float = 168
    completed_this_month: int
    reject_reasons_top: list[RejectReason]


class AiConfig(BaseModel):
    tenant_id: str
    agent_type: AgentType
    provider: AiProvider
    model_name: str
    prompt_version: str
    egress_allowed: bool = False


class AiConfigUpdate(BaseModel):
    agent_type: AgentType
    provider: AiProvider
    model_name: str = Field(default="mock-v1")
    prompt_version: str = Field(default="replaceflow-v0.1")
    egress_allowed: bool = False
