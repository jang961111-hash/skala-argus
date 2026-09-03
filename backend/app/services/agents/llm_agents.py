"""LLM 구현체 자리 (PoC 범위 밖 — NotImplementedError + TODO).

교체 지점: `app.services.agents.get_agent()` 가 Settings.ai_provider 가 LOCAL_LLM /
AX_PLATFORM / OPENAI 일 때 이 클래스들을 돌려준다. 오케스트레이터·라우터·스키마는
한 줄도 바뀌지 않는다. 프롬프트는 `docs/05_ai_ready/prompts.md` 에 버전으로 관리하고
`load_prompt(agent_code)` 로 읽는다 — 여기 하드코딩하지 않는다.

Security & Config Isolation: LLM 에이전트는 네트워크를 건드리기 전에 반드시
`settings.validate_egress()` 를 호출한다. LOCAL_LLM 은 사내 GPU 엔드포인트를 쓰고,
외부 provider 는 EGRESS_ALLOWED=true 가 있어야 한다.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from app.core.config import get_settings
from app.core.enums import AgentCode
from app.services.agents.base import AgentContext, AgentService


@lru_cache
def load_prompt(agent_code: str) -> str:
    """`docs/05_ai_ready/prompts.md` 의 `## …(\\`A1\\`)` 섹션을 읽는다."""
    path = get_settings().prompts_path
    if not path.exists():
        raise FileNotFoundError(f"prompt file not found: {path}")
    text = path.read_text(encoding="utf-8")
    m = re.search(rf"^##[^\n]*\(`{re.escape(agent_code)}`\)[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.S | re.M)
    if not m:
        raise KeyError(f"no '## {agent_code}' section in {path}")
    return m.group(1).strip()


class _LLMAgentBase(AgentService):
    def _client(self):
        settings = get_settings()
        settings.validate_egress()
        # TODO: settings.ai_provider 에 따라 클라이언트를 만든다
        #   LOCAL_LLM   -> OpenAI 호환 엔드포인트 (settings.local_llm_url, 사내 GPU)
        #   AX_PLATFORM -> SK AX 플랫폼 SDK
        #   OPENAI      -> openai.OpenAI(api_key=settings.openai_api_key)
        raise NotImplementedError("LLM client wiring is out of PoC scope")


class SpecLLMAgent(_LLMAgentBase):
    agent_code = AgentCode.A1

    def run(self, context: AgentContext) -> dict[str, Any]:
        # TODO: prompt = load_prompt("A1") + context.snapshot(제품유형·specJson·운전조건)
        #       → LLM → {"items":[{itemId,text,edited}]} 로 정규화 후 pydantic 검증
        raise NotImplementedError("SpecLLMAgent: TODO LLM + 스펙 대조 (부품 마스터 연동은 Phase 2)")


class LegalLLMAgent(_LLMAgentBase):
    agent_code = AgentCode.A2

    def run(self, context: AgentContext) -> dict[str, Any]:
        # TODO (RAG):
        #   1. 사내 법령 인덱스에서 설비·물질로 조문 후보를 검색 (온프레미스, 외부 전송 없음)
        #   2. prompt = load_prompt("A2").format(equipment=…, substance=…, law_excerpts=…)
        #   3. LLM → {"items":[…]}. 출처 조문이 없는 항목은 반환하지 않는다
        raise NotImplementedError("LegalLLMAgent: TODO LLM + 법령 인덱스 RAG (인덱스는 Phase 2)")


class SafetyDocLLMAgent(_LLMAgentBase):
    agent_code = AgentCode.A3

    def run(self, context: AgentContext) -> dict[str, Any]:
        # TODO: prompt = load_prompt("A3") + context.prior_results[AgentCode.A2] + 서류 템플릿
        #       → {"documents":[{docId,type,name,content,edited}]}
        raise NotImplementedError("SafetyDocLLMAgent: TODO LLM + 서류 템플릿")


LLM_AGENTS: dict[AgentCode, type[AgentService]] = {
    AgentCode.A1: SpecLLMAgent,
    AgentCode.A2: LegalLLMAgent,
    AgentCode.A3: SafetyDocLLMAgent,
}
