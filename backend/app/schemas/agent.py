"""에이전트 스키마 (CONTRACT §4-11~13).

`agent_steps`(진행)와 `agent_results`(결과)를 나눈 DB 구조가 응답에도 그대로 드러난다.
폴링은 `steps` 만 보고, 결과 확인·편집 화면은 `results` 를 본다.
"""
from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from app.core.enums import AgentCode, AgentStepStatus, RunStatus
from app.schemas.base import CamelModel, KstDatetime


class AgentStepResponse(CamelModel):
    agent_code: AgentCode
    status: AgentStepStatus
    message: str | None = None
    error_message: str | None = None
    started_at: KstDatetime | None = None
    finished_at: KstDatetime | None = None


class AgentResultResponse(CamelModel):
    id: str
    agent_result_id: str
    agent_code: AgentCode
    payload_json: dict[str, Any]
    edited: bool = False
    #: SAFETY_MANAGER 가 조회하면 항상 false (CONTRACT §4-7)
    editable: bool = False
    updated_at: KstDatetime | None = None


class AgentRunResponse(CamelModel):
    """폴링 응답. `allDone` 과 `pollIntervalMs` 는 서버가 내려준다 (CONTRACT §4-12)."""

    id: str
    run_id: str
    work_request_id: str
    status: RunStatus
    steps: list[AgentStepResponse] = []
    all_done: bool = False
    poll_interval_ms: int = 2500
    started_at: KstDatetime | None = None
    finished_at: KstDatetime | None = None


class AgentRunDetail(AgentRunResponse):
    """상세 화면용 — 진행 상태에 결과까지 붙는다."""

    results: list[AgentResultResponse] = []


class AgentRunCreate(CamelModel):
    """`POST /agent-runs` body 는 `workRequestId` 하나뿐이다.

    나머지 컨텍스트(설비·라인·물질·운전조건·제품명·유형·스펙·사진 메타)는
    **서버가 workRequestId 로 스냅샷을 구성**해 에이전트에 넘긴다.
    """

    work_request_id: str = Field(examples=["3f8c…-uuid"])


# --- PATCH /agent-results/{id} -------------------------------------------------
class ResultItem(CamelModel):
    """A1·A2 항목형. `itemId` 가 없으면 신규 추가 — 서버가 채번한다."""

    item_id: str | None = None
    text: str = Field(min_length=1)
    edited: bool = False


class ResultDocument(CamelModel):
    """A3 문서형. `docId` 가 없으면 신규 추가 — 서버가 채번한다."""

    doc_id: str | None = None
    type: str = Field(min_length=1, examples=["WORK_PERMIT"])
    name: str = Field(min_length=1, examples=["작업허가서 초안"])
    content: str = ""
    edited: bool = False


class AgentResultUpdate(CamelModel):
    """**전체 치환(PUT-like).** 배열에 없는 기존 id 는 삭제된다 (CONTRACT §4-13)."""

    items: list[ResultItem] | None = None
    documents: list[ResultDocument] | None = None

    @model_validator(mode="after")
    def _exactly_one(self):
        if (self.items is None) == (self.documents is None):
            raise ValueError("items(A1·A2) 또는 documents(A3) 중 하나만 보내야 합니다")
        return self
