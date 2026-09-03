"""도메인 Enum (CONTRACT §2 — 정확히 이 문자열).

모델(SQLAlchemy)과 스키마(Pydantic)가 같은 정의를 공유한다. PostgreSQL 에서는
네이티브 enum 타입으로, SQLite 에서는 VARCHAR + CHECK 로 매핑된다.
"""
from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    ENGINEER = "ENGINEER"
    SAFETY_MANAGER = "SAFETY_MANAGER"


class WorkRequestStatus(str, Enum):
    DRAFT = "DRAFT"
    AI_RUNNING = "AI_RUNNING"
    AI_DONE = "AI_DONE"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ProductType(str, Enum):
    VALVE = "VALVE"
    FITTING_TUBE = "FITTING_TUBE"
    REGULATOR = "REGULATOR"
    FILTER = "FILTER"
    ETC = "ETC"


class AgentCode(str, Enum):
    A1 = "A1"  # 규격·호환 (입력 스펙 기반)
    A2 = "A2"  # 법령·조문
    A3 = "A3"  # 안전서류 (허가서·위험성평가)


class AgentStepStatus(str, Enum):
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class RunStatus(str, Enum):
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class ApprovalDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class NextAction(str, Enum):
    """목록 항목의 다음 액션 — 서버가 계산한다 (CONTRACT §4-6).

    값은 FE `constants/domain.js` 의 `NEXT_ACTION` 과 같은 어휘를 쓴다. 프론트는
    이 값으로 라벨·경로만 매핑하고 상태로 직접 분기하지 않는다.
    """

    CONTINUE = "CONTINUE"  # DRAFT → 이어서 작성 (E_02)
    RUN = "RUN"  # AI_RUNNING → 진행 화면 (E_03)
    RESULT = "RESULT"  # AI_DONE → 결과 확인 (E_04)
    DETAIL = "DETAIL"  # 그 외 → 상세


# 에이전트 실행 순서 (고정 3종)
AGENT_ORDER: list[AgentCode] = [AgentCode.A1, AgentCode.A2, AgentCode.A3]

# productType → specJson 필수 키 (CONTRACT §2). 불일치 시 400 SPEC_SCHEMA_MISMATCH
PRODUCT_SPEC_KEYS: dict[ProductType, tuple[str, ...]] = {
    ProductType.VALVE: ("pressureRating",),
    ProductType.FITTING_TUBE: ("connectionStandard", "material"),
    ProductType.REGULATOR: ("pressureRating",),
    ProductType.FILTER: ("substanceType",),
    ProductType.ETC: ("freeSpec",),
}

# SAFETY_MANAGER 가 조회할 수 있는 범위 — "PENDING 이상" (CONTRACT §1 권한)
SAFETY_VISIBLE_STATUSES = frozenset(
    {WorkRequestStatus.PENDING, WorkRequestStatus.APPROVED, WorkRequestStatus.REJECTED}
)

# 엔지니어가 수정할 수 있는 상태. PENDING·APPROVED 는 409 IMMUTABLE_STATUS
EDITABLE_STATUSES = frozenset(
    {WorkRequestStatus.DRAFT, WorkRequestStatus.AI_RUNNING, WorkRequestStatus.AI_DONE, WorkRequestStatus.REJECTED}
)

# 결과 편집이 가능한 상태. 그 외는 409 RESULT_LOCKED
RESULT_EDITABLE_STATUSES = frozenset({WorkRequestStatus.AI_DONE, WorkRequestStatus.REJECTED})
