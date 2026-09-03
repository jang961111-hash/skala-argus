"""AgentService 인터페이스 (Interface First — 기획서 7장).

오케스트레이터는 이 인터페이스만 안다. Mock 구현은 고정 결과를 돌려주고, LLM 구현
(`llm_agents.py`)은 `app.services.agents.get_agent()` 가 Settings.ai_provider 에 따라
갈아끼운다 — 오케스트레이터도 API 도 바뀌지 않는다. 이것이 AI 확장 지점이다.

payload 통일 구조 (CONTRACT §4-13):
  A1·A2 → {"items": [{"itemId", "text", "edited"}]}
  A3    → {"documents": [{"docId", "type", "name", "content", "edited"}]}
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.core.enums import AgentCode
from app.models import AgentRun, WorkRequest


@dataclass
class AgentContext:
    """에이전트가 볼 수 있는 전부.

    `snapshot` 은 서버가 workRequestId 로 구성한 입력 스냅샷이다(설비·라인·물질·운전조건·
    제품명·유형·스펙·사진 메타). `prior_results` 로 A3 가 A2 산출을 이어받는다.
    """

    db: Session
    run: AgentRun
    work_request: WorkRequest
    snapshot: dict[str, Any]
    prior_results: dict[AgentCode, dict[str, Any]] = field(default_factory=dict)


class AgentService(ABC):
    agent_code: AgentCode

    @abstractmethod
    def run(self, context: AgentContext) -> dict[str, Any]:
        """에이전트를 실행하고 이 step 의 `payload_json` 을 돌려준다."""
        raise NotImplementedError

    def message(self) -> str:
        """진행 화면(E_03)에 띄울 한 줄. `agent_steps.message` 로 저장된다."""
        return ""


def item(index: int, text: str) -> dict[str, Any]:
    return {"itemId": f"i-{index:02d}", "text": text, "edited": False}


def document(index: int, doc_type: str, name: str, content: str) -> dict[str, Any]:
    return {"docId": f"d-{index:02d}", "type": doc_type, "name": name, "content": content, "edited": False}
