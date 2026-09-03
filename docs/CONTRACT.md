# 공통 계약서 v3.0 — 부품 교체 요청·승인 시스템 (REQ-F-0001)

> **이 파일은 팀 노션의 두 문서를 저장소로 옮긴 것이다. 창작이 아니다.**
> 원본 ①「API 명세서 v1.0 (REQ-F-0001)」 ②「FixGuide 데이터 모델 정의서 v3.0」 ③「WRA 화면정의서 v2.0」 — 전부 2026-09-03.
> **원본과 다르면 원본이 맞다.** 충돌을 발견하면 고치지 말고 보고하라.
> 쓰기 권한: 오케스트레이터 전용. v2.0(폐기)은 `CONTRACT_v2.0_superseded.md`, v1.0 은 `CONTRACT_v1.0_archived.md`.

스택: FE Vue 3 + Vite + axios · BE FastAPI (Python 3.10+) · DB PostgreSQL(Supabase) — 로컬 SQLite 폴백

> ✅ **명칭 확정: `Argus`** (2026-09-03, 팀장 결정). 이전 표기였던 `ReplaceFlow` 와 ERD 문서 제목의 `FixGuide` 는 전부 폐기한다. 코드·문서·발표자료·시드 계정 이메일(`@argus.test`)까지 이 이름 하나로 통일한다.

---

## 1. 공통 규약

| 항목 | 규약 |
|---|---|
| Base URL | `/api/v1` |
| 인증 | **JWT Bearer** — `Authorization: Bearer {accessToken}`. `/auth/signup`, `/auth/login` 제외 **전 API 필수** |
| Content-Type | `application/json; charset=utf-8` (사진 업로드만 `multipart/form-data`) |
| 시각 | ISO 8601 · **KST 오프셋 포함** — `2026-09-03T10:22:00+09:00` |
| **ID** | **UUID v4 문자열** — `WR-` 같은 접두어 ID 를 쓰지 않는다 |
| 페이지네이션 | `page`(**0-base**, 기본 0) · `size`(기본 20, 최대 100). 응답에 `page` 객체 포함 |
| 정렬 | `sort=필드,asc\|desc` — 기본 `createdAt,desc` (목록은 `submittedAt,desc`) |
| 권한 | `ENGINEER` 는 **본인 요청만** 조회·수정 / `SAFETY_MANAGER` 는 **PENDING 이상 전체** 조회·승인. 위반 시 **403** |
| 필드 표기 | **camelCase** (`workRequestId`, `requestNo`, `engineerNote`, `agentResultId`) |

### 1.1 공통 에러 응답 — 모든 4xx·5xx 단일 포맷
```json
{ "code": "EMAIL_ALREADY_EXISTS", "message": "이미 사용 중인 이메일입니다",
  "fieldErrors": [ { "field": "email", "message": "중복된 이메일" } ] }
```
`fieldErrors` 는 **입력 유효성 오류(400·422)에서만** 포함, 그 외 생략.
> FastAPI 기본 `{"detail": ...}` 이 아니다. 예외 핸들러로 위 포맷을 강제한다.

---

## 2. 도메인 Enum (정확히 이 문자열)

| Enum | 값 |
|---|---|
| `Role` | `ENGINEER` · `SAFETY_MANAGER` |
| `WorkRequestStatus` | `DRAFT` · `AI_RUNNING` · `AI_DONE` · `PENDING` · `APPROVED` · `REJECTED` |
| `ProductType` | `VALVE` · `FITTING_TUBE` · `REGULATOR` · `FILTER` · `ETC` |
| `AgentCode` | `A1` · `A2` · `A3` |
| `AgentStepStatus` | `WAITING` · `RUNNING` · `DONE` · `FAILED` |
| `RunStatus` | `RUNNING` · `DONE` · `FAILED` |
| `ApprovalDecision` | `APPROVE` · `REJECT` |

### 상태 화면 대응
| 값 | 화면 표기 | 의미 | 다음 액션 |
|---|---|---|---|
| `DRAFT` | 작성 중 | 임시 저장, AI 미실행 | E_02 이어쓰기 |
| `AI_RUNNING` | AI 검증중 | 3종 중 미완료 존재 | E_03 |
| `AI_DONE` | 결과 확인 대기 | A1·A2·A3 전부 완료, 미제출 | E_04 |
| `PENDING` | 승인 대기 | 안전관리자에게 제출됨 | S_02 |
| `APPROVED` | 승인 | 종결 | — |
| `REJECTED` | 거절·보완 | 사유와 함께 반려 | E_04 재진입 → 재제출 |

### 에이전트 3종
`A1` 규격·호환(입력 스펙 기반) · `A2` 법령·조문 · `A3` 안전서류(허가서·위험성평가)
**Phase 2**: A1 부품 마스터·호환표 연동, **A4 벤더 에이전트**

### ProductType → specJson 필수 키 (서버가 유형별 스키마 검증, 불일치 시 400 `SPEC_SCHEMA_MISMATCH`)
| productType | 화면 표기 | 필수 키 | 예시 |
|---|---|---|---|
| `VALVE` | 밸브 | `pressureRating` | `{"pressureRating":"3000 psi"}` |
| `FITTING_TUBE` | 피팅·튜브 | `connectionStandard`, `material` | `{"connectionStandard":"1/4 in VCR","material":"SUS316L"}` |
| `REGULATOR` | 레귤레이터 | `pressureRating` | `{"pressureRating":"250 psi"}` |
| `FILTER` | 필터 | `substanceType` | `{"substanceType":"N2"}` |
| `ETC` | 기타 | `freeSpec` | `{"freeSpec":"씰킷 세트, 내열 200℃"}` |

---

## 3. 상태 전이

```
POST /work-requests (draft=true) ──▶ DRAFT ──(PATCH 이어쓰기)──┐
                                        │ POST /agent-runs      │
                                        ▼                       │
       AI_RUNNING ──(A1·A2·A3 모두 DONE)──▶ AI_DONE ◀───────────┘
                                        │ PATCH submit-approval
                                        ▼
                    APPROVED ◀─(POST /approvals APPROVE)─ PENDING
                                        │ POST /approvals REJECT + reason
                                        ▼
           (E_04 수정 후 재제출) ◀───── REJECTED
```

| 전이 | 트리거 | 조건 / 오류 |
|---|---|---|
| — → `DRAFT` | `POST /work-requests` `draft=true` | 필수 검증 생략 |
| — / `DRAFT` → `AI_RUNNING` | `POST /work-requests` `draft=false` 후 `POST /agent-runs` | 필수값 누락 **400**, 진행 중 run 존재 **409** |
| `AI_RUNNING` → `AI_DONE` | 마지막 step DONE (`allDone:true`) | 서버가 전환 |
| `AI_DONE`/`REJECTED` → `PENDING` | `PATCH …/submit-approval` | 3종 결과 존재 · `engineerNote` · A2 1건 이상, 아니면 **422** |
| `PENDING` → `APPROVED`/`REJECTED` | `POST /approvals` | SAFETY_MANAGER만(**403**), PENDING 아니면 **409**, REJECT 사유 없으면 **400** |
| `PENDING`·`APPROVED` | 수정 시도 | `PATCH /work-requests` **409 IMMUTABLE_STATUS** / `PATCH /agent-results` **409 RESULT_LOCKED** |

---

## 4. API 15개

| # | Method | Path | 화면 | 권한 |
|---|---|---|---|---|
| 1 | POST | `/auth/signup` | C_01 | 공개 |
| 2 | POST | `/auth/login` | C_00 | 공개 |
| 3 | GET | `/auth/me` | 공통 | 인증 |
| 4 | GET | `/dashboard/summary?role=engineer\|safety` | E_01, S_01 | 인증 |
| 5 | POST | `/work-requests` | E_02 | ENGINEER |
| 6 | GET | `/work-requests?mine=&status=&page=&size=&sort=` | E_01, E_05, S_01 | 인증 |
| 7 | GET | `/work-requests/{id}` | E_04, E_05, S_02 | 인증 |
| 8 | PATCH | `/work-requests/{id}` | E_02, E_04 | ENGINEER |
| 9 | POST | `/work-requests/{id}/photos` | E_02 | ENGINEER |
| 10 | GET | `/work-requests/{id}/photos` | S_02 | 인증 |
| 11 | POST | `/agent-runs` | E_02 | ENGINEER |
| 12 | GET | `/agent-runs/{runId}` | E_03 | 인증 |
| 13 | PATCH | `/agent-results/{id}` | E_04 | ENGINEER |
| 14 | PATCH | `/work-requests/{id}/submit-approval` | E_04 | ENGINEER |
| 15 | POST | `/approvals` | S_02 | SAFETY_MANAGER |

> `POST /agent-runs` 는 **`/work-requests/{id}/agent-runs` 가 아니다.** body 에 `workRequestId` 를 담는다.
> `POST /approvals` 도 최상위 경로다. body 에 `workRequestId` 를 담는다.

### 주요 요청·응답 규칙

**1 signup**: `name`(2~20자) · `email`(유니크) · `password`(8자 이상, 영문+숫자+특수문자) · `passwordConfirm` · `role`. → 201.
오류 400 `VALIDATION_FAILED` / 400 `PASSWORD_MISMATCH` / 409 `EMAIL_ALREADY_EXISTS`

**2 login**: → 200 `{accessToken, role, redirectPath}`. **`redirectPath` 는 서버가 내려준다** — `ENGINEER`→`/home`, `SAFETY_MANAGER`→`/manage/requests`. 프론트는 그 값을 그대로 쓴다. 오류 401 `INVALID_CREDENTIALS`

**3 me**: 새로고침·직접 URL 진입 시 역할별 GNB 렌더링용. 오류 401 `TOKEN_EXPIRED`/`TOKEN_INVALID`

**4 dashboard**: `role` 필수. **토큰 역할과 불일치 시 403.**
- `role=engineer` → `{draft, aiRunning, pending, rejected}`. **평균 승인 소요시간 없음**
- `role=safety` → `{pending, todayProcessed, monthApproved, monthRejected, rejectReasonsTop}`

> **필드명 확정**: 승인 대기 KPI 는 두 대시보드 모두 **`pending`** 이다. `pendingApproval` 이 아니다 —
> 상태 enum 이 `PENDING` 이므로 그것과 일치시킨다. (BE·FE 구현이 이미 `pending` 이었고, 명세서 원문 JSON 블록이
> 로드되지 않아 미확정이던 구간이다. 원본에 다른 이름이 있으면 원본이 맞다.)

**5 create**: `equipment`·`line`·`substance`·`operatingCondition{temperature,pressure}`·`productName`·`productType`·`specJson` 은 **`draft=false` 일 때만 필수**. `symptom`·`siteMemo` 선택. `draft=true` 면 전부 선택이고 상태만 `DRAFT`. → 201

**6 list**: `status` 는 **콤마 다중 지정 가능**(`REJECTED,DRAFT`). 응답 `content[]` + `page{}`. 각 항목에 **`nextAction`** 포함 — 서버가 계산: `DRAFT`→이어서(E_02) · `AI_RUNNING`→진행(E_03) · `AI_DONE`→결과(E_04) · 그 외→상세. 빈 목록은 200 + `content: []`

**7 detail**: `agentRun`(steps·results) + `approval`(최신 1건, 미처리 시 `null`) 포함.
**SAFETY_MANAGER 조회 시 `agentRun.results[].editable` 은 항상 `false`.**
오류 403 `FORBIDDEN_NOT_OWNER` / 404 `WORK_REQUEST_NOT_FOUND`

**8 patch**: 부분 수정. 가능 필드 — `equipment` `line` `substance` `operatingCondition` `productName` `productType` `specJson` `symptom` `siteMemo` **`engineerNote`**. 오류 409 `IMMUTABLE_STATUS` / 403 `FORBIDDEN_NOT_OWNER`

**9 photos upload**: `multipart/form-data`, 파트명 **`files`(배열)**. jpg/png/webp · **파일당 10MB** · **요청당 최대 5장**. **EXIF 제거 + 320px 썸네일 생성.** → 201.
오류 400 `UNSUPPORTED_FILE_TYPE` / **413** `FILE_TOO_LARGE` / 409 `PHOTO_LIMIT_EXCEEDED`

**11 agent-runs**: body 는 `{workRequestId}` 만. **서버가 workRequestId 로 전체 스냅샷을 구성**해 에이전트에 보낸다(설비·라인·물질·운전조건·제품명·유형·스펙·사진 메타). → **202**.
오류 409 `RUN_ALREADY_IN_PROGRESS` / 400 `WORK_REQUEST_INCOMPLETE`

**12 polling**: 응답에 `steps[]` · **`allDone`** · **`pollIntervalMs: 2500`**(서버가 내려준다). `allDone:true` 시 프론트는 폴링 중단, [결과 확인] 활성화, 서버는 `AI_DONE` 전환.
**step 실패 시 해당 step 만 `status:"FAILED"` + `errorMessage`, HTTP 는 200 유지.** 오류 404 `AGENT_RUN_NOT_FOUND`

**13 agent-results patch**: **전체 치환(PUT-like).** 배열에 없는 기존 `itemId` 는 **삭제**, `itemId` 없이 `text` 만 오면 **신규 추가**(서버 채번). 추가·삭제·편집을 1회 호출로.
- A1·A2 (항목형): `{ "items": [ {"itemId":"i-01","text":"…","edited":false} ] }`
- A3 (문서형): `{ "documents": [ {"docId":"d-01","type":"WORK_PERMIT","name":"작업허가서 초안","content":"…","edited":false} ] }`
오류 409 `RESULT_LOCKED` / 403 `FORBIDDEN_NOT_OWNER`

**14 submit-approval**: 서버 검증 4가지 — ①A1·A2·A3 결과 전부 존재 ②`engineerNote` 비어 있지 않음 ③**A2 적용 법령 1건 이상** ④상태가 `AI_DONE` 또는 `REJECTED`. 실패 시 **422 `SUBMIT_REQUIRED_FIELD_MISSING`**.
**재제출**: `REJECTED` 에서 동일 API 호출 → `PENDING` 복귀, **직전 approval 이력 보존**

**15 approvals**: body `{workRequestId, decision, reason?, reasonCategory?}`. `reason` 은 REJECT 시 필수 **10자 이상**. → 201.
오류 **400 `REJECT_REASON_REQUIRED`** / 403 `FORBIDDEN_ROLE` / 409 `ALREADY_DECIDED` / 409 `NOT_PENDING`
**체크리스트 blocking 없음.** 승인은 사유 없이 즉시, 거절만 사유 필수.

---

## 5. DB — 테이블 7개 + 제안 1개

### 설계 원칙 (ERD 문서 원문)
1. **대리키 PK** — 전 테이블 UUID v4. 업무 식별자(`users.email`, `work_requests.request_no`, `agent_steps`/`agent_results`의 `(run_id, agent_code)`)는 **UNIQUE**. 번호·코드 체계가 바뀌어도 FK 무결성 유지
2. **사실 / 추론 / 행동 분리** — 입력(`work_requests`) · AI 산출(`agent_runs`/`agent_steps`/`agent_results`) · 사람의 결정(`approvals`)을 테이블로 분리. **위 층이 아래 층을 덮어쓰지 않는다**
3. **append-only 이력** — `agent_runs`(재실행), `approvals`(재제출 후 재결정)는 갱신하지 않고 **행을 추가**. 최신 1건을 화면에 노출
4. **jsonb 는 구조가 가변인 곳에만** — `operating_condition`, `spec_json`, `payload_json`. 조회·집계 키(`status`, `agent_code`, `reason_category`, `edited`)는 **컬럼**
5. **상태는 PostgreSQL enum** (룩업 테이블 아님)

### 테이블
| # | 테이블 | 핵심 컬럼 |
|---|---|---|
| 1 | `users` | `id` uuid PK · `name` varchar(20) · `email` varchar(120) **UNIQUE** · `password_hash` varchar(255) **bcrypt** · `role` enum · `created_at` |
| 2 | `work_requests` | `id` uuid PK · **`request_no` varchar(20) UNIQUE** (`WR-YYYYMMDD-NNN`, 서버 채번) · `requester_id` FK · `equipment` varchar(80) · `line` varchar(50) · `substance` varchar(80) · `operating_condition` jsonb · `product_name` varchar(120) · `product_type` enum · `spec_json` jsonb · `symptom` text · `site_memo` text · `engineer_note` text · `status` enum default `DRAFT` · `created_at` · `updated_at` · `submitted_at` |
| 3 | `work_request_photos` | `id` uuid PK · `work_request_id` FK · `file_name` · `storage_key` · `thumbnail_key` · `size` int · `uploaded_at` |
| 4 | `agent_runs` | `id` uuid PK · `work_request_id` FK · `status` enum default RUNNING · `started_at` · `finished_at` · **`input_snapshot` jsonb (구현됨)** · **[제안·미구현]** `ai_config_id` FK |
| 5 | `agent_steps` | `id` uuid PK · `run_id` FK · `agent_code` enum · `status` enum default WAITING · `message` varchar(200) · `error_message` text · `started_at` · `finished_at` · **UNIQUE(run_id, agent_code)** |
| 6 | `agent_results` | `id` uuid PK · `run_id` FK · `agent_code` enum · `payload_json` jsonb · `edited` bool default false · `updated_at` · **`original_json` jsonb (구현됨)** · **UNIQUE(run_id, agent_code)** |
| 7 | `approvals` | `id` uuid PK · `work_request_id` FK · `approver_id` FK · `decision` enum · `reason` text · `reason_category` varchar(30) · `decided_at` |
| 8 | **[제안 · v3.0 미구현]** `ai_configs` | `id` uuid PK · `agent_code` · `provider`(MOCK/LOCAL_LLM/OPENAI) · `model_name` · `prompt_version` · `temperature` numeric(3,2) · `max_tokens` · `egress_allowed` bool default false · `is_active` bool · **부분 유니크 `UNIQUE(agent_code) WHERE is_active`**. **API 키는 넣지 않는다(환경변수)** |

**인덱스**: `work_requests(requester_id, status)` E_01·E_05 / `work_requests(status, submitted_at)` S_01 / `request_no` UNIQUE / `approvals(work_request_id, decided_at)` / `approvals(decided_at)`

**DRAFT 허용을 위해 `work_requests` 의 업무 컬럼은 DB NOT NULL 이 아니다.** `draft=false` 조건부 검증은 **서비스 계층**에서.

### 관계 (전부 1:N)
`users→work_requests` · `users→approvals` · `work_requests→work_request_photos`(최대 5) · `work_requests→agent_runs`(재실행) · `work_requests→approvals`(append-only) · `agent_runs→agent_steps`(고정 3) · `agent_runs→agent_results`(고정 3) · `ai_configs→agent_runs`

> ⚠️ **N:M 은 이번 범위에 없다** (ERD 문서 명시). 법령 마스터·설비 마스터·호환표는 Phase 2.
> **루브릭이 "1:N, N:M 관계"를 요구하므로 감점 위험이 있다. 팀 판단 필요 사항으로 보고됨.**

---

## 6. 에러 코드 (전체 23종)

| 상태 | code |
|---|---|
| 400 | `VALIDATION_FAILED` · `PASSWORD_MISMATCH` · `SPEC_SCHEMA_MISMATCH` · `REJECT_REASON_REQUIRED` · `UNSUPPORTED_FILE_TYPE` · `WORK_REQUEST_INCOMPLETE` |
| 401 | `INVALID_CREDENTIALS` · `TOKEN_EXPIRED` · `TOKEN_INVALID` |
| 403 | `FORBIDDEN_ROLE` · `FORBIDDEN_NOT_OWNER` |
| 404 | `WORK_REQUEST_NOT_FOUND` · `AGENT_RUN_NOT_FOUND` |
| 409 | `EMAIL_ALREADY_EXISTS` · `RUN_ALREADY_IN_PROGRESS` · `IMMUTABLE_STATUS` · `RESULT_LOCKED` · `ALREADY_DECIDED` · `NOT_PENDING` · `PHOTO_LIMIT_EXCEEDED` |
| 413 | `FILE_TOO_LARGE` |
| 422 | `SUBMIT_REQUIRED_FIELD_MISSING` |
| 500 | `INTERNAL_ERROR` |

---

## 7. 화면 ↔ API 매트릭스

| Screen ID | 화면 | Role | 호출 API |
|---|---|---|---|
| `WRA_C_00` | 로그인 `/login` | 공통 | 2 |
| `WRA_C_01` | 회원가입 `/signup` | 공통 | 1 |
| `WRA_E_01` | 엔지니어 메인 `/home` | ENGINEER | 4(engineer) · 6(mine) · 7 |
| `WRA_E_02` | 요청 등록 `/requests/new` | ENGINEER | 5 · 9 · 11 |
| `WRA_E_03` | AI 검증 진행 `/requests/{id}/run` | ENGINEER | 12(폴링) · 7 |
| `WRA_E_04` | 결과 확인·수정 `/requests/{id}/result` | ENGINEER | 7 · 13 · 8 · 14 |
| `WRA_E_05` | 내 요청 목록 `/my/requests` | ENGINEER | 6 · 7 · 14 |
| `WRA_S_01` | 요청 관리 `/manage/requests` | SAFETY_MANAGER | 4(safety) · 6(status=PENDING) |
| `WRA_S_02` | 요청 상세 `/manage/requests/{id}` | SAFETY_MANAGER | 7 · 10 · 15 |

---

## 8. 팀 확인 필요 (원본 9절 — 임의로 정하지 말 것)

1. 제출 경로를 `PATCH /work-requests/{id}/submit-approval` 로 확정 — 대상 식별 필요
2. **`AI_DONE` 신설** — 화면정의서엔 문구만 있고 코드값 없었음. E_03/E_04 구분용
3. `GET /auth/me` 신설 — AC 에 없으나 새로고침 시 필요
4. `nextAction` 을 서버가 계산 — 프론트 분기로 바꿔도 무방
5. 결과 수정 = **전체 치환** — 항목 단위 API 로 쪼갤지 확인
6. `reasonCategory` — 고정 5종 enum 으로 굳힐지 자유 입력으로 둘지 **확인 필요**
7. 사진 업로드는 요청 생성 이후 구조 — E_02 에서 저장 전 업로드하려면 **DRAFT 선생성 전제**
8. `approvals` append-only 다건 유지 — 단건 갱신으로 갈지 확인
9. 폴링 주기 `pollIntervalMs: 2500` 서버 제공 — SSE/WebSocket 은 Phase 2
10. Phase 2 범위 — A1 부품 마스터·호환표, A4 벤더 에이전트

---

## 9. 계약 변경 이력

| 시각 | 버전 | 내용 |
|---|---|---|
| 09-02 | v1.0 | 기획서 E안v3 기준 (보존: `CONTRACT_v1.0_archived.md`) |
| 09-03 오후 | v2.0 | 오케스트레이터가 화면정의서에서 **추론**해 작성 — **팀 권위 문서와 불일치하여 폐기** (`CONTRACT_v2.0_superseded.md`) |
| 09-03 | **v3.0** | 팀 「API 명세서 v1.0」 + 「데이터 모델 정의서 v3.0」 + 「WRA 화면정의서 v2.0」을 **그대로 옮김** |


---

## 10. 구현 실측 정정 (2026-09-03 16:00)

계약이 `[추가 제안]` 으로 표시한 3개 중 **2개는 실제로 구현됐다.** 팀 ERD 원문은 제안이었으나 BE 가 채택했다.

| 항목 | 계약 표기 | 실측 |
|---|---|---|
| `agent_runs.input_snapshot` | [제안] | **구현됨** — `backend/app/models/agent.py` |
| `agent_results.original_json` | [제안] | **구현됨** — 동 파일 |
| `ai_configs` 테이블 + `agent_runs.ai_config_id` | [제안] | **미구현.** 설정 격리는 `backend/app/core/config.py` 의 환경변수 계층으로 구현. `validate_egress()` 가 외부 provider + `egress_allowed=false` 조합에서 **기동 자체를 거부**한다(fail-fast). 멀티테넌트 확장 시 이 테이블로 승격 |

DDL·DBML 에는 `ai_configs` 를 남겨 두되 "미구현, 승격 대상" 주석을 달았다 — 팀 ERD 의 설계 의도를 지우지 않기 위해서다.
