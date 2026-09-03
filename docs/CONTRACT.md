# ReplaceFlow 공통 계약서 (모든 산출물이 반드시 따를 것)

서비스명: **ReplaceFlow** — 반도체 설비 부품 교체 승인 프로세스 에이전트
기획서 원본: /home/claude/E안v3_설비교체_승인_에이전트_기획서_PoC발표용.md (반드시 먼저 읽을 것)
스택: FE Vue 3 + Vite + axios · BE FastAPI (Python 3.11) · DB PostgreSQL(Supabase) — 로컬 개발은 SQLite 폴백 · API 명세 OpenAPI 3.0 · Mock Postman · ERD dbdiagram(DBML)

## 상태값 (정확히 이 문자열)
- work_requests.status: `REQUESTED` → `RUNNING` → `REVIEW` → `PENDING_APPROVAL` → `APPROVED` | `REJECTED` → `DONE`
- agent_runs.overall_status: `RUNNING` | `REVIEW` | `FAILED`
- step.status: `PENDING` | `RUNNING` | `DONE` | `FAILED`
- step.agent: `SPEC` | `LEGAL` | `SAFETY_DOC` | `VENDOR`
- users.role: `ENGINEER` | `SAFETY_MANAGER` | `BUYER` | `ADMIN`
- approvals.decision: `APPROVE` | `REJECT` | `REQUEST_INFO`
- documents.type: `WORK_PERMIT` | `RISK_ASSESSMENT` | `LOTO_CHECKLIST` | `RFQ`
- parts.grade: `OEM` | `EQUIVALENT` | `REFURB`
- ai_configs.provider: `LOCAL_LLM` | `AX_PLATFORM` | `OPENAI`

## REST API (base: /api/v1) — Method/Path/Status Code 고정
| Method | Path | 응답 |
|---|---|---|
| GET | /work-requests?status=&page=&size= | 200 `{items:[WorkRequestSummary], total}` |
| POST | /work-requests | 201 `WorkRequest` |
| GET | /work-requests/{id} | 200 `WorkRequestDetail` (latest_run, approvals 포함) / 404 |
| POST | /work-requests/{id}/agent-runs | 202 `{run_id, overall_status:"RUNNING"}` / 404 / 409(이미 APPROVED/DONE) |
| GET | /agent-runs/{runId} | 200 `AgentRun` / 404 |
| PATCH | /work-requests/{id}/submit-approval | 200 `WorkRequest` / 422(누락 정보) / 409(run 미완료) |
| POST | /work-requests/{id}/approvals | 201 `Approval` / 409(필수 체크리스트 미완료 상태에서 APPROVE) / 404 |
| GET | /documents/{docId} | 200 `Document` / 404 |
| GET | /parts/{partId}/compatibility | 200 `{part, alternatives:[]}` |
| GET | /laws/search?q=&equipmentType=&substance= | 200 `{items:[LawArticle]}` |
| GET | /dashboard/summary | 200 `DashboardSummary` |
| GET | /tenants/{id}/ai-config | 200 `[AiConfig]` |
| PUT | /tenants/{id}/ai-config | 200 `[AiConfig]` |
| GET | /equipments | 200 `[Equipment]` |
| GET | /parts | 200 `[Part]` |

Mock 동작(BE·Postman 공통): `POST …/agent-runs` 직후 steps 4개 모두 `PENDING`. 이후 `GET /agent-runs/{runId}` 호출마다 다음 step 하나가 `DONE`(순서 SPEC→LEGAL→SAFETY_DOC→VENDOR). 4개 모두 DONE이면 `overall_status=REVIEW`, work_request.status=`REVIEW`.
승인 규칙: `checklist` 4항목(`WORK_PERMIT`, `RISK_ASSESSMENT`, `LOTO_GAS_ISOLATION`, `GAS_DETECTOR_CHECK`) 모두 `true`가 아니면 `APPROVE`는 409.

## 핵심 JSON 스키마 (필드명 고정)

WorkRequest
```json
{ "id": "WR-20260902-011", "tenant_id": "T-001", "equipment_id": "EQ-GC-02", "part_id": "P-VLV-001",
  "symptom": "가스 유량 이상, 밸브 누설 의심", "site_check_note": "현장 확인 결과 밸브 시트 마모", "requested_by": "U-001",
  "status": "REQUESTED", "created_at": "2026-09-02T15:00:00+09:00", "updated_at": "2026-09-02T15:00:00+09:00" }
```

AgentRun
```json
{ "run_id": "RUN-0042", "work_request_id": "WR-20260902-011", "overall_status": "REVIEW",
  "steps": [
    { "agent": "SPEC", "status": "DONE", "started_at": "...", "completed_at": "...",
      "result": { "spec_match": true, "current_part": "VLV-SS316-1/4-NC",
        "alternatives": [ { "part_no": "VLV-SS316-1/4-NC-EQ", "grade": "EQUIVALENT", "diff": "시트 재질 PCTFE→PTFE", "allowed_for_toxic_gas": false } ] } },
    { "agent": "LEGAL", "status": "DONE", "result": {
        "applicable_laws": [ { "law": "산업안전보건기준에 관한 규칙", "article": "제92조", "title": "정비등의 작업 시의 운전정지 등", "quote": "…운전을 정지하고 … 잠금장치 및 표지판을…" },
                             { "law": "화학물질관리법", "article": "제24조", "title": "취급시설의 설치·관리 기준", "quote": "" },
                             { "law": "고압가스 안전관리법 시행규칙", "article": "별표", "title": "특정고압가스 사용시설 기준", "quote": "" } ],
        "required_procedures": [ { "name": "작업허가서(가스 배관 작업)", "phase": "BEFORE", "required": true },
                                 { "name": "위험성평가", "phase": "BEFORE", "required": true },
                                 { "name": "LOTO·가스 차단·퍼지 확인", "phase": "BEFORE", "required": true },
                                 { "name": "가스 감지기 정상 확인", "phase": "AFTER", "required": true } ] } },
    { "agent": "SAFETY_DOC", "status": "DONE", "result": { "documents": [
        { "doc_id": "DOC-0101", "type": "WORK_PERMIT", "missing": ["작업자 2명 이름"] },
        { "doc_id": "DOC-0102", "type": "RISK_ASSESSMENT", "missing": [] } ] } },
    { "agent": "VENDOR", "status": "DONE", "result": { "rfq_doc_id": "DOC-0103", "rfq_summary": "VLV-SS316-1/4-NC 2EA 견적·납기 요청", "lead_time_est_days": 3, "last_purchase": "2026-02-14" } }
  ],
  "summary": "OEM 동일 규격 밸브 교체. 유독가스 라인이라 호환품 불가. 작업허가·위험성평가·LOTO 필수. 서류 초안 2건 생성, 작업자 명단만 보완 필요.",
  "approval_required_by": "SAFETY_MANAGER", "model_name": "mock-v1", "prompt_version": "replaceflow-v0.1",
  "created_at": "2026-09-02T15:10:02+09:00", "completed_at": "2026-09-02T15:11:30+09:00" }
```

Approval (요청 body / 응답)
```json
{ "approval_id": "AP-0007", "work_request_id": "WR-20260902-011", "approver_id": "U-002", "decision": "APPROVE",
  "checklist": { "WORK_PERMIT": true, "RISK_ASSESSMENT": true, "LOTO_GAS_ISOLATION": true, "GAS_DETECTOR_CHECK": true },
  "comment": "작업자 명단 확인 완료. 승인.", "decided_at": "2026-09-02T16:20:00+09:00" }
```

DashboardSummary
```json
{ "in_progress": 5, "pending_approval": 2, "avg_approval_hours": 26.5, "as_is_baseline_hours": 168, "completed_this_month": 12,
  "reject_reasons_top": [ { "reason": "서류 누락", "count": 3 }, { "reason": "호환품 부적합", "count": 1 } ] }
```

## ERD 테이블 (기획서 9장 그대로): tenants, users, equipments, parts, equipment_parts, part_compatibility, work_requests, agent_runs, legal_findings, documents, approvals, law_index, ai_configs, audit_logs

## 샘플 데이터 (모든 산출물이 같은 샘플 사용)
- tenant T-001 "○○반도체(하이닉스 2차 협력사)"
- users: U-001 김민준(ENGINEER), U-002 이정호(SAFETY_MANAGER), U-003 박수진(BUYER), U-004 관리자(ADMIN)
- equipments: EQ-GC-02 가스캐비닛#2(GAS_CABINET, 물질 SiH4), EQ-VLV-07 공정가스 밸브#7(VALVE, NH3), EQ-SCR-01 스크러버#1(SCRUBBER)
- parts: P-VLV-001 VLV-SS316-1/4-NC(OEM, toxic_gas_allowed=true, stock 2), P-VLV-002 VLV-SS316-1/4-NC-EQ(EQUIVALENT, false, stock 5), P-REG-001 압력조정기 REG-2S(OEM), P-FLT-001 인라인 필터(EQUIVALENT)
- law_index 6건: 산안규칙 91·92·93·319조, 화관법 24조, 고압가스법 시행규칙 별표(특정고압가스 사용시설)
- work_requests 5건 (상태 다양: REQUESTED 1, RUNNING 1, REVIEW 1, PENDING_APPROVAL 1, APPROVED 1)
