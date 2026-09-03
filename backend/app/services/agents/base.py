"""AgentService interface (Interface First — 기획서 7장).

The orchestrator only knows this interface. Mock implementations return the
fixed JSON from docs/CONTRACT.md; LLM implementations (llm_agents.py) will be
swapped in via app.services.agents.get_agent() based on Settings.ai_provider /
ai_configs.provider without changing the orchestrator or the API.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models import AgentRun, Equipment, Part, WorkRequest


@dataclass
class AgentContext:
    """Everything an agent may need. Prior step results are passed so A3 can use A2 output, A4 can use A1."""

    db: Session
    run: AgentRun
    work_request: WorkRequest
    equipment: Equipment | None
    part: Part | None
    prior_results: dict[str, dict[str, Any]] = field(default_factory=dict)


class AgentService(ABC):
    agent_type: str  # SPEC | LEGAL | SAFETY_DOC | VENDOR

    @abstractmethod
    def run(self, context: AgentContext) -> dict[str, Any]:
        """Execute the agent and return the `result` JSON for its step."""
        raise NotImplementedError
