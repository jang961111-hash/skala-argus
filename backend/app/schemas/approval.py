"""승인 스키마 (CONTRACT §4-15).

체크리스트 blocking 은 없다. 승인은 사유 없이 즉시, 거절만 `reason` 10자 이상 필수
(미만이면 400 `REJECT_REASON_REQUIRED`) — 길이 판정은 서비스가 한다.
"""
from __future__ import annotations

from pydantic import Field

from app.core.enums import ApprovalDecision
from app.schemas.base import CamelModel, KstDatetime

REJECT_REASON_MIN_LEN = 10


class ApprovalCreate(CamelModel):
    work_request_id: str
    decision: ApprovalDecision
    reason: str | None = Field(default=None, examples=["유독가스 라인이라 호환품 사용이 불가합니다"])
    reason_category: str | None = Field(default=None, max_length=30, examples=["규격 부적합"])


class ApprovalResponse(CamelModel):
    id: str
    approval_id: str
    work_request_id: str
    approver_id: str
    approver_name: str | None = None
    decision: ApprovalDecision
    reason: str | None = None
    reason_category: str | None = None
    decided_at: KstDatetime
