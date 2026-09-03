from __future__ import annotations

from app.core.config import get_settings
from app.core.enums import AgentCode
from app.services.agents.base import AgentContext, AgentService  # noqa: F401


def get_agent(agent_code: AgentCode, provider: str | None = None) -> AgentService:
    """팩토리: Settings(또는 호출자가 준 provider)에 따라 Mock / LLM 구현을 고른다.

    이 함수가 AI 확장 지점이다 — 오케스트레이터는 어떤 구현이 오는지 알지 못한다.
    """
    provider = (provider or get_settings().ai_provider).upper()
    if provider == "MOCK":
        from app.services.agents.mock_agents import MOCK_AGENTS

        return MOCK_AGENTS[agent_code]()
    from app.services.agents.llm_agents import LLM_AGENTS

    return LLM_AGENTS[agent_code]()
