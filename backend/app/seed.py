"""Seed sample data from docs/CONTRACT.md (all deliverables share this dataset). Idempotent: skips if tenants exist."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AgentRun,
    AiConfig,
    Approval,
    Document,
    Equipment,
    EquipmentPart,
    LawIndex,
    Part,
    PartCompatibility,
    Tenant,
    User,
    WorkRequest,
)

KST = timezone(timedelta(hours=9))


def seed_if_empty(db: Session) -> bool:
    if db.scalar(select(Tenant).limit(1)) is not None:
        return False
    seed(db)
    return True


def seed(db: Session) -> None:
    db.add(Tenant(id="T-001", name="○○반도체(하이닉스 2차 협력사)", plan="STANDARD"))
    db.add_all(
        [
            User(id="U-001", tenant_id="T-001", name="김민준", role="ENGINEER"),
            User(id="U-002", tenant_id="T-001", name="이정호", role="SAFETY_MANAGER"),
            User(id="U-003", tenant_id="T-001", name="박수진", role="BUYER"),
            User(id="U-004", tenant_id="T-001", name="관리자", role="ADMIN"),
        ]
    )
    db.add_all(
        [
            Equipment(id="EQ-GC-02", tenant_id="T-001", name="가스캐비닛#2", type="GAS_CABINET", line="L1", substances=["SiH4"]),
            Equipment(id="EQ-VLV-07", tenant_id="T-001", name="공정가스 밸브#7", type="VALVE", line="L1", substances=["NH3"]),
            Equipment(id="EQ-SCR-01", tenant_id="T-001", name="스크러버#1", type="SCRUBBER", line="L2", substances=[]),
        ]
    )
    db.add_all(
        [
            Part(id="P-VLV-001", tenant_id="T-001", part_no="VLV-SS316-1/4-NC", name="다이어프램 밸브 SS316 1/4\" NC",
                 spec={"material": "SS316", "size": "1/4", "type": "NC", "seat": "PCTFE"}, grade="OEM", toxic_gas_allowed=True, stock=2),
            Part(id="P-VLV-002", tenant_id="T-001", part_no="VLV-SS316-1/4-NC-EQ", name="다이어프램 밸브 SS316 1/4\" NC (호환)",
                 spec={"material": "SS316", "size": "1/4", "type": "NC", "seat": "PTFE"}, grade="EQUIVALENT", toxic_gas_allowed=False, stock=5),
            Part(id="P-REG-001", tenant_id="T-001", part_no="REG-2S", name="압력조정기 REG-2S",
                 spec={"stage": 2, "inlet_max_bar": 200}, grade="OEM", toxic_gas_allowed=True, stock=1),
            Part(id="P-FLT-001", tenant_id="T-001", part_no="FLT-IL-003", name="인라인 필터",
                 spec={"rating_um": 0.003}, grade="EQUIVALENT", toxic_gas_allowed=True, stock=8),
        ]
    )
    db.flush()
    db.add_all(
        [
            EquipmentPart(equipment_id="EQ-GC-02", part_id="P-VLV-001", installed_at=datetime(2025, 3, 1, tzinfo=KST), last_replaced_at=datetime(2026, 2, 14, tzinfo=KST)),
            EquipmentPart(equipment_id="EQ-GC-02", part_id="P-REG-001", installed_at=datetime(2025, 3, 1, tzinfo=KST)),
            EquipmentPart(equipment_id="EQ-VLV-07", part_id="P-VLV-001", installed_at=datetime(2025, 6, 10, tzinfo=KST)),
            EquipmentPart(equipment_id="EQ-SCR-01", part_id="P-FLT-001", installed_at=datetime(2025, 9, 20, tzinfo=KST)),
            PartCompatibility(part_id="P-VLV-001", alt_part_id="P-VLV-002", diff="시트 재질 PCTFE→PTFE", allowed_for_toxic_gas=False),
        ]
    )
    db.add_all(
        [
            LawIndex(id="LAW-001", law="산업안전보건기준에 관한 규칙", article="제91조", title="고장난 기계의 정비 등",
                     text="사업주는 기계 또는 방호장치의 결함이 발견된 경우 정비가 완료될 때까지 해당 기계 및 방호장치 등의 사용을 금지하여야 한다.",
                     effective_date="2024-01-01", source_uri="https://www.law.go.kr/법령/산업안전보건기준에관한규칙/제91조",
                     equipment_types=["GAS_CABINET", "VALVE", "PIPING", "SCRUBBER"], substances=[]),
            LawIndex(id="LAW-002", law="산업안전보건기준에 관한 규칙", article="제92조", title="정비등의 작업 시의 운전정지 등",
                     text="사업주는 공작기계·수송기계·건설기계 등의 정비·청소·급유·검사·수리·교체 또는 조정 작업 시 근로자가 위험해질 우려가 있으면 해당 기계의 운전을 정지하여야 한다. 기동장치에 잠금장치를 하고 그 열쇠를 별도 관리하거나 표지판을 설치하는 등 필요한 방호 조치를 하여야 한다.",
                     effective_date="2024-01-01", source_uri="https://www.law.go.kr/법령/산업안전보건기준에관한규칙/제92조",
                     equipment_types=["GAS_CABINET", "VALVE", "PIPING", "SCRUBBER"], substances=[]),
            LawIndex(id="LAW-003", law="산업안전보건기준에 관한 규칙", article="제93조", title="방호장치의 해체 금지",
                     text="사업주는 기계·기구 또는 설비에 설치한 방호장치를 해체하거나 사용을 정지해서는 아니 된다. 다만, 방호장치의 수리·조정 등 필요한 경우에는 그러하지 아니하다.",
                     effective_date="2024-01-01", source_uri="https://www.law.go.kr/법령/산업안전보건기준에관한규칙/제93조",
                     equipment_types=["GAS_CABINET", "VALVE", "PIPING", "SCRUBBER"], substances=[]),
            LawIndex(id="LAW-004", law="산업안전보건기준에 관한 규칙", article="제319조", title="정전전로에서의 전기작업",
                     text="사업주는 근로자가 노출된 충전부 또는 그 부근에서 작업함으로써 감전될 우려가 있는 경우에는 작업에 들어가기 전에 해당 전로를 차단하여야 한다. 잠금장치 및 꼬리표를 부착하여야 한다.",
                     effective_date="2024-01-01", source_uri="https://www.law.go.kr/법령/산업안전보건기준에관한규칙/제319조",
                     equipment_types=["GAS_CABINET", "SCRUBBER"], substances=[]),
            LawIndex(id="LAW-005", law="화학물질관리법", article="제24조", title="취급시설의 설치·관리 기준",
                     text="유해화학물질 취급시설을 설치·운영하려는 자는 환경부령으로 정하는 설치 및 관리 기준에 따라 설치·운영하여야 하며, 정기적으로 검사를 받아야 한다.",
                     effective_date="2024-01-01", source_uri="https://www.law.go.kr/법령/화학물질관리법/제24조",
                     equipment_types=["GAS_CABINET", "VALVE", "PIPING"], substances=["SiH4", "NH3", "Cl2", "HF"]),
            LawIndex(id="LAW-006", law="고압가스 안전관리법 시행규칙", article="별표", title="특정고압가스 사용시설 기준",
                     text="특정고압가스(실란, 암모니아 등 독성·가연성 가스) 사용시설은 가스누출 검지경보장치를 설치하고, 배관 작업 전 가스 차단 및 퍼지를 실시하여야 한다.",
                     effective_date="2024-01-01", source_uri="https://www.law.go.kr/법령/고압가스안전관리법시행규칙/별표",
                     equipment_types=["GAS_CABINET", "VALVE", "PIPING"], substances=["SiH4", "NH3", "PH3", "AsH3"]),
        ]
    )
    db.add_all(
        [
            AiConfig(tenant_id="T-001", agent_type=a, provider="LOCAL_LLM", model_name="mock-v1", prompt_version="replaceflow-v0.1", egress_allowed=False)
            for a in ("SPEC", "LEGAL", "SAFETY_DOC", "VENDOR")
        ]
    )
    db.flush()

    # ---- work_requests: 5 sample rows with varied status ----
    base = datetime(2026, 9, 2, 15, 0, tzinfo=KST)

    def wr(i: int, eq: str, part: str, symptom: str, note: str, status: str, created: datetime) -> WorkRequest:
        return WorkRequest(
            id=f"WR-{created.strftime('%Y%m%d')}-{i:03d}", tenant_id="T-001", equipment_id=eq, part_id=part,
            symptom=symptom, site_check_note=note, requested_by="U-001", status=status, created_at=created, updated_at=created,
        )

    w1 = wr(1, "EQ-GC-02", "P-VLV-001", "가스 유량 이상, 밸브 누설 의심", "현장 확인 결과 밸브 시트 마모", "APPROVED", base - timedelta(hours=36))
    w2 = wr(2, "EQ-VLV-07", "P-VLV-001", "밸브 개폐 지연", "액추에이터 응답 지연 확인", "PENDING_APPROVAL", base - timedelta(days=2))
    w3 = wr(3, "EQ-SCR-01", "P-FLT-001", "차압 상승", "필터 막힘 확인", "REVIEW", base - timedelta(days=1))
    w4 = wr(4, "EQ-GC-02", "P-REG-001", "2차 압력 불안정", "조정기 출력 압력 흔들림", "RUNNING", base - timedelta(hours=2))
    w5 = wr(5, "EQ-VLV-07", "P-VLV-001", "누설 감지기 경보(미세)", "육안 확인 중", "REQUESTED", base)
    db.add_all([w1, w2, w3, w4, w5])
    db.flush()

    from app.services.agents.mock_agents import LegalMockAgent

    def done_steps(run_id: str, part_no: str, doc_ids: tuple[str, str, str], t0: datetime) -> list[dict]:
        return [
            {"agent": "SPEC", "status": "DONE", "started_at": (t0).isoformat(), "completed_at": (t0 + timedelta(seconds=20)).isoformat(),
             "result": {"spec_match": True, "current_part": part_no,
                        "alternatives": [{"part_no": "VLV-SS316-1/4-NC-EQ", "grade": "EQUIVALENT", "diff": "시트 재질 PCTFE→PTFE", "allowed_for_toxic_gas": False}]}},
            {"agent": "LEGAL", "status": "DONE", "started_at": (t0 + timedelta(seconds=20)).isoformat(), "completed_at": (t0 + timedelta(seconds=45)).isoformat(),
             "result": LegalMockAgent.RESULT},
            {"agent": "SAFETY_DOC", "status": "DONE", "started_at": (t0 + timedelta(seconds=45)).isoformat(), "completed_at": (t0 + timedelta(seconds=70)).isoformat(),
             "result": {"documents": [{"doc_id": doc_ids[0], "type": "WORK_PERMIT", "missing": []}, {"doc_id": doc_ids[1], "type": "RISK_ASSESSMENT", "missing": []}]}},
            {"agent": "VENDOR", "status": "DONE", "started_at": (t0 + timedelta(seconds=70)).isoformat(), "completed_at": (t0 + timedelta(seconds=88)).isoformat(),
             "result": {"rfq_doc_id": doc_ids[2], "rfq_summary": f"{part_no} 2EA 견적·납기 요청", "lead_time_est_days": 3, "last_purchase": "2026-02-14"}},
        ]

    summary = "OEM 동일 규격 밸브 교체. 유독가스 라인이라 호환품 불가. 작업허가·위험성평가·LOTO 필수. 서류 초안 2건 생성, 작업자 명단만 보완 필요."

    def make_run(run_id: str, w: WorkRequest, part_no: str, doc_ids: tuple[str, str, str]) -> AgentRun:
        t0 = w.created_at + timedelta(minutes=10)
        run = AgentRun(id=run_id, work_request_id=w.id, overall_status="REVIEW", steps_json=done_steps(run_id, part_no, doc_ids, t0),
                       summary=summary, approval_required_by="SAFETY_MANAGER", model_name="mock-v1", prompt_version="replaceflow-v0.1",
                       created_at=t0, completed_at=t0 + timedelta(seconds=88))
        db.add(run)
        db.flush()
        db.add_all(
            [
                Document(id=doc_ids[0], agent_run_id=run_id, type="WORK_PERMIT", body=f"# 작업허가서\n\n- 작업요청: {w.id}\n- 부품: {part_no}\n- 작업자: 김민준, 박수진\n", missing_json=[]),
                Document(id=doc_ids[1], agent_run_id=run_id, type="RISK_ASSESSMENT", body=f"# 위험성평가표\n\n- 대상: {w.equipment_id} / {part_no}\n", missing_json=[]),
                Document(id=doc_ids[2], agent_run_id=run_id, type="RFQ", body=f"# 견적요청서\n\n- 품번: {part_no}\n- 수량: 2 EA\n", missing_json=[]),
            ]
        )
        return run

    make_run("RUN-0001", w1, "VLV-SS316-1/4-NC", ("DOC-0001", "DOC-0002", "DOC-0003"))
    make_run("RUN-0002", w2, "VLV-SS316-1/4-NC", ("DOC-0004", "DOC-0005", "DOC-0006"))
    make_run("RUN-0003", w3, "FLT-IL-003", ("DOC-0007", "DOC-0008", "DOC-0009"))
    # RUNNING run: 2 of 4 done
    t0 = w4.created_at + timedelta(minutes=1)
    steps = done_steps("RUN-0004", "REG-2S", ("", "", ""), t0)[:2] + [
        {"agent": "SAFETY_DOC", "status": "PENDING", "started_at": None, "completed_at": None, "result": None},
        {"agent": "VENDOR", "status": "PENDING", "started_at": None, "completed_at": None, "result": None},
    ]
    db.add(AgentRun(id="RUN-0004", work_request_id=w4.id, overall_status="RUNNING", steps_json=steps, model_name="mock-v1",
                    prompt_version="replaceflow-v0.1", created_at=t0))

    # approvals: w1 approved (26.5h after creation), plus history for reject-reason KPI
    full = {"WORK_PERMIT": True, "RISK_ASSESSMENT": True, "LOTO_GAS_ISOLATION": True, "GAS_DETECTOR_CHECK": True}
    db.add_all(
        [
            Approval(id="AP-0001", work_request_id=w1.id, approver_id="U-002", decision="APPROVE", checklist_json=full,
                     comment="작업자 명단 확인 완료. 승인.", decided_at=w1.created_at + timedelta(hours=26, minutes=30)),
            Approval(id="AP-0002", work_request_id=w3.id, approver_id="U-002", decision="REQUEST_INFO",
                     checklist_json={**full, "GAS_DETECTOR_CHECK": False}, comment="서류 누락: 작업자 명단 보완 요청", decided_at=w3.created_at + timedelta(hours=3)),
        ]
    )
    w1.updated_at = w1.created_at + timedelta(hours=26, minutes=30)
    db.commit()
