# ReplaceFlow 공통 계약서 v2.0 (모든 산출물이 반드시 따를 것)

> **쓰기 권한: 오케스트레이터 전용.** 트랙 담당자는 읽기만 한다.
> 변경이 필요하면 **작업을 멈추고 변경을 요청**한다. 임의로 우회하지 않는다.
> v1.0 은 `docs/CONTRACT_v1.0_archived.md` 에 보존. 근거 문서는 `WRA_화면정의서_v2.0`(2026-09-03).

서비스명: **ReplaceFlow** — 반도체 설비 부품 교체 승인 프로세스 에이전트
스택: FE Vue 3 + Vite + axios · BE FastAPI (**Python 3.10+**, 개발 3.11) · DB PostgreSQL(Supabase) — 로컬 SQLite 폴백 · OpenAPI 3.0 · Postman Mock · dbdiagram(DBML)

---

## 0. v1.0 → v2.0 변경 요약 (이 6개가 이번 개정의 전부다)

| # | 변경 | 영향 |
|---|---|---|
| 1 | **역할별 화면 분리** — 엔지니어/안전관리자 GNB·플로우 별도 | FE 라우팅, `GET /dashboard/summary?role=` |
| 2 | **로그인·회원가입 추가** | `users.email/password_hash`, `/auth/*` 3종, 전 엔드포인트 인증 |
| 3 | **엔지니어 메인에서 평균 승인 소요시간 KPI·진행률 컬럼 제거** | DashboardSummary 역할별 분리 |
| 4 | **요청 등록 확장** — 제품 유형 5종별 동적 스펙 + 사진 업로드, 입력 전체를 AI 컨텍스트로 전송 | `work_requests` 7컬럼 추가, `photos` 테이블 신설 |
| 5 | **AI 에이전트 4종 → 3종** (VENDOR 제외, Phase 2) + **결과를 엔지니어가 편집** | `step.agent` enum 축소, `agent_results` 편집 가능, `PATCH /agent-results/{id}` |
| 6 | **승인에서 체크리스트 blocking 제거** — 승인 / 거절+사유로 단순화 | `approvals.checklist` 폐지, `reason` 필수화 |

---

## 1. 상태값 (정확히 이 문자열 — 어디서도 다르게 쓰지 않는다)

- `work_requests.status`: `DRAFT` → `REQUESTED` → `RUNNING` → `REVIEW` → `PENDING_APPROVAL` → `APPROVED` | `REJECTED` → `DONE`

  화면 라벨 대응 (화면정의서 한글 ↔ enum). **화면정의서의 "PENDING" 은 `PENDING_APPROVAL` 을 가리킨다. enum 은 바꾸지 않는다.**

  | 화면 라벨 | enum | 의미 |
  |---|---|---|
  | 작성 중 | `DRAFT` | 임시 저장, AI 미실행 |
  | — | `REQUESTED` | 생성 직후, agent-run 시작 전 (과도 상태) |
  | AI 검증중 | `RUNNING` | 에이전트 실행 중 |
  | 결과 확인·수정 | `REVIEW` | 3종 완료, 엔지니어 편집 단계 |
  | 승인 대기 | `PENDING_APPROVAL` | 안전관리자에게 제출됨 |
  | 승인 | `APPROVED` | |
  | 거절·보완 | `REJECTED` | 사유 포함, 재제출 가능 |
  | 완료 | `DONE` | 교체 작업까지 완료 |

- `agent_runs.overall_status`: `RUNNING` | `REVIEW` | `FAILED`
- `step.status`: `PENDING` | `RUNNING` | `DONE` | `FAILED`
- **`step.agent`: `SPEC` | `LEGAL` | `SAFETY_DOC`** ← **VENDOR 제거 (Phase 2).** 3종이다.
- `users.role`: `ENGINEER` | `SAFETY_MANAGER` | `BUYER` | `ADMIN` (v2.0 회원가입은 앞의 2종만 선택 가능)
- **`approvals.decision`: `APPROVE` | `REJECT`** ← `REQUEST_INFO` 제거 (거절·보완으로 통합)
- `documents.type`: `WORK_PERMIT` | `RISK_ASSESSMENT` | `LOTO_CHECKLIST` (`RFQ` 제거 — VENDOR 삭제에 수반)
- `parts.grade`: `OEM` | `EQUIVALENT` | `REFURB`
- `ai_configs.provider`: `LOCAL_LLM` | `AX_PLATFORM` | `OPENAI`
- **`work_requests.product_type` (신규): `VALVE` | `FITTING_TUBE` | `REGULATOR` | `FILTER` | `OTHER`**

### 제품 유형 → 동적 스펙 필드 (`spec_json` 에 담는다)

| product_type | 화면 라벨 | `spec_json` 키 | 예시 |
|---|---|---|---|
| `VALVE` | 밸브 | `pressure_rating` | `"3000 psi"` |
| `FITTING_TUBE` | 피팅·튜브 | `connection_spec`, `material` | `"1/4 VCR"`, `"SS316L"` |
| `REGULATOR` | 레귤레이터 | `pressure_rating` | `"3000 psi"` |
| `FILTER` | 필터 | `substance_type` | `"SiH4"` |
| `OTHER` | 기타 | `free_spec` | 자유 입력 문자열 |

---

## 2. REST API (base: `/api/v1`) — Method/Path/Status Code 고정

### 2.1 인증 (신규)

| Method | Path | 응답 |
|---|---|---|
| POST | `/auth/signup` | 201 `User` / 409(중복 이메일) / 422(필수 누락·비밀번호 불일치) |
| POST | `/auth/login` | 200 `{access_token, token_type:"bearer", user}` / 401(자격 증명 불일치) |
| GET | `/auth/me` | 200 `User` / 401 |

인증 방식: `Authorization: Bearer <token>`. 3일 범위에서는 **서명된 불투명 토큰**(HMAC-SHA256, `SECRET_KEY` 는 `.env`)으로 충분하다. 비밀번호는 **평문 저장 금지** — `hashlib.pbkdf2_hmac` 또는 `passlib` 사용. `password_hash` 는 어떤 응답에도 포함되지 않는다.

**미인증 접근**: 아래 2.2~2.5 전 엔드포인트는 토큰 필요. 없으면 401.

### 2.2 작업요청

| Method | Path | 응답 |
|---|---|---|
| GET | `/work-requests?mine=&status=&page=&size=` | 200 `{items:[WorkRequestSummary], total}` |
| POST | `/work-requests` | 201 `WorkRequest` (body 의 `status` 가 `DRAFT` 면 임시저장, 없으면 `REQUESTED`) |
| GET | `/work-requests/{id}` | 200 `WorkRequestDetail` / 404 |
| **PATCH** | **`/work-requests/{id}`** | 200 `WorkRequest` — 부분 수정(`engineer_note`, 등록 필드) / 404 / 409(APPROVED·DONE 은 수정 불가) |
| PATCH | `/work-requests/{id}/submit-approval` | 200 `WorkRequest` / 409(run 미완료) / 422(`engineer_note` 누락) |
| PATCH | `/work-requests/{id}/complete` | 200 `WorkRequest` / 409(APPROVED 아님) |
| POST | `/work-requests/{id}/photos` | 201 `Photo` — `multipart/form-data`, 필드명 `file` / 404 / 422(형식·용량) |
| GET | `/work-requests/{id}/photos` | 200 `[Photo]` / 404 |

`mine=true` 는 토큰의 사용자 기준으로 필터한다. 쿼리스트링에 사용자 ID 를 넣지 않는다.

### 2.3 에이전트

| Method | Path | 응답 |
|---|---|---|
| POST | `/work-requests/{id}/agent-runs` | 202 `{run_id, overall_status:"RUNNING"}` / 404 / 409(이미 RUNNING·APPROVED·DONE) |
| GET | `/agent-runs/{runId}` | 200 `AgentRun` / 404 |
| **PATCH** | **`/agent-results/{resultId}`** | 200 `AgentStepResult` — 엔지니어가 결과 편집 / 404 / 409(REVIEW 상태 아님) |

### 2.4 승인

| Method | Path | 응답 |
|---|---|---|
| POST | `/work-requests/{id}/approvals` | 201 `Approval` / 404 / **409**(PENDING_APPROVAL 아님 · 요청자 자가승인) / **422**(`decision=REJECT` 인데 `reason` 없음) |

**승인 규칙 (v2.0 — 여기가 v1.0 과 가장 다르다)**
- **체크리스트 blocking 폐지.** `checklist` 필드 자체를 없앤다. 체크리스트 미완료로 409 를 내던 로직을 제거한다.
- `decision=REJECT` 면 **`reason` 필수**. 없으면 422.
- **요청자 자가승인 차단(409)은 유지한다.** Human-in-the-loop 의 핵심이라 v2.0 에서도 남긴다.
- 승인자는 `SAFETY_MANAGER` 역할만 가능. 아니면 409.

### 2.5 조회·설정 (v1.0 그대로)

| Method | Path | 응답 |
|---|---|---|
| GET | `/documents/{docId}` | 200 `Document` / 404 |
| GET | `/parts` · `/parts/{partId}/compatibility` | 200 / 404 |
| GET | `/equipments` | 200 `[Equipment]` |
| GET | `/laws/search?q=&equipmentType=&substance=` | 200 `{items:[LawArticle]}` |
| **GET** | **`/dashboard/summary?role=engineer\|safety`** | 200 `EngineerDashboard` \| `SafetyDashboard` |
| GET · PUT | `/tenants/{id}/ai-config` | 200 `[AiConfig]` / 409(외부 provider + `egress_allowed=false`) |

### 2.6 Mock 동작 (BE·Postman·FE 공통)

`POST …/agent-runs` 직후 steps **3개** 모두 `PENDING`. 이후 `GET /agent-runs/{runId}` 호출마다 다음 step 하나가 `DONE` (순서 **SPEC → LEGAL → SAFETY_DOC**). 3개 모두 DONE 이면 `overall_status=REVIEW`, `work_request.status=REVIEW`.

`BACKGROUND_ADVANCE=true` 면 GET 은 완전 read-only 가 되고 BackgroundTasks 워커가 전이시킨다. **GET 이 상태를 바꾸는 것은 Mock 단계의 의도된 설계이며 플래그로 끌 수 있다** — 이 근거를 문서·발표에서 그대로 쓴다.

### 2.7 오류 응답 포맷

FastAPI 기본 형식을 그대로 쓴다. **`{code, message, details}` 형식을 쓰지 않는다.**
```json
{ "detail": "요청자는 본인 요청을 승인할 수 없습니다" }
```
422(Pydantic 검증 실패)만 FastAPI 표준 배열 형식이다:
```json
{ "detail": [ { "type": "...", "loc": ["body","reason"], "msg": "...", "input": null } ] }
```

---

## 3. 핵심 JSON 스키마 (필드명 고정)

### User
```json
{ "id": "U-001", "tenant_id": "T-001", "name": "김민준", "email": "engineer@example.com", "role": "ENGINEER",
  "created_at": "2026-09-03T09:00:00+09:00" }
```
`password_hash` 는 **응답에 절대 포함되지 않는다.**

### WorkRequest
```json
{ "id": "WR-20260903-011", "tenant_id": "T-001", "equipment_id": "EQ-GC-02", "part_id": "P-VLV-001",
  "line": "A라인", "substance": "SiH4", "operating_condition": "상온 / 3000 psi",
  "product_name": "SS-8-VCR", "product_type": "VALVE", "spec_json": { "pressure_rating": "3000 psi" },
  "symptom": "가스 유량 이상, 밸브 누설 의심", "site_check_note": "현장 확인 결과 밸브 시트 마모",
  "engineer_note": "압력 등급 상향 반영, 제38조 작업허가 필요 판단.",
  "requested_by": "U-001", "status": "REQUESTED",
  "created_at": "2026-09-03T15:00:00+09:00", "updated_at": "2026-09-03T15:00:00+09:00" }
```
`engineer_note` 는 E_04 에서 엔지니어가 작성해 안전관리자에게 전달하는 설명이다. `submit-approval` 시 비어 있으면 **422**.

### WorkRequestSummary (목록용 — 평탄화 구조를 유지한다)
```json
{ "id": "WR-20260903-011", "equipment_id": "EQ-GC-02", "equipment_name": "가스캐비닛#2",
  "part_id": "P-VLV-001", "part_no": "VLV-SS316-1/4-NC",
  "product_name": "SS-8-VCR", "product_type": "VALVE",
  "symptom": "가스 유량 이상", "status": "RUNNING",
  "requested_by": "U-001", "requester_name": "김민준",
  "agent_progress": { "done": 2, "total": 3 },
  "approver_id": null, "created_at": "...", "updated_at": "..." }
```
**`total` 은 3 이다** (에이전트 3종). 엔지니어 메인(E_01) 테이블은 진행률 컬럼을 렌더링하지 않지만, 필드 자체는 E_03 진행 화면이 쓰므로 응답에 남긴다.

### WorkRequestDetail
`WorkRequest` 의 모든 필드 + 아래. **평탄화 구조다. `equipment`/`part`/`requester` 같은 nested 객체를 쓰지 않는다.**
```json
{ "...WorkRequest 전 필드...",
  "equipment_name": "가스캐비닛#2", "part_no": "VLV-SS316-1/4-NC", "requester_name": "김민준",
  "photos": [ { "photo_id": "PH-0001", "filename": "valve.jpg", "content_type": "image/jpeg", "size": 184320, "uploaded_at": "..." } ],
  "latest_run": { "...AgentRun..." }, "approvals": [ { "...Approval..." } ] }
```

### AgentRun (steps 3개)
```json
{ "run_id": "RUN-0042", "work_request_id": "WR-20260903-011", "overall_status": "REVIEW",
  "steps": [
    { "result_id": "RES-0001", "agent": "SPEC", "status": "DONE", "started_at": "...", "completed_at": "...", "edited": false,
      "result": { "spec_match": true, "current_part": "VLV-SS316-1/4-NC", "required_spec": "2500 psi", "input_spec": "3000 psi",
        "alternatives": [ { "part_no": "VLV-SS316-1/4-NC-EQ", "grade": "EQUIVALENT", "diff": "시트 재질 PCTFE→PTFE", "allowed_for_toxic_gas": false } ] } },
    { "result_id": "RES-0002", "agent": "LEGAL", "status": "DONE", "edited": false, "result": {
        "applicable_laws": [ { "law": "산업안전보건기준에 관한 규칙", "article": "제92조", "title": "정비등의 작업 시의 운전정지 등", "quote": "…운전을 정지하고 … 잠금장치 및 표지판을…" } ],
        "required_procedures": [ { "name": "작업허가서(가스 배관 작업)", "phase": "BEFORE", "required": true } ] } },
    { "result_id": "RES-0003", "agent": "SAFETY_DOC", "status": "DONE", "edited": false, "result": { "documents": [
        { "doc_id": "DOC-0101", "type": "WORK_PERMIT", "missing": ["작업자 2명 이름"] },
        { "doc_id": "DOC-0102", "type": "RISK_ASSESSMENT", "missing": [] } ] } }
  ],
  "summary": "OEM 동일 규격 밸브 교체. 유독가스 라인이라 호환품 불가. 작업허가·위험성평가·LOTO 필수.",
  "approval_required_by": "SAFETY_MANAGER", "model_name": "mock-v1", "prompt_version": "replaceflow-v0.2",
  "created_at": "...", "completed_at": "..." }
```
`result_id` 는 `PATCH /agent-results/{resultId}` 의 대상이다. `edited` 는 엔지니어가 수정했는지 표시하며, **수정된 항목은 화면에서 AI 원본과 시각적으로 구분한다.**

### PATCH /agent-results/{resultId} 요청 body
```json
{ "result": { "...해당 agent 의 result 전체 구조..." } }
```
부분 치환이 아니라 해당 step 의 `result` 객체를 통째로 받는다. 서버는 `edited=true` 로 표시하고 `updated_at` 을 갱신한다.

### Approval — **`checklist` 없음**
```json
{ "approval_id": "AP-0007", "work_request_id": "WR-20260903-011", "approver_id": "U-002", "approver_name": "이정호",
  "decision": "REJECT", "reason": "규격 부적합: 유독가스 라인에 호환품 불가",
  "decided_at": "2026-09-03T16:20:00+09:00" }
```
`decision=APPROVE` 면 `reason` 은 선택(생략 가능). `decision=REJECT` 면 **필수**.

### EngineerDashboard (`?role=engineer`) — 평균 승인 소요시간 없음
```json
{ "draft": 2, "running": 1, "pending_approval": 3, "rejected": 1 }
```

### SafetyDashboard (`?role=safety`)
```json
{ "pending_approval": 5, "today_processed": 7, "month_approved": 42, "month_rejected": 6,
  "reject_reasons_top": [ { "reason": "규격 부적합", "count": 9 }, { "reason": "법령 미충족", "count": 7 } ] }
```
`as_is_baseline_hours`(168) 와 `avg_approval_hours` 는 **엔지니어 대시보드에서 제거**되지만, 발표 근거로 쓰이므로 `SafetyDashboard` 에도 두지 않고 `GET /dashboard/summary` (role 미지정) 응답에만 남긴다 — 하위호환.

---

## 4. ERD 테이블 (16개 — v1.0 14개 + `photos`, `agent_results`)

`tenants` · `users` · `equipments` · `parts` · `equipment_parts` · `part_compatibility` · `work_requests` · `agent_runs` · **`agent_results`** · `legal_findings` · `documents` · `approvals` · `law_index` · `ai_configs` · `audit_logs` · **`photos`**

### 신규·변경 컬럼
- `users`: **`email` VARCHAR(255) UNIQUE NOT NULL**, **`password_hash` VARCHAR(255) NOT NULL** 추가
- `work_requests`: **`line`**, **`substance`**, **`operating_condition`**, **`product_name`**, **`product_type`**, **`spec_json` JSONB**, **`engineer_note` TEXT** 추가. `status` CHECK 에 `DRAFT` 추가
- `photos` (신규): `photo_id` VARCHAR(16) PK, `work_request_id` FK, `filename`, `content_type`, `size` INT, `storage_path`, `uploaded_at`
- `agent_results` (신규): `result_id` VARCHAR(16) PK, `agent_run_id` FK, `agent` (SPEC/LEGAL/SAFETY_DOC), `result` JSONB, `edited` BOOLEAN DEFAULT FALSE, `updated_at`
- `approvals`: **`checklist` 컬럼 삭제**, `reason` TEXT 추가 (REJECT 시 NOT NULL — 애플리케이션 레벨 검증)
- `law_index`: **`id` 를 `VARCHAR(32)` PK 로** (SERIAL 아님, `LAW-NNNN` 규칙). 필터 컬럼은 `equipment_types` / `substances` **JSONB 배열**

### 유지해야 할 N:M 2개 (루브릭 직결 — 깨뜨리지 말 것)
`equipment_parts` (equipments↔parts 복합 PK) · `part_compatibility` (parts↔parts 자기참조 복합 PK)

### 알려진 정규화 한계 (숨기지 말고 `erd.md` 에 명시한다)
1. `part_compatibility.allowed_for_toxic_gas` 가 `parts.toxic_gas_allowed` 와 **중복 저장** — 2NF 부분함수종속. 동기화 제약이 없어 안전 게이트가 낡은 값으로 돌 수 있다
2. `legal_findings` 가 조문과 절차를 한 행에 섞어 조문 스냅샷이 중복 — 3NF
3. `work_requests.tenant_id` 이행종속 + 복합 FK 부재로 **교차 테넌트 행이 제약 없이 저장 가능**

---

## 5. 화면 9종 (WRA — 화면정의서 v2.0)

| Screen ID | 경로 | 역할 | 비고 |
|---|---|---|---|
| `WRA_C_00` | `/login` | 공통 | 성공 시 역할 분기 → E_01 / S_01 |
| `WRA_C_01` | `/signup` | 공통 | 역할 선택 필수 (엔지니어/안전관리자) |
| `WRA_E_01` | `/home` | 엔지니어 | KPI 4 (작성중·진행중·승인대기·반려) + 최근 요청. **평균 승인시간·진행률 컬럼 없음** |
| `WRA_E_02` | `/requests/new` | 엔지니어 | 동적 스펙 5종 + 사진 업로드 |
| `WRA_E_03` | `/requests/{id}/run` | 엔지니어 | 에이전트 **3종** 카드, 2~3초 폴링 |
| `WRA_E_04` | `/requests/{id}/result` | 엔지니어 | 결과 **편집** + `engineer_note` 작성 후 제출 |
| `WRA_E_05` | `/my/requests` | 엔지니어 | 상태 탭 필터, 거절 사유 열람·재제출 |
| `WRA_S_01` | `/manage/requests` | 안전관리자 | KPI 4 + 승인 대기 목록 + 거절 사유 TOP5 |
| `WRA_S_02` | `/manage/requests/{id}` | 안전관리자 | AI 결과 **읽기 전용** + 승인/거절+사유 |

---

## 6. 샘플 데이터 (모든 산출물이 같은 샘플 사용)

- tenant `T-001` "○○반도체(하이닉스 2차 협력사)"
- users (**비밀번호는 전부 `Passw0rd!`**, 시드에서 해시로 저장):
  - `U-001` 김민준 `engineer@replaceflow.test` ENGINEER
  - `U-002` 이정호 `safety@replaceflow.test` SAFETY_MANAGER
  - `U-003` 박수진 `buyer@replaceflow.test` BUYER
  - `U-004` 관리자 `admin@replaceflow.test` ADMIN
- equipments: `EQ-GC-02` 가스캐비닛#2(GAS_CABINET, SiH4) · `EQ-VLV-07` 공정가스 밸브#7(VALVE, NH3) · `EQ-SCR-01` 스크러버#1(SCRUBBER)
- parts: `P-VLV-001` VLV-SS316-1/4-NC(OEM, toxic_gas_allowed=true, stock 2) · `P-VLV-002` VLV-SS316-1/4-NC-EQ(EQUIVALENT, false, stock 5) · `P-REG-001` REG-2S(OEM) · `P-FLT-001` 인라인 필터(EQUIVALENT)
- law_index 6건: `LAW-0001`~`LAW-0006` — 산안규칙 91·92·93·319조, 화관법 24조, 고압가스법 시행규칙 별표
- work_requests **6건** — 상태 각 1건: `DRAFT` · `RUNNING` · `REVIEW` · `PENDING_APPROVAL` · `APPROVED` · `REJECTED`(사유 포함)

---

## 7. 계약 변경 이력

| 시각 | 변경 | 근거 |
|---|---|---|
| 2026-09-02 | v1.0 확정 | 기획서 E안v3 |
| 2026-09-03 | **v2.0** — 역할 분리·인증·동적 스펙·사진·에이전트 3종·결과 편집·체크리스트 폐지 | `WRA_화면정의서_v2.0`(09-03 10:23), 팀 결정 |
