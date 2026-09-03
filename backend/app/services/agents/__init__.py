from __future__ import annotations

from app.core.config import get_settings
from app.services.agents.base import AgentContext, AgentService  # noqa: F401


def get_agent(agent_type: str, provider: str | None = None) -> AgentService:
    """Factory: pick Mock or LLM implementation from settings / ai_configs.provider."""
    provider = (provider or get_settings().ai_provider).upper()
    if provider == "MOCK":
        from app.services.agents.mock_agents import MOCK_AGENTS

        return MOCK_AGENTS[agent_type]()
    from app.services.agents.llm_agents import LLM_AGENTS

    return LLM_AGENTS[agent_type]()
