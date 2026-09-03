from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import Decision


class Checklist(BaseModel):
    WORK_PERMIT: bool = False
    RISK_ASSESSMENT: bool = False
    LOTO_GAS_ISOLATION: bool = False
    GAS_DETECTOR_CHECK: bool = False

    def is_complete(self) -> bool:
        return all(self.model_dump().values())


class ApprovalCreate(BaseModel):
    approver_id: str = Field(examples=["U-002"])
    decision: Decision
    checklist: Checklist = Field(default_factory=Checklist)
    comment: str | None = Field(default=None, examples=["작업자 명단 확인 완료. 승인."])


class Approval(BaseModel):
    approval_id: str
    work_request_id: str
    approver_id: str
    decision: Decision
    checklist: Checklist
    comment: str | None = None
    decided_at: datetime
