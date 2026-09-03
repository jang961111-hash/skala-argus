"""WorkRequestService — 작업요청 생성·조회·수정·제출 (CONTRACT §4-5~8, §4-14).

계약의 두 규칙이 이 파일 전체를 지배한다.
1. **DRAFT 를 허용하려고 DB 는 NOT NULL 을 걸지 않는다.** `draft=false` 조건부 필수 검증과
   productType 별 specJson 스키마 검증은 전부 여기(서비스 계층)에 있다.
2. **권한은 조회 시점에 건다.** ENGINEER 는 본인 요청만, SAFETY_MANAGER 는 PENDING 이상만.
   위반은 403 `FORBIDDEN_NOT_OWNER`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.enums import (
    AgentCode,
    EDITABLE_STATUSES,
    NextAction,
    PRODUCT_SPEC_KEYS,
    RESULT_EDITABLE_STATUSES,
    Role,
    SAFETY_VISIBLE_STATUSES,
    WorkRequestStatus,
)
from app.core.errors import AppError, ErrorCode
from app.models import User, WorkRequest
from app.repositories.agent_repo import AgentRepository
from app.repositories.approval_repo import ApprovalRepository
from app.repositories.request_no import insert_with_request_no
from app.repositories.user_repo import UserRepository
from app.repositories.work_request_repo import SORTABLE, WorkRequestRepository
from app.schemas.page import page_meta
from app.schemas.work_request import WorkRequestCreate, WorkRequestPatch

#: `draft=false` 로 생성하거나 AI 를 돌리려면 채워져 있어야 하는 필드 (CONTRACT §4-5)
REQUIRED_FOR_SUBMIT = (
    "equipment",
    "line",
    "substance",
    "operating_condition",
    "product_name",
    "product_type",
    "spec_json",
)
FIELD_ALIASES = {
    "equipment": "equipment",
    "line": "line",
    "substance": "substance",
    "operating_condition": "operatingCondition",
    "product_name": "productName",
    "product_type": "productType",
    "spec_json": "specJson",
}

NEXT_ACTION_BY_STATUS = {
    WorkRequestStatus.DRAFT: NextAction.CONTINUE,
    WorkRequestStatus.AI_RUNNING: NextAction.RUN,
    WorkRequestStatus.AI_DONE: NextAction.RESULT,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def next_action_for(status: WorkRequestStatus) -> NextAction:
    return NEXT_ACTION_BY_STATUS.get(status, NextAction.DETAIL)


def validate_spec_schema(product_type, spec_json: dict[str, Any] | None) -> None:
    """productType 별 필수 키 검증 (CONTRACT §2). 불일치 시 400 SPEC_SCHEMA_MISMATCH."""
    if product_type is None:
        return
    required = PRODUCT_SPEC_KEYS[product_type]
    spec = spec_json or {}
    missing = [key for key in required if not str(spec.get(key) or "").strip()]
    if missing:
        raise AppError(
            ErrorCode.SPEC_SCHEMA_MISMATCH,
            f"{product_type.value} 유형은 {', '.join(required)} 키가 필요합니다",
            [{"field": f"specJson.{k}", "message": "필수 항목"} for k in missing],
        )


class WorkRequestService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = WorkRequestRepository(db)
        self.users = UserRepository(db)
        self.agents = AgentRepository(db)
        self.approvals = ApprovalRepository(db)

    # ------------------------------------------------------------ 권한 게이트
    def get_for(self, wr_id: str, current: User) -> WorkRequest:
        wr = self.repo.get(wr_id)
        if wr is None:
            raise AppError(ErrorCode.WORK_REQUEST_NOT_FOUND, "작업요청을 찾을 수 없습니다")
        self.assert_can_read(wr, current)
        return wr

    @staticmethod
    def assert_can_read(wr: WorkRequest, current: User) -> None:
        if current.role is Role.ENGINEER:
            if wr.requester_id != current.id:
                raise AppError(ErrorCode.FORBIDDEN_NOT_OWNER, "본인이 등록한 요청만 조회할 수 있습니다")
        elif wr.status not in SAFETY_VISIBLE_STATUSES:
            raise AppError(ErrorCode.FORBIDDEN_NOT_OWNER, "승인 대기 이후 요청만 조회할 수 있습니다")

    @staticmethod
    def assert_owner(wr: WorkRequest, current: User) -> None:
        if wr.requester_id != current.id:
            raise AppError(ErrorCode.FORBIDDEN_NOT_OWNER, "본인이 등록한 요청만 수정할 수 있습니다")

    # ---------------------------------------------------------------- create
    def create(self, body: WorkRequestCreate, current: User) -> WorkRequest:
        wr = WorkRequest(
            requester_id=current.id,
            equipment=body.equipment,
            line=body.line,
            substance=body.substance,
            operating_condition=body.operating_condition.model_dump(by_alias=True) if body.operating_condition else None,
            product_name=body.product_name,
            product_type=body.product_type,
            spec_json=body.spec_json,
            symptom=body.symptom,
            site_memo=body.site_memo,
            status=WorkRequestStatus.DRAFT,
            created_at=_now(),
            updated_at=_now(),
        )
        if not body.draft:
            # 요청 등록의 필수값 누락은 입력 유효성 오류다 (CONTRACT §4-5)
            self._require_complete(wr, ErrorCode.VALIDATION_FAILED)
            validate_spec_schema(wr.product_type, wr.spec_json)
        return insert_with_request_no(self.db, wr)

    @staticmethod
    def _require_complete(wr: WorkRequest, code: ErrorCode) -> None:
        """필수 업무 필드 확인. **오류 코드는 호출자가 정한다.**

        같은 검증이지만 의미가 다르다 — 등록 시점의 누락은 400 `VALIDATION_FAILED`,
        미완성 요청으로 AI 를 돌리려는 시도는 400 `WORK_REQUEST_INCOMPLETE` 다.
        """
        missing = [f for f in REQUIRED_FOR_SUBMIT if not getattr(wr, f)]
        if missing:
            raise AppError(
                code,
                "필수 입력값이 비어 있습니다: " + ", ".join(FIELD_ALIASES[f] for f in missing),
                [{"field": FIELD_ALIASES[f], "message": "필수 항목"} for f in missing],
            )

    def assert_ready_for_run(self, wr: WorkRequest) -> None:
        """AI 실행 전 필수값·스펙 스키마 확인 (400 WORK_REQUEST_INCOMPLETE / SPEC_SCHEMA_MISMATCH)."""
        self._require_complete(wr, ErrorCode.WORK_REQUEST_INCOMPLETE)
        validate_spec_schema(wr.product_type, wr.spec_json)

    # ----------------------------------------------------------------- patch
    def patch(self, wr_id: str, body: WorkRequestPatch, current: User) -> WorkRequest:
        wr = self.get_for(wr_id, current)
        self.assert_owner(wr, current)
        if wr.status not in EDITABLE_STATUSES:
            raise AppError(
                ErrorCode.IMMUTABLE_STATUS,
                f"{wr.status.value} 상태의 요청은 수정할 수 없습니다",
            )
        data = body.model_dump(exclude_unset=True)
        if "operating_condition" in data and body.operating_condition is not None:
            data["operating_condition"] = body.operating_condition.model_dump(by_alias=True)
        for key, value in data.items():
            setattr(wr, key, value)
        # 유형이나 스펙을 건드렸으면 스키마를 다시 본다
        if ("product_type" in data or "spec_json" in data) and wr.product_type is not None:
            validate_spec_schema(wr.product_type, wr.spec_json)
        wr.updated_at = _now()
        return self.repo.save(wr)

    # ------------------------------------------------------------------ list
    def list(
        self,
        *,
        current: User,
        mine: bool,
        status_param: str | None,
        page: int,
        size: int,
        sort: str,
    ) -> dict[str, Any]:
        statuses = self._parse_statuses(status_param)
        sort_field, sort_desc = self._parse_sort(sort)

        if current.role is Role.ENGINEER:
            # 엔지니어는 mine 여부와 무관하게 본인 것만 볼 수 있다
            requester_id, visible = current.id, None
        else:
            requester_id = current.id if mine else None
            visible = SAFETY_VISIBLE_STATUSES

        rows, total = self.repo.list(
            statuses=statuses,
            requester_id=requester_id,
            visible_statuses=visible,
            page=page,
            size=size,
            sort_field=sort_field,
            sort_desc=sort_desc,
        )
        return {"content": [self.to_summary(wr) for wr in rows], "page": page_meta(page, size, total)}

    @staticmethod
    def _parse_statuses(status_param: str | None) -> list[WorkRequestStatus] | None:
        """`status` 는 콤마 다중 지정이 가능하다 (`REJECTED,DRAFT`)."""
        if not status_param:
            return None
        out: list[WorkRequestStatus] = []
        for raw in status_param.split(","):
            token = raw.strip().upper()
            if not token:
                continue
            try:
                out.append(WorkRequestStatus(token))
            except ValueError as exc:
                raise AppError(
                    ErrorCode.VALIDATION_FAILED,
                    f"알 수 없는 상태값입니다: {token}",
                    [{"field": "status", "message": f"허용되지 않는 값: {token}"}],
                ) from exc
        return out or None

    @staticmethod
    def _parse_sort(sort: str) -> tuple[str, bool]:
        field, _, direction = sort.partition(",")
        field = field.strip() or "createdAt"
        if field not in SORTABLE:
            raise AppError(
                ErrorCode.VALIDATION_FAILED,
                f"정렬할 수 없는 필드입니다: {field}",
                [{"field": "sort", "message": f"허용: {', '.join(SORTABLE)}"}],
            )
        return field, direction.strip().lower() != "asc"

    # ------------------------------------------------------------ serializers
    def to_summary(self, wr: WorkRequest) -> dict[str, Any]:
        requester = self.users.get(wr.requester_id)
        return {
            "id": wr.id,
            "workRequestId": wr.id,
            "requestNo": wr.request_no,
            "requesterId": wr.requester_id,
            "requesterName": requester.name if requester else None,
            "equipment": wr.equipment,
            "line": wr.line,
            "substance": wr.substance,
            "productName": wr.product_name,
            "productType": wr.product_type,
            "symptom": wr.symptom,
            "status": wr.status,
            "nextAction": next_action_for(wr.status),
            "createdAt": wr.created_at,
            "updatedAt": wr.updated_at,
            "submittedAt": wr.submitted_at,
        }

    def to_detail(self, wr: WorkRequest, current: User) -> dict[str, Any]:
        from app.services.agent_service import run_to_detail
        from app.services.approval_service import approval_to_schema
        from app.services.photo_service import photo_to_schema

        run = self.agents.latest_run_for(wr.id)
        approval = self.approvals.latest_for(wr.id)
        editable = (
            current.role is Role.ENGINEER
            and wr.requester_id == current.id
            and wr.status in RESULT_EDITABLE_STATUSES
        )
        return {
            **self.to_summary(wr),
            "operatingCondition": wr.operating_condition,
            "specJson": wr.spec_json,
            "siteMemo": wr.site_memo,
            "engineerNote": wr.engineer_note,
            "agentRun": run_to_detail(self.db, run, editable=editable) if run else None,
            "approval": approval_to_schema(approval, self.users.get(approval.approver_id)) if approval else None,
            "photos": [photo_to_schema(p) for p in self.repo.photos_for(wr.id)],
        }

    # ------------------------------------------------------- submit-approval
    def submit_approval(self, wr_id: str, current: User) -> WorkRequest:
        """AI_DONE·REJECTED → PENDING. 서버 검증 4가지 (CONTRACT §4-14).

        재제출도 같은 API 다. 직전 approval 이력은 append-only 라 그대로 보존된다.
        """
        wr = self.get_for(wr_id, current)
        self.assert_owner(wr, current)

        problems: list[dict] = []
        if wr.status not in {WorkRequestStatus.AI_DONE, WorkRequestStatus.REJECTED}:
            problems.append({"field": "status", "message": f"{wr.status.value} 상태에서는 제출할 수 없습니다"})
        if not (wr.engineer_note or "").strip():
            problems.append({"field": "engineerNote", "message": "엔지니어 노트를 작성해야 합니다"})

        run = self.agents.latest_run_for(wr.id)
        results = {r.agent_code: r for r in (self.agents.results_for(run.id) if run else [])}
        missing_agents = [code.value for code in (AgentCode.A1, AgentCode.A2, AgentCode.A3) if code not in results]
        if missing_agents:
            problems.append({"field": "agentResults", "message": f"AI 결과가 없습니다: {', '.join(missing_agents)}"})
        else:
            laws = (results[AgentCode.A2].payload_json or {}).get("items") or []
            if len(laws) < 1:
                problems.append({"field": "agentResults.A2", "message": "적용 법령이 1건 이상이어야 합니다"})

        if problems:
            raise AppError(
                ErrorCode.SUBMIT_REQUIRED_FIELD_MISSING,
                "제출 요건을 충족하지 않았습니다",
                problems,
            )

        wr.status = WorkRequestStatus.PENDING
        wr.submitted_at = _now()
        wr.updated_at = wr.submitted_at
        return self.repo.save(wr)
