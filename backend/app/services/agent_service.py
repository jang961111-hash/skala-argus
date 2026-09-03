"""AgentOrchestrator — run 생성 · step 진행 · 결과 편집 (CONTRACT §4-11~13).

Mock 진행 방식: `POST /agent-runs` 직후 step 3개가 전부 `WAITING` 이고, 이후
`GET /agent-runs/{runId}` 호출마다 다음 step 하나가 `DONE` 이 된다(A1→A2→A3).
셋 다 DONE 이면 run 은 `DONE`, work_request 는 `AI_DONE` 으로 넘어간다.
`BACKGROUND_ADVANCE=true` 면 GET 은 완전한 읽기 전용이 되고 BackgroundTasks 워커가
전이시킨다 — **GET 이 상태를 바꾸는 것은 Mock 단계의 의도된 설계이며 플래그로 끌 수 있다.**

`agent_steps`(진행)와 `agent_results`(결과)를 분리한 덕분에 폴링 UPDATE 와 편집 UPDATE 가
서로 다른 행을 건드린다.
"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import (
    AGENT_ORDER,
    AgentCode,
    AgentStepStatus,
    RESULT_EDITABLE_STATUSES,
    Role,
    RunStatus,
    WorkRequestStatus,
)
from app.core.errors import AppError, ErrorCode
from app.models import AgentResult, AgentRun, AgentStep, User
from app.repositories.agent_repo import AgentRepository
from app.repositories.work_request_repo import WorkRequestRepository
from app.schemas.agent import AgentResultUpdate
from app.services.agents import AgentContext, get_agent

log = logging.getLogger("replaceflow.agents")

ITEM_KEY_BY_AGENT = {AgentCode.A1: "items", AgentCode.A2: "items", AgentCode.A3: "documents"}
ID_KEY_BY_COLLECTION = {"items": "itemId", "documents": "docId"}
ID_PREFIX_BY_COLLECTION = {"items": "i", "documents": "d"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AgentOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AgentRepository(db)
        self.work_requests = WorkRequestRepository(db)
        self.settings = get_settings()

    # ------------------------------------------------------------------ create
    def create_run(self, wr_id: str, current: User) -> AgentRun:
        from app.services.work_request_service import WorkRequestService

        service = WorkRequestService(self.db)
        wr = service.get_for(wr_id, current)
        service.assert_owner(wr, current)
        if self.repo.running_run_for(wr.id) is not None:
            raise AppError(ErrorCode.RUN_ALREADY_IN_PROGRESS, "이미 진행 중인 AI 실행이 있습니다")
        if wr.status in {WorkRequestStatus.PENDING, WorkRequestStatus.APPROVED}:
            raise AppError(ErrorCode.IMMUTABLE_STATUS, f"{wr.status.value} 상태에서는 AI 를 다시 실행할 수 없습니다")
        service.assert_ready_for_run(wr)

        run = AgentRun(
            work_request_id=wr.id,
            status=RunStatus.RUNNING,
            started_at=_now(),
            input_snapshot=self.build_snapshot(wr),
        )
        self.db.add(run)
        self.db.flush()
        for code in AGENT_ORDER:
            self.db.add(AgentStep(run_id=run.id, agent_code=code, status=AgentStepStatus.WAITING))
        wr.status = WorkRequestStatus.AI_RUNNING
        wr.updated_at = _now()
        self.db.add(wr)
        return self.repo.save_run(run)

    def build_snapshot(self, wr) -> dict[str, Any]:
        """서버가 workRequestId 로 구성하는 입력 스냅샷 (CONTRACT §4-11).

        요청이 나중에 수정돼도 '무엇을 넣고 돌렸는지'가 run 에 남는다.
        """
        photos = self.work_requests.photos_for(wr.id)
        return {
            "workRequestId": wr.id,
            "requestNo": wr.request_no,
            "equipment": wr.equipment,
            "line": wr.line,
            "substance": wr.substance,
            "operatingCondition": wr.operating_condition,
            "productName": wr.product_name,
            "productType": wr.product_type.value if wr.product_type else None,
            "specJson": wr.spec_json,
            "symptom": wr.symptom,
            "siteMemo": wr.site_memo,
            "photos": [{"photoId": p.id, "fileName": p.file_name, "size": p.size} for p in photos],
        }

    # ----------------------------------------------------------------- advance
    def advance(self, run_id: str) -> AgentRun:
        """다음 WAITING step 하나를 완료한다. run 이 이미 끝났으면 아무것도 하지 않는다."""
        run = self.repo.get_run(run_id)
        if run is None:
            raise AppError(ErrorCode.AGENT_RUN_NOT_FOUND, "AI 실행 정보를 찾을 수 없습니다")
        if run.status is not RunStatus.RUNNING:
            return run

        steps = self.repo.steps_for(run.id)
        step = next((s for s in steps if s.status is AgentStepStatus.WAITING), None)
        if step is None:
            return self._finish(run, steps)

        wr = self.work_requests.get(run.work_request_id)
        prior = {r.agent_code: r.payload_json for r in self.repo.results_for(run.id)}
        context = AgentContext(
            db=self.db,
            run=run,
            work_request=wr,
            snapshot=run.input_snapshot or self.build_snapshot(wr),
            prior_results=prior,
        )
        step.status = AgentStepStatus.RUNNING
        step.started_at = _now()
        try:
            agent = get_agent(step.agent_code)
            payload = agent.run(context)
            self.db.add(
                AgentResult(
                    run_id=run.id,
                    agent_code=step.agent_code,
                    payload_json=payload,
                    original_json=payload,
                    edited=False,
                    updated_at=_now(),
                )
            )
            step.status = AgentStepStatus.DONE
            step.message = agent.message()
            step.finished_at = _now()
        except Exception as exc:  # noqa: BLE001 — 어떤 실패든 해당 step 만 FAILED, HTTP 는 200
            log.exception("agent %s failed", step.agent_code)
            step.status = AgentStepStatus.FAILED
            step.error_message = str(exc)
            step.finished_at = _now()
            run.status = RunStatus.FAILED
            run.finished_at = _now()
            self.db.add_all([step, run])
            return self.repo.save_run(run)

        self.db.add(step)
        self.db.flush()
        steps = self.repo.steps_for(run.id)
        if all(s.status is AgentStepStatus.DONE for s in steps):
            return self._finish(run, steps)
        return self.repo.save_run(run)

    def _finish(self, run: AgentRun, steps: list[AgentStep]) -> AgentRun:
        run.status = RunStatus.DONE
        run.finished_at = _now()
        wr = self.work_requests.get(run.work_request_id)
        if wr is not None and wr.status is WorkRequestStatus.AI_RUNNING:
            wr.status = WorkRequestStatus.AI_DONE
            wr.updated_at = run.finished_at
            self.db.add(wr)
        return self.repo.save_run(run)

    def advance_all_in_background(self, run_id: str, delay_sec: float = 2.0) -> None:
        """BACKGROUND_ADVANCE=true 일 때의 워커. step 하나를 delay_sec 간격으로 완료한다."""
        from app.db.session import SessionLocal

        for _ in AGENT_ORDER:
            time.sleep(delay_sec)
            db = SessionLocal()
            try:
                AgentOrchestrator(db).advance(run_id)
            finally:
                db.close()

    # ----------------------------------------------------------- 결과 편집
    def edit_result(self, result_id: str, body: AgentResultUpdate, current: User) -> AgentResult:
        """**전체 치환.** 배열에 없는 기존 id 는 삭제, id 없는 항목은 신규 추가(서버 채번)."""
        result = self.repo.get_result(result_id)
        if result is None:
            raise AppError(ErrorCode.AGENT_RUN_NOT_FOUND, "AI 결과를 찾을 수 없습니다")
        run = self.repo.get_run(result.run_id)
        wr = self.work_requests.get(run.work_request_id) if run else None
        if wr is None:
            raise AppError(ErrorCode.WORK_REQUEST_NOT_FOUND, "작업요청을 찾을 수 없습니다")
        if current.role is not Role.ENGINEER or wr.requester_id != current.id:
            raise AppError(ErrorCode.FORBIDDEN_NOT_OWNER, "본인이 등록한 요청의 결과만 수정할 수 있습니다")
        if wr.status not in RESULT_EDITABLE_STATUSES:
            raise AppError(ErrorCode.RESULT_LOCKED, f"{wr.status.value} 상태에서는 결과를 수정할 수 없습니다")

        collection = ITEM_KEY_BY_AGENT[result.agent_code]
        incoming = body.items if collection == "items" else body.documents
        if incoming is None:
            expected = "items" if collection == "items" else "documents"
            raise AppError(
                ErrorCode.VALIDATION_FAILED,
                f"{result.agent_code.value} 결과는 `{expected}` 배열로 보내야 합니다",
                [{"field": expected, "message": "필수 항목"}],
            )

        payload, edited = self._replace_collection(result, collection, [e.model_dump(by_alias=True) for e in incoming])
        result.payload_json = payload
        result.edited = edited
        result.updated_at = _now()
        return self.repo.save_result(result)

    @staticmethod
    def _replace_collection(
        result: AgentResult, collection: str, incoming: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], bool]:
        id_key = ID_KEY_BY_COLLECTION[collection]
        prefix = ID_PREFIX_BY_COLLECTION[collection]
        original = {
            entry.get(id_key): entry
            for entry in ((result.original_json or {}).get(collection) or [])
            if entry.get(id_key)
        }
        previous = {
            entry.get(id_key): entry
            for entry in ((result.payload_json or {}).get(collection) or [])
            if entry.get(id_key)
        }

        used = set(original) | set(previous) | {e.get(id_key) for e in incoming if e.get(id_key)}
        seq = max((int(m.group(1)) for i in used if i and (m := re.fullmatch(rf"{prefix}-(\d+)", str(i)))), default=0)

        body_field = "text" if collection == "items" else "content"
        entries: list[dict[str, Any]] = []
        changed = len(incoming) != len(previous)
        for entry in incoming:
            entry = dict(entry)
            entry_id = entry.get(id_key)
            if not entry_id:
                seq += 1
                entry_id = f"{prefix}-{seq:02d}"
                entry[id_key] = entry_id
                entry["edited"] = True  # 신규 추가는 언제나 사람이 손댄 것
                changed = True
            else:
                source = original.get(entry_id)
                if source is None:
                    entry["edited"] = True  # 원본에 없던 id → 사람이 넣은 것
                    changed = True
                else:
                    is_edited = any(entry.get(k) != source.get(k) for k in (body_field, "type", "name") if k in entry)
                    entry["edited"] = bool(is_edited)
                    changed = changed or is_edited
            entries.append(entry)

        # 원본에 있었는데 이번 배열에 없는 항목은 삭제된 것이다
        if set(original) - {e.get(id_key) for e in entries}:
            changed = True
        return {collection: entries}, changed


# --------------------------------------------------------------- serializers
def _step_to_schema(step: AgentStep) -> dict[str, Any]:
    return {
        "agentCode": step.agent_code,
        "status": step.status,
        "message": step.message,
        "errorMessage": step.error_message,
        "startedAt": step.started_at,
        "finishedAt": step.finished_at,
    }


def result_to_schema(result: AgentResult, *, editable: bool) -> dict[str, Any]:
    return {
        "id": result.id,
        "agentResultId": result.id,
        "agentCode": result.agent_code,
        "payloadJson": result.payload_json or {},
        "edited": result.edited,
        "editable": editable,
        "updatedAt": result.updated_at,
    }


def run_to_response(db: Session, run: AgentRun) -> dict[str, Any]:
    """폴링 응답 (CONTRACT §4-12) — steps + allDone + pollIntervalMs."""
    steps = AgentRepository(db).steps_for(run.id)
    return {
        "id": run.id,
        "runId": run.id,
        "workRequestId": run.work_request_id,
        "status": run.status,
        "steps": [_step_to_schema(s) for s in steps],
        "allDone": bool(steps) and all(s.status is AgentStepStatus.DONE for s in steps),
        "pollIntervalMs": get_settings().poll_interval_ms,
        "startedAt": run.started_at,
        "finishedAt": run.finished_at,
    }


def run_to_detail(db: Session, run: AgentRun, *, editable: bool) -> dict[str, Any]:
    """상세 화면용 — 진행 상태에 결과까지. SAFETY_MANAGER 조회면 editable 은 항상 False."""
    results = AgentRepository(db).results_for(run.id)
    return {
        **run_to_response(db, run),
        "results": [result_to_schema(r, editable=editable) for r in results],
    }
