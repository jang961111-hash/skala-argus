# ReplaceFlow Use-Case 명세서

문서 버전: v1.0 (2026-09-02) · 기준 문서: `docs/CONTRACT.md`, `E안v3_설비교체_승인_에이전트_기획서_PoC발표용.md`
상태값·필드명·API 경로는 CONTRACT.md의 문자열을 그대로 사용한다.

---

## 1. Actor 정의표

| Actor ID | Actor | 유형 | users.role | 설명 | 주요 UC |
|---|---|---|---|---|---|
| ACT-01 | 설비 엔지니어 | 사람 (Primary) | `ENGINEER` | 설비 이상을 현장에서 확인하고 작업요청을 생성한다. 에이전트 결과를 검토·보완하고 승인을 요청하며, 승인 후 작업을 수행하고 완료를 보고한다. | UC-01, UC-03, UC-05 |
| ACT-02 | 안전관리자 | 사람 (Primary) | `SAFETY_MANAGER` | 승인 패널에서 적용 법령·서류 초안을 검토하고 필수 체크리스트를 확인한 뒤 승인/반려/보완요청을 결정한다. **최종 판단 주체.** | UC-04 |
| ACT-03 | 구매 담당 | 사람 (Secondary, 선택) | `BUYER` | 벤더 에이전트가 만든 RFQ 초안을 확인·수정하여 발주한다. | UC-05 |
| ACT-04 | 관리자 | 사람 (Primary) | `ADMIN` | 대시보드 KPI를 확인하고 법령 인덱스·BOM·호환표·서류 템플릿·AI 설정을 관리한다. | UC-06, UC-07 |
| ACT-05 | 모니터링 시스템 | 외부 시스템 (Mock) | — | 가스 유량·압력 이상 알람을 발생시킨다. PoC 범위에서는 Mock 입력이며, 확장 시 알람이 UC-01을 자동 트리거한다. | UC-01 (트리거) |
| ACT-06 | 에이전트 서비스 | 시스템 (Mock/LLM) | — | 오케스트레이터가 실행하는 4개 전문 에이전트 `SPEC` / `LEGAL` / `SAFETY_DOC` / `VENDOR`. PoC에서는 Mock 구현체(고정 JSON, 단계별 상태 전이). | UC-02 |
| ACT-07 | 법령 인덱스 | 외부 데이터 (사내 적재) | — | 법제처 Open API에서 사전 적재한 `law_index` 테이블. `LEGAL` 에이전트의 인용 출처. | UC-02, UC-07 |

---

## 2. Use-Case 명세

### UC-01 작업요청 생성

| 항목 | 내용 |
|---|---|
| ID | UC-01 |
| 이름 | 작업요청 생성 |
| 주 Actor | 설비 엔지니어 (`ENGINEER`) |
| 부 Actor | 모니터링 시스템 (Mock 알람, 트리거 역할) |
| 사전조건 | 엔지니어가 로그인되어 있다. 대상 설비(`equipments`)와 부품(`parts`)이 마스터에 등록되어 있다. 현장 확인이 완료되었다. |
| 사후조건 | `work_requests` 레코드가 `status = REQUESTED`로 생성된다. `audit_logs`에 생성 이력이 남는다. |
| 관련 API | `GET /api/v1/equipments` (200 `[Equipment]`), `GET /api/v1/parts` (200 `[Part]`), `POST /api/v1/work-requests` (201 `WorkRequest`) |
| AI 확장 지점 | 없음 (사람 입력). 확장 시 모니터링 알람 → 자동 요청 생성(기획서 12장 확장 3) |

**기본 흐름**

1. (선택) 모니터링 시스템이 가스 유량·압력 이상 알람을 발생시킨다. 엔지니어가 현장에서 실제 이상 여부를 확인한다.
2. 엔지니어가 화면 1(작업요청 목록)에서 "작업요청 생성"을 선택한다.
3. 시스템이 `GET /equipments`, `GET /parts`로 설비·부품 목록을 조회하여 폼에 표시한다.
4. 엔지니어가 `equipment_id`, `part_id`, `symptom`(증상), `site_check_note`(현장 확인 메모)를 입력한다.
5. 엔지니어가 "저장"을 누르면 FE가 `POST /work-requests`를 호출한다.
6. 시스템이 `work_requests`에 `status = REQUESTED`, `requested_by = 현재 사용자`로 저장하고 201 `WorkRequest`를 반환한다.
7. FE가 화면 2(작업요청 상세)로 이동하고 "에이전트 실행" 버튼을 활성화한다.

**대안/예외 흐름**

- 4a. 필수 필드(`equipment_id`, `part_id`, `symptom`) 누락 → 422 응답, FE가 누락 필드를 표시한다.
- 4b. 등록되지 않은 `equipment_id`/`part_id` → 404, 엔지니어가 재선택한다.
- 1a. 알람 없이 정기 점검에서 발견된 경우에도 동일하게 2단계부터 진행한다.

---

### UC-02 에이전트 실행

| 항목 | 내용 |
|---|---|
| ID | UC-02 |
| 이름 | 에이전트 실행 (오케스트레이션) |
| 주 Actor | 시스템 (AgentOrchestrator) |
| 부 Actor | 설비 엔지니어(실행 트리거), 에이전트 서비스 `SPEC`/`LEGAL`/`SAFETY_DOC`/`VENDOR`, 법령 인덱스 |
| 사전조건 | 작업요청이 `REQUESTED`(또는 `REJECTED` 후 재실행) 상태이다. `ai_configs`에 테넌트의 에이전트별 provider/model/prompt_version이 존재한다. |
| 사후조건 | `agent_runs` 레코드가 생성되고 4개 step이 모두 `DONE`이면 `agent_runs.overall_status = REVIEW`, `work_requests.status = REVIEW`. `legal_findings`, `documents` 레코드가 정규화 저장된다. |
| 관련 API | `POST /api/v1/work-requests/{id}/agent-runs` (202 `{run_id, overall_status:"RUNNING"}` / 404 / 409), `GET /api/v1/agent-runs/{runId}` (200 `AgentRun` / 404) |
| AI 확장 지점 | **있음 — 핵심 확장 지점.** 오케스트레이터 + 4개 `AgentService` 인터페이스(Mock → LLM 구현체 교체) |

**기본 흐름**

1. 엔지니어가 화면 2에서 "에이전트 실행"을 누른다. FE가 `POST /work-requests/{id}/agent-runs`를 호출한다.
2. 시스템(WorkRequest API)이 요청 상태를 검증하고 `AgentOrchestrator`에 실행을 위임한다.
3. 오케스트레이터가 `agent_runs` 레코드를 생성한다: `overall_status = RUNNING`, `steps` 4개(`SPEC`, `LEGAL`, `SAFETY_DOC`, `VENDOR`) 모두 `status = PENDING`, `model_name`, `prompt_version`은 `ai_configs`에서 채운다.
4. 시스템이 `work_requests.status`를 `RUNNING`으로 바꾸고 즉시 202 `{run_id, overall_status:"RUNNING"}`을 반환한다.
5. 오케스트레이터가 4개 에이전트를 병렬(논리적)로 실행한다. 각 step은 `PENDING → RUNNING → DONE`으로 전이한다.
   - `SPEC`: 설비 BOM·부품 카탈로그·`part_compatibility`를 비교하여 `spec_match`, `current_part`, `alternatives[]`(`part_no`, `grade`, `diff`, `allowed_for_toxic_gas`)를 산출한다.
   - `LEGAL`: 설비 유형·물질·작업 종류로 `law_index`를 검색하여 `applicable_laws[]`(`law`, `article`, `title`, `quote`)와 `required_procedures[]`(`name`, `phase`, `required`)를 산출한다.
   - `SAFETY_DOC`: `LEGAL` 결과와 작업 내용으로 `documents[]`(`doc_id`, `type`, `missing[]`) 초안을 생성한다.
   - `VENDOR`: `SPEC` 결과와 구매 이력으로 `rfq_doc_id`, `rfq_summary`, `lead_time_est_days`, `last_purchase`를 산출한다.
6. FE가 3초 간격으로 `GET /agent-runs/{runId}`를 폴링한다. 응답의 `steps[].status`로 타임라인 카드가 `대기 → 실행 중 → 완료`로 갱신된다.
7. 4개 step이 모두 `DONE`이면 오케스트레이터가 결과를 통합하여 `summary`, `approval_required_by = SAFETY_MANAGER`를 작성하고 `overall_status = REVIEW`, `completed_at`을 기록한다.
8. 시스템이 `work_requests.status`를 `REVIEW`로 바꾼다. FE가 폴링을 중단하고 승인 요청 UI를 활성화한다.

**대안/예외 흐름**

- 1a. 작업요청이 이미 `APPROVED` 또는 `DONE` → 409, 실행 거부.
- 1b. `{id}`가 존재하지 않음 → 404.
- 5a. 특정 step 실패(예: `LEGAL` 인덱스 검색 오류) → 해당 step `status = FAILED`, `overall_status = FAILED`, `work_requests.status`는 `REQUESTED`로 되돌리지 않고 유지하되 FE가 "재실행" 버튼을 제공한다. 재실행 시 새 `run_id`가 발급된다.
- 5b. `LEGAL`이 근거 조문을 찾지 못한 절차는 `required = UNKNOWN`으로 두고 안전관리자 확인 문구를 붙인다(프롬프트 규칙). 조문 인용이 없는 답은 표시하지 않는다.
- 6a. Mock 모드: `GET /agent-runs/{runId}` 호출마다 다음 step 하나가 `DONE`으로 전이한다(순서 `SPEC → LEGAL → SAFETY_DOC → VENDOR`). 4회 호출(약 12초)에 `REVIEW`가 된다.

---

### UC-03 결과 검토·보완

| 항목 | 내용 |
|---|---|
| ID | UC-03 |
| 이름 | 에이전트 결과 검토·보완 및 승인 요청 |
| 주 Actor | 설비 엔지니어 (`ENGINEER`) |
| 부 Actor | 없음 |
| 사전조건 | `work_requests.status = REVIEW`, 최신 `agent_runs.overall_status = REVIEW`. |
| 사후조건 | 누락 항목이 보완되고 `work_requests.status = PENDING_APPROVAL`. 안전관리자에게 승인 요청이 노출된다. |
| 관련 API | `GET /api/v1/work-requests/{id}` (200 `WorkRequestDetail`), `GET /api/v1/documents/{docId}` (200 `Document`), `GET /api/v1/parts/{partId}/compatibility` (200 `{part, alternatives:[]}`), `PATCH /api/v1/work-requests/{id}/submit-approval` (200 `WorkRequest` / 422 / 409) |
| AI 확장 지점 | 부분 — 결과 열람은 사람. 확장 시 보완 입력을 반영한 서류 재생성(`SAFETY_DOC` 재호출) |

**기본 흐름**

1. 엔지니어가 화면 2에서 `GET /work-requests/{id}`로 요청 정보·`latest_run`을 조회한다.
2. 엔지니어가 타임라인 카드를 클릭하여 상세를 본다: `SPEC` 호환표(`GET /parts/{partId}/compatibility`), `LEGAL` 조문 인용, `SAFETY_DOC` 서류 초안(`GET /documents/{docId}`), `VENDOR` RFQ 요약.
3. `SAFETY_DOC` 결과의 `documents[].missing`에 항목이 있으면(예: `"작업자 2명 이름"`) 엔지니어가 해당 값을 입력한다.
4. 엔지니어가 "승인 요청"을 누른다. FE가 `PATCH /work-requests/{id}/submit-approval`을 호출한다.
5. 시스템이 최신 run이 `REVIEW`인지, `documents[].missing`이 모두 비었는지 검증한다.
6. 시스템이 `work_requests.status`를 `PENDING_APPROVAL`로 바꾸고 200 `WorkRequest`를 반환한다.
7. 안전관리자의 목록/대시보드에서 `pending_approval` 건수가 증가한다.

**대안/예외 흐름**

- 4a. 누락 정보가 남아 있음 → 422, FE가 누락 항목 목록을 표시하고 3단계로 돌아간다.
- 4b. 최신 run이 `RUNNING` 또는 `FAILED` → 409, "에이전트 실행이 완료되지 않았습니다" 안내.
- 2a. `SPEC` 결과 `spec_match = false`이고 `alternatives[].allowed_for_toxic_gas = false`뿐인 경우, 엔지니어가 OEM 부품으로 `part_id`를 바꾸어 UC-02를 재실행한다.

---

### UC-04 승인

| 항목 | 내용 |
|---|---|
| ID | UC-04 |
| 이름 | 승인 / 반려 / 보완요청 |
| 주 Actor | 안전관리자 (`SAFETY_MANAGER`) |
| 부 Actor | 설비 엔지니어(반려·보완요청 코멘트 수신) |
| 사전조건 | `work_requests.status = PENDING_APPROVAL`. 최신 `agent_runs`의 `LEGAL`, `SAFETY_DOC` 결과가 존재한다. |
| 사후조건 | `approvals` 레코드가 생성된다. `decision = APPROVE` → `work_requests.status = APPROVED`, `decision = REJECT` → `REJECTED`, `decision = REQUEST_INFO` → `REVIEW`로 되돌아간다(엔지니어 보완 후 재요청). `audit_logs`에 결정 이력이 남는다. |
| 관련 API | `GET /api/v1/work-requests/{id}` (200), `GET /api/v1/documents/{docId}` (200), `GET /api/v1/laws/search?q=&equipmentType=&substance=` (200 `{items:[LawArticle]}`), `POST /api/v1/work-requests/{id}/approvals` (201 `Approval` / 409 / 404) |
| AI 확장 지점 | **없음 — 사람 고정(Human-in-the-loop).** 에이전트는 근거만 제공하며 결정은 시스템이 대신하지 않는다. |

**기본 흐름**

1. 안전관리자가 화면 1에서 `PENDING_APPROVAL` 건을 선택하여 화면 2로 이동한다.
2. 승인 패널이 `latest_run`의 `LEGAL.result.applicable_laws[]`(조문 링크)와 `required_procedures[]`를 표시한다.
3. 안전관리자가 서류 초안(`WORK_PERMIT`, `RISK_ASSESSMENT`, `LOTO_CHECKLIST`)을 `GET /documents/{docId}`로 열람한다. 필요 시 `GET /laws/search`로 원문을 추가 확인한다.
4. 안전관리자가 필수 체크리스트 4항목 `WORK_PERMIT`, `RISK_ASSESSMENT`, `LOTO_GAS_ISOLATION`, `GAS_DETECTOR_CHECK`를 하나씩 확인한다. 4개가 모두 `true`가 되기 전까지 "승인" 버튼은 비활성이다.
5. 안전관리자가 코멘트를 입력하고 "승인"을 누른다. FE가 `POST /work-requests/{id}/approvals`에 `{approver_id, decision:"APPROVE", checklist:{...}, comment}`를 전송한다.
6. `ApprovalService`가 체크리스트 게이트(4항목 모두 `true`)를 검증하고 `approvals` 레코드를 생성한다(`decided_at` 기록).
7. 시스템이 `work_requests.status`를 `APPROVED`로 바꾸고 201 `Approval`을 반환한다.
8. 대시보드의 `avg_approval_hours`가 갱신된다.

**대안/예외 흐름**

- 5a. **반려**: `decision = REJECT` + 코멘트(예: "호환품 부적합") → `status = REJECTED`. 엔지니어에게 코멘트가 전달되고 `reject_reasons_top` 집계에 반영된다. 엔지니어는 요청을 수정하여 UC-02를 재실행할 수 있다.
- 5b. **보완요청**: `decision = REQUEST_INFO` + 코멘트 → `status = REVIEW`. 엔지니어가 UC-03으로 돌아가 보완 후 다시 `submit-approval`한다("메신저 왕복" 대체).
- 5c. 체크리스트 4항목 중 하나라도 `true`가 아닌 상태로 `APPROVE` 전송(FE 우회 포함) → 409. `REJECT`/`REQUEST_INFO`는 체크리스트 미완료여도 허용된다.
- 1a. 상태가 `PENDING_APPROVAL`이 아닌 요청에 결정 시도 → 409.
- 1b. `{id}` 없음 → 404.

---

### UC-05 발주·작업

| 항목 | 내용 |
|---|---|
| ID | UC-05 |
| 이름 | 발주·작업 수행·완료 보고 |
| 주 Actor | 설비 엔지니어 (`ENGINEER`) |
| 부 Actor | 구매 담당 (`BUYER`, 선택), 벤더(외부, 시스템 밖) |
| 사전조건 | `work_requests.status = APPROVED`. `VENDOR` step 결과의 `rfq_doc_id`가 존재한다. |
| 사후조건 | RFQ가 발송되고 부품 교체 작업이 수행된 뒤 `work_requests.status = DONE`. `equipment_parts.last_replaced_at`이 갱신된다(확장). |
| 관련 API | `GET /api/v1/documents/{docId}` (200 `Document`, type `RFQ`), `GET /api/v1/work-requests/{id}` (200) — 완료 보고 상태 전이는 CONTRACT의 상태값 `DONE`을 따르며 전용 엔드포인트는 PoC 범위 외(FE 수동 전이 또는 확장 API) |
| AI 확장 지점 | 부분 — RFQ 초안은 `VENDOR` 에이전트 산출물. 발송·발주 확정·작업 수행은 사람. 확장 시 벤더 포털·ERP 연동. |

**기본 흐름**

1. 승인 완료 알림을 받은 엔지니어(또는 구매 담당)가 화면 2에서 `VENDOR` 카드를 열어 `rfq_summary`, `lead_time_est_days`, `last_purchase`를 확인한다.
2. `GET /documents/{rfq_doc_id}`로 RFQ 초안 본문을 열람하고 필요하면 수량·납기를 수정한다.
3. 구매 담당이 RFQ를 벤더에 발송하고 발주를 확정한다(시스템 밖 행위, PoC에서는 버튼 클릭으로 대체).
4. 부품 입고 후 엔지니어가 승인된 절차(작업허가서·LOTO·가스 차단·퍼지)에 따라 교체 작업을 수행한다.
5. 작업 후 절차(`phase = AFTER`: 가스 감지기 정상 확인)를 완료한다.
6. 엔지니어가 "작업 완료 보고"를 누르면 `work_requests.status`가 `DONE`으로 전이한다.
7. 대시보드 `completed_this_month`가 증가한다.

**대안/예외 흐름**

- 2a. 재고(`parts.stock`)가 충분하면 RFQ 발송을 생략하고 4단계로 진행한다.
- 3a. 벤더 납기가 `lead_time_est_days`를 크게 초과하면 엔지니어가 `SPEC` 결과의 `alternatives[]` 중 `allowed_for_toxic_gas = true`인 부품으로 요청을 수정하고 UC-02부터 재실행한다(유독가스 라인은 호환품 불가 원칙).
- 4a. 작업 중 추가 이상 발견 → 새 작업요청(UC-01)을 생성한다.

---

### UC-06 대시보드

| 항목 | 내용 |
|---|---|
| ID | UC-06 |
| 이름 | 대시보드·KPI 조회 |
| 주 Actor | 관리자 (`ADMIN`) |
| 부 Actor | 안전관리자, 설비 엔지니어(목록·KPI 열람) |
| 사전조건 | 로그인 상태. `work_requests`, `approvals` 데이터가 존재한다. |
| 사후조건 | 없음(조회 전용). |
| 관련 API | `GET /api/v1/dashboard/summary` (200 `DashboardSummary`), `GET /api/v1/work-requests?status=&page=&size=` (200 `{items:[WorkRequestSummary], total}`) |
| AI 확장 지점 | 없음. 확장 시 반려 사유·승인 이력을 프롬프트 튜닝 데이터로 활용(기획서 12장 확장 2). |

**기본 흐름**

1. 사용자가 화면 1에 진입한다. FE가 `GET /dashboard/summary`를 호출한다.
2. KPI 타일에 `in_progress`, `pending_approval`, `avg_approval_hours`(As-Is `as_is_baseline_hours = 168` 대비), `completed_this_month`를 표시한다.
3. `reject_reasons_top[]`(`reason`, `count`)를 TOP5 목록으로 표시한다.
4. FE가 `GET /work-requests?status=&page=&size=`로 요청 테이블(설비 / 부품 / 상태 / 에이전트 진행률 / 승인자)을 표시한다.
5. 사용자가 `status` 필터(예: `PENDING_APPROVAL`)와 페이지를 바꾸면 4단계를 재호출한다.
6. 행을 클릭하면 화면 2(UC-03/UC-04)로 이동한다.

**대안/예외 흐름**

- 1a. 데이터가 없는 신규 테넌트 → KPI 0, `avg_approval_hours = null` 표시.
- 4a. 3초 폴링 중인 `RUNNING` 건은 테이블의 에이전트 진행률(완료 step 수 / 4)이 실시간 갱신된다.

---

### UC-07 지식 관리

| 항목 | 내용 |
|---|---|
| ID | UC-07 |
| 이름 | 지식·설정 관리 (법령 인덱스, BOM·호환표, 서류 템플릿, AI 설정) |
| 주 Actor | 관리자 (`ADMIN`) |
| 부 Actor | 법령 인덱스(법제처 Open API 사전 적재), 사내 LLM/AX 플랫폼(설정 대상) |
| 사전조건 | `ADMIN` 권한. 테넌트(`tenant_id`)가 존재한다. |
| 사후조건 | `law_index`, `parts`, `part_compatibility`, `equipment_parts`, 서류 템플릿, `ai_configs`가 갱신된다. 이후 실행되는 `agent_runs`부터 새 설정이 적용되며, 과거 `legal_findings`는 스냅샷으로 보존된다. |
| 관련 API | `GET /api/v1/laws/search?q=&equipmentType=&substance=` (200), `GET /api/v1/tenants/{id}/ai-config` (200 `[AiConfig]`), `PUT /api/v1/tenants/{id}/ai-config` (200 `[AiConfig]`), `GET /api/v1/parts` (200), `GET /api/v1/parts/{partId}/compatibility` (200) |
| AI 확장 지점 | **있음 — 설정·지식 공급 지점.** `ai_configs.provider`(`LOCAL_LLM` / `AX_PLATFORM` / `OPENAI`), `model_name`, `prompt_version`, `egress_allowed`를 에이전트별로 분리 관리. `law_index`는 `LEGAL` 에이전트 RAG의 지식원. |

**기본 흐름**

1. 관리자가 설정 화면에서 `GET /tenants/{id}/ai-config`로 에이전트별(`agent_type` = `SPEC`/`LEGAL`/`SAFETY_DOC`/`VENDOR`) 현재 설정을 조회한다.
2. 관리자가 에이전트별 `provider`, `model_name`, `prompt_version`, `egress_allowed`를 수정하고 `PUT /tenants/{id}/ai-config`로 저장한다(기본값 `provider = LOCAL_LLM`, `egress_allowed = false`).
3. 관리자가 법령 인덱스 갱신을 실행한다(법제처 Open API → `law_index` 적재, PoC에서는 샘플 6개 조문 시드). `GET /laws/search`로 적재 결과를 검증한다.
4. 관리자가 BOM·호환표(`parts`, `part_compatibility`, `equipment_parts`)를 갱신한다.
5. 관리자가 서류 템플릿(`WORK_PERMIT`, `RISK_ASSESSMENT`, `LOTO_CHECKLIST`, `RFQ`)을 갱신한다.
6. 변경 내역이 `audit_logs`에 `before_json` / `after_json`으로 기록된다.

**대안/예외 흐름**

- 2a. `provider = OPENAI` 등 외부 provider 선택 시 `egress_allowed = true`가 함께 필요하다. 온프레미스 정책상 `egress_allowed = false`인 테넌트에서 외부 provider 저장 시도 → 422(정책 위반) 안내.
- 3a. 법령 개정으로 `law_index`가 갱신되어도 기존 `legal_findings`(건별 스냅샷)는 변경하지 않는다.
- 1a. `ADMIN`이 아닌 사용자의 접근 → 403.

---

## 3. AI 확장 지점 정의

### 3.1 원칙

기획서 4장의 설계 원칙을 그대로 따른다: **에이전트는 정보를 모으고 초안을 쓸 뿐, 판단·승인·발주 확정은 사람이 한다.** 산업안전 규제상 승인 주체는 사람이어야 하며 이는 기능이 아니라 설계 요건이다.

### 3.2 확장 지점 (AI가 들어가는 곳)

| # | 확장 지점 | 위치(코드/데이터) | 관련 UC | PoC 구현 | 확장 구현 |
|---|---|---|---|---|---|
| X-0 | **AgentOrchestrator** | BE `AgentOrchestrator` — `agent_runs` 생성, 4개 step 상태 관리, 결과 통합(`summary`, `approval_required_by`) | UC-02 | 순차 Mock 전이(폴링 1회당 step 1개 `DONE`) | Queue 기반 실 병렬 실행, 재시도, step 단위 FAILED 복구 |
| X-1 | **A1 SPEC 에이전트** | `AgentService` 인터페이스 구현체 `SpecAgent` — 입력: 설비 BOM, `part_id`, `part_compatibility` / 출력: `spec_match`, `current_part`, `alternatives[]` | UC-02, (UC-03 열람) | Mock 고정 JSON | ERP·BOM 실연동 + LLM 규격 비교 |
| X-2 | **A2 LEGAL 에이전트** | `LegalAgent` — 입력: 설비 유형, 물질, 작업 종류, `law_index` 발췌 / 출력: `applicable_laws[]`, `required_procedures[]` → `legal_findings` 정규화 | UC-02, (UC-04 근거) | Mock 고정 JSON, `law_index` 6조문 | 법제처 Open API 전량 적재 + Vector DB + 사내 GPU LLM RAG. 프롬프트 `replaceflow-v0.1`(기획서 7장). 근거 없는 항목은 `required = UNKNOWN` |
| X-3 | **A3 SAFETY_DOC 에이전트** | `SafetyDocAgent` — 입력: A2 결과 + 작업 내용 + 서류 템플릿 / 출력: `documents[]`(`doc_id`, `type`, `missing[]`) → `documents` 테이블 | UC-02, UC-03 | Mock 초안 2건 | LLM 초안 생성, 보완 입력 반영 재생성 |
| X-4 | **A4 VENDOR 에이전트** | `VendorAgent` — 입력: A1 결과, 구매 이력 / 출력: `rfq_doc_id`, `rfq_summary`, `lead_time_est_days`, `last_purchase` | UC-02, UC-05 | Mock 고정 JSON | 벤더 포털·ERP 연동, 납기 실조회 |
| X-C | **AI 설정 격리** | `ai_configs`(`tenant_id`, `agent_type`, `provider`, `model_name`, `prompt_version`, `egress_allowed`) + `GET/PUT /tenants/{id}/ai-config` | UC-07 | `provider = LOCAL_LLM`, `egress_allowed = false` 기본, 모델명 `mock-v1` | 에이전트별 provider 교체(`LOCAL_LLM` / `AX_PLATFORM` / `OPENAI`), 프롬프트 버전 롤아웃 |
| X-K | **지식 공급** | `law_index`(법제처 사전 적재), `part_compatibility`, 서류 템플릿 | UC-07 | 샘플 시드 | 정기 재적재 배치, 개정 이력 관리 |

FE는 확장 지점의 내부를 전혀 모른다. FE가 아는 것은 `GET /agent-runs/{runId}`의 JSON 계약(`steps[].agent`, `steps[].status`, `steps[].result`)뿐이므로 Mock → LLM 교체 시 FE 변경은 0이다.

### 3.3 사람이 유지하는 곳 (AI가 대체하지 않는 곳)

| 행위 | Actor | UC | 시스템 보장 장치 |
|---|---|---|---|
| 현장 이상 확인 및 작업요청 생성 | 설비 엔지니어 | UC-01 | `site_check_note` 필수 입력 |
| 에이전트 결과 검토, 누락 정보 보완, 승인 요청 결정 | 설비 엔지니어 | UC-03 | `submit-approval` 422(누락) / 409(run 미완료) |
| 법령·서류 근거 확인, 체크리스트 확인, 승인/반려/보완요청 **결정** | 안전관리자 | UC-04 | `approvals.decision`은 사람만 생성. 체크리스트 4항목 모두 `true` 아니면 `APPROVE` 409. `approval_required_by = SAFETY_MANAGER` |
| RFQ 발송·발주 확정 | 구매 담당 / 엔지니어 | UC-05 | 에이전트는 `RFQ` 초안(`documents.type = RFQ`)만 생성, 발송 행위 없음 |
| 실제 교체 작업, 작업 후 가스 감지기 확인, 완료 보고 | 설비 엔지니어 | UC-05 | `DONE` 전이는 사람의 보고로만 발생 |
| 법령 인덱스·호환표·템플릿·AI 설정 변경 | 관리자 | UC-07 | `audit_logs` before/after 기록, `egress_allowed` 정책 검증 |
| `required = UNKNOWN` 절차의 최종 판단 | 안전관리자 | UC-04 | LEGAL 프롬프트 규칙: 근거 못 찾으면 사람에게 넘김 |

### 3.4 상태 전이와 책임 주체 요약

| 전이 | 트리거 주체 | UC |
|---|---|---|
| (생성) → `REQUESTED` | 엔지니어 | UC-01 |
| `REQUESTED` → `RUNNING` | 엔지니어(실행 버튼) → 시스템 | UC-02 |
| `RUNNING` → `REVIEW` | 시스템(오케스트레이터, 4 step `DONE`) | UC-02 |
| `REVIEW` → `PENDING_APPROVAL` | 엔지니어(`submit-approval`) | UC-03 |
| `PENDING_APPROVAL` → `APPROVED` / `REJECTED` | 안전관리자(`approvals`) | UC-04 |
| `PENDING_APPROVAL` → `REVIEW` (`REQUEST_INFO`) | 안전관리자 | UC-04 |
| `APPROVED` → `DONE` | 엔지니어(완료 보고) | UC-05 |
| `REJECTED` → `RUNNING` (수정 후 재실행) | 엔지니어 | UC-02 |

AI가 스스로 일으키는 전이는 `RUNNING → REVIEW` 하나뿐이다.
