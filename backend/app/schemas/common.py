from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class WorkRequestStatus(str, Enum):
    REQUESTED = "REQUESTED"
    RUNNING = "RUNNING"
    REVIEW = "REVIEW"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DONE = "DONE"


class OverallStatus(str, Enum):
    RUNNING = "RUNNING"
    REVIEW = "REVIEW"
    FAILED = "FAILED"


class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class AgentType(str, Enum):
    SPEC = "SPEC"
    LEGAL = "LEGAL"
    SAFETY_DOC = "SAFETY_DOC"
    VENDOR = "VENDOR"


class UserRole(str, Enum):
    ENGINEER = "ENGINEER"
    SAFETY_MANAGER = "SAFETY_MANAGER"
    BUYER = "BUYER"
    ADMIN = "ADMIN"


class Decision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_INFO = "REQUEST_INFO"


class DocumentType(str, Enum):
    WORK_PERMIT = "WORK_PERMIT"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    LOTO_CHECKLIST = "LOTO_CHECKLIST"
    RFQ = "RFQ"


class PartGrade(str, Enum):
    OEM = "OEM"
    EQUIVALENT = "EQUIVALENT"
    REFURB = "REFURB"


class AiProvider(str, Enum):
    LOCAL_LLM = "LOCAL_LLM"
    AX_PLATFORM = "AX_PLATFORM"
    OPENAI = "OPENAI"


AGENT_ORDER = [AgentType.SPEC, AgentType.LEGAL, AgentType.SAFETY_DOC, AgentType.VENDOR]
CHECKLIST_KEYS = ["WORK_PERMIT", "RISK_ASSESSMENT", "LOTO_GAS_ISOLATION", "GAS_DETECTOR_CHECK"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    detail: str
