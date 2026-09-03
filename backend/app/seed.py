"""데모용 시드 데이터. 비어 있을 때만 넣는다(멱등).

v3.0 계약에는 샘플 데이터 절이 없다. 화면 9종을 전부 그려볼 수 있도록 **6개 상태를 각 1건씩**
만들어 둔다. 비밀번호는 전부 `Passw0rd!` 이며 bcrypt 해시로만 저장한다.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import (
    AgentCode,
    AgentStepStatus,
    ApprovalDecision,
    ProductType,
    Role,
    RunStatus,
    WorkRequestStatus,
)
from app.core.security import hash_password
from app.models import AgentResult, AgentRun, AgentStep, Approval, User, WorkRequest
from app.services.agents.base import AgentContext
from app.services.agents.mock_agents import LegalMockAgent, SafetyDocMockAgent, SpecMockAgent

KST = timezone(timedelta(hours=9))
SEED_PASSWORD = "Passw0rd!"

ENGINEER_EMAIL = "engineer@argus.test"
SAFETY_EMAIL = "safety@argus.test"


def seed_if_empty(db: Session) -> bool:
    if db.scalar(select(User).limit(1)) is not None:
        return False
    seed(db)
    return True


def _valve(pressure: str = "3000 psi") -> dict:
    return {
        "equipment": "가스캐비닛#2",
        "line": "A라인",
        "substance": "SiH4",
        "operating_condition": {"temperature": "상온", "pressure": pressure},
        "product_name": "SS-8-VCR",
        "product_type": ProductType.VALVE,
        "spec_json": {"pressureRating": pressure},
    }


def seed(db: Session) -> None:
    base = datetime(2026, 9, 3, 9, 0, tzinfo=KST)

    engineer = User(
        name="김민준", email=ENGINEER_EMAIL, password_hash=hash_password(SEED_PASSWORD),
        role=Role.ENGINEER, created_at=base,
    )
    safety = User(
        name="이정호", email=SAFETY_EMAIL, password_hash=hash_password(SEED_PASSWORD),
        role=Role.SAFETY_MANAGER, created_at=base,
    )
    db.add_all([engineer, safety])
    db.flush()

    day = base.strftime("%Y%m%d")
    seq = iter(range(1, 100))

    def make(status: WorkRequestStatus, created: datetime, **overrides) -> WorkRequest:
        fields = {**_valve(), **overrides}
        wr = WorkRequest(
            request_no=f"WR-{day}-{next(seq):03d}",
            requester_id=engineer.id,
            status=status,
            created_at=created,
            updated_at=created,
            **fields,
        )
        db.add(wr)
        db.flush()
        return wr

    note = "압력 등급 상향분을 반영했습니다. 제92조 운전정지·LOTO 적용이 필요하다고 판단합니다."

    w_draft = make(
        WorkRequestStatus.DRAFT, base + timedelta(hours=1),
        symptom="밸브 미세 누설 의심 (작성 중)", site_memo=None,
        product_type=ProductType.ETC, spec_json={"freeSpec": "현장 재확인 후 확정"},
    )
    w_running = make(
        WorkRequestStatus.AI_RUNNING, base + timedelta(hours=2),
        symptom="2차 압력 불안정", site_memo="조정기 출력 압력 흔들림",
        product_name="REG-2S", product_type=ProductType.REGULATOR, spec_json={"pressureRating": "250 psi"},
    )
    w_done = make(
        WorkRequestStatus.AI_DONE, base + timedelta(hours=3),
        symptom="차압 상승", site_memo="필터 막힘 확인", engineer_note=note,
        equipment="스크러버#1", line="C라인", product_name="FLT-IL-003",
        product_type=ProductType.FILTER, spec_json={"substanceType": "N2"},
    )
    w_pending = make(
        WorkRequestStatus.PENDING, base + timedelta(hours=4),
        symptom="밸브 개폐 지연", site_memo="액추에이터 응답 지연 확인", engineer_note=note,
    )
    w_approved = make(
        WorkRequestStatus.APPROVED, base - timedelta(days=1),
        symptom="가스 유량 이상, 밸브 누설 의심", site_memo="현장 확인 결과 밸브 시트 마모", engineer_note=note,
    )
    w_rejected = make(
        WorkRequestStatus.REJECTED, base - timedelta(hours=20),
        symptom="누설 감지기 경보(미세)", site_memo="육안 확인 중", engineer_note="호환품으로 대체 요청합니다.",
        substance="NH3", line="B라인", product_name="SS-6-VCR-EQ", spec_json={"pressureRating": "2500 psi"},
    )
    w_pending.submitted_at = w_pending.created_at + timedelta(minutes=30)
    w_approved.submitted_at = w_approved.created_at + timedelta(minutes=30)
    w_rejected.submitted_at = w_rejected.created_at + timedelta(minutes=30)

    # --- agent runs -----------------------------------------------------------
    def snapshot(wr: WorkRequest) -> dict:
        return {
            "workRequestId": wr.id, "requestNo": wr.request_no, "equipment": wr.equipment, "line": wr.line,
            "substance": wr.substance, "operatingCondition": wr.operating_condition,
            "productName": wr.product_name, "productType": wr.product_type.value if wr.product_type else None,
            "specJson": wr.spec_json, "symptom": wr.symptom, "siteMemo": wr.site_memo, "photos": [],
        }

    def completed_run(wr: WorkRequest) -> AgentRun:
        started = wr.created_at + timedelta(minutes=5)
        run = AgentRun(
            work_request_id=wr.id, status=RunStatus.DONE, started_at=started,
            finished_at=started + timedelta(seconds=70), input_snapshot=snapshot(wr),
        )
        db.add(run)
        db.flush()
        agents = (SpecMockAgent(), LegalMockAgent(), SafetyDocMockAgent())
        prior: dict[AgentCode, dict] = {}
        for offset, agent in enumerate(agents):
            context = AgentContext(db=db, run=run, work_request=wr, snapshot=run.input_snapshot, prior_results=prior)
            payload = agent.run(context)
            prior[agent.agent_code] = payload
            db.add(
                AgentStep(
                    run_id=run.id, agent_code=agent.agent_code, status=AgentStepStatus.DONE,
                    message=agent.message(),
                    started_at=started + timedelta(seconds=offset * 25),
                    finished_at=started + timedelta(seconds=offset * 25 + 20),
                )
            )
            db.add(
                AgentResult(
                    run_id=run.id, agent_code=agent.agent_code, payload_json=payload, original_json=payload,
                    edited=False, updated_at=started + timedelta(seconds=offset * 25 + 20),
                )
            )
        return run

    for wr in (w_done, w_pending, w_approved, w_rejected):
        completed_run(wr)

    # AI_RUNNING: A1 만 완료, A2·A3 대기
    started = w_running.created_at + timedelta(minutes=1)
    run = AgentRun(
        work_request_id=w_running.id, status=RunStatus.RUNNING, started_at=started,
        input_snapshot=snapshot(w_running),
    )
    db.add(run)
    db.flush()
    spec_agent = SpecMockAgent()
    spec_payload = spec_agent.run(
        AgentContext(db=db, run=run, work_request=w_running, snapshot=run.input_snapshot)
    )
    db.add(
        AgentStep(
            run_id=run.id, agent_code=AgentCode.A1, status=AgentStepStatus.DONE, message=spec_agent.message(),
            started_at=started, finished_at=started + timedelta(seconds=20),
        )
    )
    db.add(
        AgentResult(
            run_id=run.id, agent_code=AgentCode.A1, payload_json=spec_payload, original_json=spec_payload,
            edited=False, updated_at=started + timedelta(seconds=20),
        )
    )
    db.add_all(
        [
            AgentStep(run_id=run.id, agent_code=AgentCode.A2, status=AgentStepStatus.WAITING),
            AgentStep(run_id=run.id, agent_code=AgentCode.A3, status=AgentStepStatus.WAITING),
        ]
    )

    # --- approvals (append-only) ---------------------------------------------
    db.add_all(
        [
            Approval(
                work_request_id=w_approved.id, approver_id=safety.id, decision=ApprovalDecision.APPROVE,
                reason=None, reason_category=None,
                decided_at=w_approved.created_at + timedelta(hours=26, minutes=30),
            ),
            Approval(
                work_request_id=w_rejected.id, approver_id=safety.id, decision=ApprovalDecision.REJECT,
                reason="유독가스 라인이라 호환품 시트 재질로는 사용할 수 없습니다. OEM 동일 규격으로 다시 올려주세요.",
                reason_category="규격 부적합",
                decided_at=w_rejected.created_at + timedelta(hours=3),
            ),
        ]
    )
    w_approved.updated_at = w_approved.created_at + timedelta(hours=26, minutes=30)
    w_rejected.updated_at = w_rejected.created_at + timedelta(hours=3)
    db.commit()
