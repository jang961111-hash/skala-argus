"""작업요청 스키마 (CONTRACT §4-5~10).

`draft=true` 면 업무 필드가 전부 선택이고 상태만 `DRAFT` 다. `draft=false` 의 필수값
검증과 productType 별 `specJson` 스키마 검증은 **서비스 계층**에서 한다
(400 `WORK_REQUEST_INCOMPLETE` / 400 `SPEC_SCHEMA_MISMATCH`).
"""
from __future__ import annotations

from typing import Any

from pydantic import Field

from app.core.enums import NextAction, ProductType, WorkRequestStatus
from app.schemas.agent import AgentRunDetail
from app.schemas.approval import ApprovalResponse
from app.schemas.base import CamelModel, KstDatetime


class OperatingCondition(CamelModel):
    temperature: str | None = Field(default=None, examples=["상온"])
    pressure: str | None = Field(default=None, examples=["3000 psi"])


class WorkRequestCreate(CamelModel):
    draft: bool = Field(default=False, description="true 면 임시저장 — 업무 필드 검증을 생략하고 상태만 DRAFT")
    equipment: str | None = Field(default=None, max_length=80, examples=["가스캐비닛#2"])
    line: str | None = Field(default=None, max_length=50, examples=["A라인"])
    substance: str | None = Field(default=None, max_length=80, examples=["SiH4"])
    operating_condition: OperatingCondition | None = None
    product_name: str | None = Field(default=None, max_length=120, examples=["SS-8-VCR"])
    product_type: ProductType | None = Field(default=None, examples=["VALVE"])
    spec_json: dict[str, Any] | None = Field(default=None, examples=[{"pressureRating": "3000 psi"}])
    symptom: str | None = Field(default=None, examples=["가스 유량 이상, 밸브 누설 의심"])
    site_memo: str | None = Field(default=None, examples=["현장 확인 결과 밸브 시트 마모"])


class WorkRequestPatch(CamelModel):
    """부분 수정 — 보낸 필드만 반영된다 (CONTRACT §4-8)."""

    equipment: str | None = Field(default=None, max_length=80)
    line: str | None = Field(default=None, max_length=50)
    substance: str | None = Field(default=None, max_length=80)
    operating_condition: OperatingCondition | None = None
    product_name: str | None = Field(default=None, max_length=120)
    product_type: ProductType | None = None
    spec_json: dict[str, Any] | None = None
    symptom: str | None = None
    site_memo: str | None = None
    engineer_note: str | None = None


class WorkRequestSummary(CamelModel):
    """목록 항목. `nextAction` 은 서버가 계산해 내려준다 (CONTRACT §4-6)."""

    id: str
    work_request_id: str
    request_no: str
    requester_id: str
    requester_name: str | None = None
    equipment: str | None = None
    line: str | None = None
    substance: str | None = None
    product_name: str | None = None
    product_type: ProductType | None = None
    symptom: str | None = None
    status: WorkRequestStatus
    next_action: NextAction
    created_at: KstDatetime
    updated_at: KstDatetime
    submitted_at: KstDatetime | None = None


class WorkRequestDetail(WorkRequestSummary):
    operating_condition: dict[str, Any] | None = None
    spec_json: dict[str, Any] | None = None
    site_memo: str | None = None
    engineer_note: str | None = None
    #: 최신 run 1건 (없으면 null)
    agent_run: AgentRunDetail | None = None
    #: 최신 결정 1건 (미처리면 null). 이력은 append-only 로 DB 에 남는다
    approval: ApprovalResponse | None = None
    photos: list["PhotoResponse"] = []


class PhotoResponse(CamelModel):
    id: str
    photo_id: str
    work_request_id: str
    file_name: str
    size: int
    storage_key: str
    thumbnail_key: str
    #: 화면에서 바로 쓰는 경로 — `/uploads` 정적 마운트가 서빙한다
    original_url: str
    thumbnail_url: str
    uploaded_at: KstDatetime
