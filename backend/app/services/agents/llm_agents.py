"""LLM implementations of the AgentService interface (NOT implemented in PoC).

Swap-in point: app.services.agents.get_agent() returns these classes when
Settings.ai_provider (or ai_configs.provider for the tenant) is LOCAL_LLM /
AX_PLATFORM / OPENAI. Prompts are versioned in docs/05_ai_ready/prompts.md and
loaded via `load_prompt(agent_type)` — never hard-coded here.

Security & Config Isolation: an LLM agent must call `settings.validate_egress()`
before touching any network; LOCAL_LLM uses Settings.local_llm_url, external
providers require EGRESS_ALLOWED=true.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from app.core.config import get_settings
from app.services.agents.base import AgentContext, AgentService


@lru_cache
def load_prompt(agent_type: str) -> str:
    """Read the `## <AGENT_TYPE>` section of docs/05_ai_ready/prompts.md."""
    path = get_settings().prompts_path
    if not path.exists():
        raise FileNotFoundError(f"prompt file not found: {path}")
    text = path.read_text(encoding="utf-8")
    m = re.search(rf"^##[^\n]*\(`{re.escape(agent_type)}`\)[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.S | re.M)
    if not m:
        raise KeyError(f"no '## {agent_type}' section in {path}")
    return m.group(1).strip()


class _LLMAgentBase(AgentService):
    def _client(self):
        settings = get_settings()
        settings.validate_egress()
        # TODO: return an LLM client based on settings.ai_provider
        #   LOCAL_LLM  -> OpenAI-compatible endpoint at settings.local_llm_url (사내 GPU)
        #   AX_PLATFORM-> SK AX platform SDK
        #   OPENAI     -> openai.OpenAI(api_key=settings.openai_api_key)
        raise NotImplementedError("LLM client wiring is out of PoC scope")


class SpecLLMAgent(_LLMAgentBase):
    agent_type = "SPEC"

    def run(self, context: AgentContext) -> dict[str, Any]:
        # TODO: build prompt = load_prompt("SPEC") + BOM/part spec/vendor catalog (사내 DB) → LLM → JSON
        #       validate output with pydantic before returning {spec_match, current_part, alternatives[]}
        raise NotImplementedError("SpecLLMAgent: TODO LLM + BOM lookup")


class LegalLLMAgent(_LLMAgentBase):
    agent_type = "LEGAL"

    def run(self, context: AgentContext) -> dict[str, Any]:
        # TODO (RAG):
        #   1. retrieve law excerpts from law_index (MasterRepository.search_laws or a vector DB)
        #      filtered by equipment.type and equipment.substances  — index is on-premise, no egress
        #   2. prompt = load_prompt("LEGAL").format(equipment=..., substances=..., work_type=..., law_excerpts=...)
        #   3. LLM → JSON {applicable_laws[], required_procedures[]}; entries without a citation → required="UNKNOWN"
        #   4. persist as legal_findings rows (조문 단위 추적) exactly as LegalMockAgent does
        raise NotImplementedError("LegalLLMAgent: TODO LLM + RAG over law_index")


class SafetyDocLLMAgent(_LLMAgentBase):
    agent_type = "SAFETY_DOC"

    def run(self, context: AgentContext) -> dict[str, Any]:
        # TODO: prompt = load_prompt("SAFETY_DOC") + context.prior_results["LEGAL"] + 서류 템플릿
        #       → generate WORK_PERMIT / RISK_ASSESSMENT / LOTO_CHECKLIST drafts → Document rows → {documents[]}
        raise NotImplementedError("SafetyDocLLMAgent: TODO LLM + document templates")


class VendorLLMAgent(_LLMAgentBase):
    agent_type = "VENDOR"

    def run(self, context: AgentContext) -> dict[str, Any]:
        # TODO: prompt = load_prompt("VENDOR") + context.prior_results["SPEC"] + 구매 이력(ERP)
        #       → RFQ draft Document + {rfq_doc_id, rfq_summary, lead_time_est_days, last_purchase}
        raise NotImplementedError("VendorLLMAgent: TODO LLM + purchase history")


LLM_AGENTS: dict[str, type[AgentService]] = {
    "SPEC": SpecLLMAgent,
    "LEGAL": LegalLLMAgent,
    "SAFETY_DOC": SafetyDocLLMAgent,
    "VENDOR": VendorLLMAgent,
}
