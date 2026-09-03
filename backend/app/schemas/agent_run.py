from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import AgentType, OverallStatus, StepStatus


class AgentStep(BaseModel):
    agent: AgentType
    status: StepStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


class AgentRun(BaseModel):
    run_id: str
    work_request_id: str
    overall_status: OverallStatus
    steps: list[AgentStep]
    summary: str | None = None
    approval_required_by: str = "SAFETY_MANAGER"
    model_name: str
    prompt_version: str
    created_at: datetime
    completed_at: datetime | None = None


class AgentRunAccepted(BaseModel):
    run_id: str = Field(examples=["RUN-0042"])
    overall_status: OverallStatus = OverallStatus.RUNNING
