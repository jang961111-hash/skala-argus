"""Mock 에이전트 3종 — A1 규격·호환 / A2 법령·조문 / A3 안전서류.

입력 스냅샷(설비·라인·물질·운전조건·제품명·유형·스펙)을 실제로 읽어 문장을 만든다.
LLM 을 붙일 때 이 클래스만 `llm_agents.py` 의 구현으로 갈아끼우면 된다.

Phase 2: A1 의 부품 마스터·호환표 연동, A4 벤더 에이전트.
"""
from __future__ import annotations

from typing import Any

from app.core.enums import AgentCode
from app.services.agents.base import AgentContext, AgentService, document, item


def _spec_text(snapshot: dict[str, Any]) -> str:
    spec = snapshot.get("specJson") or {}
    return ", ".join(f"{k}={v}" for k, v in spec.items()) or "스펙 미입력"


class SpecMockAgent(AgentService):
    """A1 — 입력 스펙 기준의 규격·호환 판정."""

    agent_code = AgentCode.A1

    def message(self) -> str:
        return "규격·호환 검토 완료"

    def run(self, context: AgentContext) -> dict[str, Any]:
        s = context.snapshot
        product = s.get("productName") or "대상 부품"
        product_type = s.get("productType") or "ETC"
        substance = s.get("substance") or "미지정 물질"
        condition = s.get("operatingCondition") or {}
        pressure = condition.get("pressure") or "운전압력 미입력"
        temperature = condition.get("temperature") or "운전온도 미입력"

        items = [
            item(1, f"{product}({product_type}) 입력 스펙: {_spec_text(s)}"),
            item(2, f"운전조건 {temperature} / {pressure} 기준으로 규격 적합 판정."),
            item(3, f"{substance} 라인이므로 시트·개스킷 재질은 내식성 등급을 유지해야 한다."),
            item(4, "호환품 적용 시 시트 재질 변경(PCTFE→PTFE)은 유독가스 라인에서 허용되지 않는다."),
            item(5, "동일 규격 OEM 품으로 교체할 것을 권고한다. 부품 마스터 대조는 Phase 2."),
        ]
        return {"items": items}


class LegalMockAgent(AgentService):
    """A2 — 적용 법령·조문. submit-approval 이 여기 items 를 1건 이상 요구한다."""

    agent_code = AgentCode.A2

    def message(self) -> str:
        return "적용 법령 검토 완료"

    def run(self, context: AgentContext) -> dict[str, Any]:
        s = context.snapshot
        substance = s.get("substance") or "취급 물질"
        items = [
            item(1, "산업안전보건기준에 관한 규칙 제92조(정비등의 작업 시의 운전정지 등) — "
                    "정비·교체 작업 전 운전을 정지하고 기동장치에 잠금장치와 표지판을 설치한다."),
            item(2, "산업안전보건기준에 관한 규칙 제93조(방호장치의 해체 금지) — "
                    "방호장치를 임의로 해체하거나 사용을 정지해서는 안 된다."),
            item(3, f"화학물질관리법 제24조(취급시설의 설치·관리 기준) — {substance} 취급시설은 "
                    "환경부령 기준에 따라 설치·운영하고 정기 검사를 받아야 한다."),
            item(4, "고압가스 안전관리법 시행규칙 별표(특정고압가스 사용시설 기준) — "
                    "가스누출 검지경보장치를 설치하고 배관 작업 전 가스 차단·퍼지를 실시한다."),
            item(5, "필수 절차: 작업허가서 발행 → 위험성평가 → LOTO·가스 차단·퍼지 → 작업 후 가스 감지기 정상 확인."),
        ]
        return {"items": items}


class SafetyDocMockAgent(AgentService):
    """A3 — 안전서류 초안. A2 결과를 이어받아 필수 절차를 본문에 옮긴다."""

    agent_code = AgentCode.A3

    def message(self) -> str:
        return "안전서류 초안 생성 완료"

    def run(self, context: AgentContext) -> dict[str, Any]:
        s = context.snapshot
        equipment = s.get("equipment") or "대상 설비"
        line = s.get("line") or "라인 미지정"
        product = s.get("productName") or "대상 부품"
        substance = s.get("substance") or "취급 물질"
        request_no = s.get("requestNo") or ""

        legal = context.prior_results.get(AgentCode.A2) or {}
        procedures = "\n".join(f"- {i['text']}" for i in legal.get("items", [])[-2:]) or "- 작업허가·위험성평가·LOTO"

        permit = (
            f"# 작업허가서 (가스 배관 작업)\n\n"
            f"- 작업요청: {request_no}\n- 설비: {equipment} ({line})\n- 대상 부품: {product}\n"
            f"- 취급 물질: {substance}\n- 작업 내용: {s.get('symptom') or '부품 교체'}\n\n"
            f"## 근거 및 필수 절차\n{procedures}\n\n"
            f"## 확인 서명\n- 작업 책임자: ____________\n- 안전관리자: ____________\n"
        )
        risk = (
            f"# 위험성평가표\n\n- 대상: {equipment} / {product}\n"
            f"- 유해위험요인: {substance} 누출, 잔압 분출, 협착\n"
            f"- 최초 위험도: 높음\n- 감소 대책: 가스 차단·퍼지·LOTO 후 작업, 2인 1조, 보호구 착용\n"
            f"- 잔여 위험도: 낮음\n- 작업 후 확인: 가스 감지기 정상 동작 확인\n"
        )
        return {
            "documents": [
                document(1, "WORK_PERMIT", "작업허가서 초안", permit),
                document(2, "RISK_ASSESSMENT", "위험성평가표 초안", risk),
            ]
        }


MOCK_AGENTS: dict[AgentCode, type[AgentService]] = {
    AgentCode.A1: SpecMockAgent,
    AgentCode.A2: LegalMockAgent,
    AgentCode.A3: SafetyDocMockAgent,
}
