from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.agent_run import AgentRun
from app.schemas.approval import Approval
from app.schemas.common import ORMModel, WorkRequestStatus


class WorkRequestCreate(BaseModel):
    tenant_id: str = Field(default="T-001", examples=["T-001"])
    equipment_id: str = Field(examples=["EQ-GC-02"])
    part_id: str = Field(examples=["P-VLV-001"])
    symptom: str = Field(min_length=1, examples=["가스 유량 이상, 밸브 누설 의심"])
    site_check_note: str | None = Field(default=None, examples=["현장 확인 결과 밸브 시트 마모"])
    requested_by: str = Field(examples=["U-001"])


class WorkRequest(ORMModel):
    id: str
    tenant_id: str
    equipment_id: str
    part_id: str
    symptom: str
    site_check_note: str | None = None
    requested_by: str
    status: WorkRequestStatus
    created_at: datetime
    updated_at: datetime


class WorkRequestSummary(ORMModel):
    id: str
    equipment_id: str
    equipment_name: str | None = None
    part_id: str
    part_no: str | None = None
    symptom: str
    status: WorkRequestStatus
    requested_by: str
    agent_progress: dict = Field(default_factory=lambda: {"done": 0, "total": 4}, description="완료된 step 수 {done, total}")
    approver_id: str | None = None
    created_at: datetime
    updated_at: datetime


class WorkRequestList(BaseModel):
    items: list[WorkRequestSummary]
    total: int


class WorkRequestDetail(WorkRequest):
    equipment_name: str | None = None
    part_no: str | None = None
    latest_run: AgentRun | None = None
    approvals: list[Approval] = []


class SubmitApprovalBody(BaseModel):
    """PATCH /work-requests/{id}/submit-approval. 누락 정보 보완 값 (optional)."""

    site_check_note: str | None = None
    missing_info: dict[str, str] | None = Field(
        default=None, description="SAFETY_DOC missing 항목 보완 값 (예: {'작업자 2명 이름': '김민준, 박수진'})"
    )
