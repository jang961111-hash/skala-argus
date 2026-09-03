"""CONTRACT §5 — 테이블 7개.

설비·부품 마스터, 호환표, 법령 인덱스, 문서 마스터, 테넌트, 감사 로그는 **Phase 2** 이며
이번 범위에 없다(ERD 문서 명시). 설비·라인·물질은 `work_requests` 의 varchar 컬럼이다.
"""
from app.models.user import User  # noqa: F401
from app.models.work_request import WorkRequest, WorkRequestPhoto  # noqa: F401
from app.models.agent import AgentRun, AgentStep, AgentResult  # noqa: F401
from app.models.approval import Approval  # noqa: F401

__all__ = [
    "User",
    "WorkRequest",
    "WorkRequestPhoto",
    "AgentRun",
    "AgentStep",
    "AgentResult",
    "Approval",
]
