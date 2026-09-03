"""Mock agents returning the fixed results defined in docs/CONTRACT.md (AgentRun sample).

SafetyDocMockAgent and VendorMockAgent create real `documents` rows so that
GET /documents/{docId} works against the doc_ids returned in the step result.
LegalMockAgent also normalises its output into `legal_findings` rows.
"""
from __future__ import annotations

from typing import Any

from app.models import Document, LegalFinding
from app.repositories.ids import next_document_id
from app.services.agents.base import AgentContext, AgentService


class SpecMockAgent(AgentService):
    agent_type = "SPEC"

    def run(self, context: AgentContext) -> dict[str, Any]:
        part = context.part
        current_part = part.part_no if part else "VLV-SS316-1/4-NC"
        alternatives = []
        if part is not None:
            from app.repositories.master_repo import MasterRepository

            for pc, alt in MasterRepository(context.db).alternatives(part.id):
                alternatives.append(
                    {
                        "part_no": alt.part_no,
                        "grade": alt.grade,
                        "diff": pc.diff,
                        "allowed_for_toxic_gas": pc.allowed_for_toxic_gas,
                    }
                )
        if not alternatives:
            alternatives = [
                {
                    "part_no": "VLV-SS316-1/4-NC-EQ",
                    "grade": "EQUIVALENT",
                    "diff": "시트 재질 PCTFE→PTFE",
                    "allowed_for_toxic_gas": False,
                }
            ]
        return {"spec_match": True, "current_part": current_part, "alternatives": alternatives}


class LegalMockAgent(AgentService):
    agent_type = "LEGAL"

    RESULT: dict[str, Any] = {
        "applicable_laws": [
            {
                "law": "산업안전보건기준에 관한 규칙",
                "article": "제92조",
                "title": "정비등의 작업 시의 운전정지 등",
                "quote": "…운전을 정지하고 … 잠금장치 및 표지판을…",
            },
            {"law": "화학물질관리법", "article": "제24조", "title": "취급시설의 설치·관리 기준", "quote": ""},
            {"law": "고압가스 안전관리법 시행규칙", "article": "별표", "title": "특정고압가스 사용시설 기준", "quote": ""},
        ],
        "required_procedures": [
            {"name": "작업허가서(가스 배관 작업)", "phase": "BEFORE", "required": True},
            {"name": "위험성평가", "phase": "BEFORE", "required": True},
            {"name": "LOTO·가스 차단·퍼지 확인", "phase": "BEFORE", "required": True},
            {"name": "가스 감지기 정상 확인", "phase": "AFTER", "required": True},
        ],
    }

    def run(self, context: AgentContext) -> dict[str, Any]:
        result = {k: [dict(x) for x in v] for k, v in self.RESULT.items()}
        findings = [
            LegalFinding(agent_run_id=context.run.id, law=l["law"], article=l["article"], title=l["title"], quote=l["quote"])
            for l in result["applicable_laws"]
        ] + [
            LegalFinding(
                agent_run_id=context.run.id,
                procedure_name=p["name"],
                phase=p["phase"],
                required=p["required"],
                law="산업안전보건기준에 관한 규칙",
                article="제92조",
            )
            for p in result["required_procedures"]
        ]
        context.db.add_all(findings)
        context.db.flush()
        return result


class SafetyDocMockAgent(AgentService):
    agent_type = "SAFETY_DOC"

    def run(self, context: AgentContext) -> dict[str, Any]:
        wr = context.work_request
        eq_name = context.equipment.name if context.equipment else wr.equipment_id
        part_no = context.part.part_no if context.part else wr.part_id
        legal = context.prior_results.get("LEGAL", {})
        procedures = "\n".join(
            f"- [{p['phase']}] {p['name']} (필수: {'예' if p['required'] else '아니오'})"
            for p in legal.get("required_procedures", [])
        )
        permit = Document(
            id=next_document_id(context.db),
            agent_run_id=context.run.id,
            type="WORK_PERMIT",
            body=(
                f"# 작업허가서 (가스 배관 작업)\n\n"
                f"- 작업요청: {wr.id}\n- 설비: {eq_name}\n- 부품: {part_no}\n- 작업 내용: {wr.symptom} / {wr.site_check_note or ''}\n"
                f"- 작업자: (누락) 작업자 2명 이름\n\n## 필수 절차\n{procedures}\n"
            ),
            missing_json=["작업자 2명 이름"],
        )
        context.db.add(permit)
        context.db.flush()
        ra = Document(
            id=next_document_id(context.db),
            agent_run_id=context.run.id,
            type="RISK_ASSESSMENT",
            body=(
                f"# 위험성평가표\n\n- 대상: {eq_name} / {part_no}\n"
                f"- 유해위험요인: 유독가스 누출, 잔압, 협착\n- 위험도: 높음 → 가스 차단·퍼지·LOTO 후 작업으로 감소\n"
                f"- 관리대책: 가스 감지기 상시 감시, 2인 1조, 보호구 착용\n"
            ),
            missing_json=[],
        )
        context.db.add(ra)
        context.db.flush()
        return {
            "documents": [
                {"doc_id": permit.id, "type": "WORK_PERMIT", "missing": list(permit.missing_json)},
                {"doc_id": ra.id, "type": "RISK_ASSESSMENT", "missing": list(ra.missing_json)},
            ]
        }


class VendorMockAgent(AgentService):
    agent_type = "VENDOR"

    def run(self, context: AgentContext) -> dict[str, Any]:
        part_no = context.part.part_no if context.part else "VLV-SS316-1/4-NC"
        summary = f"{part_no} 2EA 견적·납기 요청"
        rfq = Document(
            id=next_document_id(context.db),
            agent_run_id=context.run.id,
            type="RFQ",
            body=(
                f"# 견적요청서 (RFQ)\n\n수신: OEM 밸브 공급사 담당자님\n\n"
                f"아래 품목의 견적 및 납기를 요청드립니다.\n\n- 품번: {part_no}\n- 수량: 2 EA\n"
                f"- 희망 납기: 3일 이내\n- 최근 구매: 2026-02-14\n\n감사합니다.\n"
            ),
            missing_json=[],
        )
        context.db.add(rfq)
        context.db.flush()
        return {"rfq_doc_id": rfq.id, "rfq_summary": summary, "lead_time_est_days": 3, "last_purchase": "2026-02-14"}


MOCK_AGENTS: dict[str, type[AgentService]] = {
    "SPEC": SpecMockAgent,
    "LEGAL": LegalMockAgent,
    "SAFETY_DOC": SafetyDocMockAgent,
    "VENDOR": VendorMockAgent,
}
