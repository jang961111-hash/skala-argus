# Argus(FixGuide) 시스템 아키텍처

문서 버전: v3.0 (2026-09-03) · 기준: `docs/CONTRACT.md` v3.0(단일 진실 원천 — 팀 「API 명세서 v1.0」+「데이터 모델 정의서 v3.0」+「WRA 화면정의서 v2.0」을 그대로 옮긴 문서), `docs/06_erd/erd.md`
다이어그램: `architecture.mmd`(전체 구성), `state_machine.mmd`(`work_requests.status`), `sequence_agent_run.mmd`(에이전트 실행~승인 시퀀스) — v3.0 상태값(`DRAFT/AI_RUNNING/AI_DONE/PENDING/APPROVED/REJECTED`)·에이전트 3종(A1/A2/A3) 반영은 다이어그램 소유 트랙에서 별도 갱신 필요
이전 버전: v1.0(14테이블)·v2.0(16테이블, 오케스트레이터가 화면정의서에서 **추론**해 작성 — 팀 권위 문서와 불일치해 **폐기**)는 각각 `CONTRACT_v1.0_archived.md`/`CONTRACT_v2.0_superseded.md` 참조. **v3.0 은 팀 ERD(8테이블)를 그대로 옮긴 버전**이며 이 문서도 그 번역이다.

---

## 1. 전체 구성 개요

```
[FE Vue 3] ◀─REST JSON(camelCase)─▶ ┌──────────── BE FastAPI ──────────────────┐
  로그인/회원가입(C_00/C_01)          │ Auth(JWT Bearer, 전 API 필수 — auth 제외)  │──▶ [PostgreSQL / SQLite, 8테이블]
  엔지니어 화면 5종(E_01~E_05)        │ Router → Service → Repository              │      (UUID PK, ENUM 7종)
  안전관리자 화면 2종(S_01/S_02)      │  AgentOrchestrator ─┬ A1(규격·호환)         │
                                    │                     ├ A2(법령·조문)         │
                                    │                     └ A3(안전서류)          │
                                    │  ApprovalService(append-only, 사유만 필수)   │
                                    │  ai_configs([제안]): provider=MOCK,          │
                                    │              egress_allowed=false           │
                                    └──────────────────────────────────────────────┘
확장(Phase 2): [A1 부품 마스터·호환표 연동] [A4 벤더 에이전트] [법령 마스터 N:M] [Queue] [사내 GPU LLM/A.X] [SSE/WebSocket]
```

설계 전제는 **온프레미스**이며, PoC(3일) 범위에서는 에이전트를 Mock 구현체로 대체하되 인터페이스·상태머신·JSON 계약을 실제 산출물로 남긴다. **v3.0 은 팀이 이미 확정한 ERD·API 명세를 그대로 옮긴 버전**이라 v2.0(오케스트레이터가 추론한 16테이블)과 구조가 크게 다르다 — 설비·부품·법령 **마스터 테이블이 없다.** `work_requests.equipment`/`substance`/`product_name` 등은 전부 자유 입력 컬럼이고, N:M 관계는 이번 범위에 0개다(마스터가 생기는 Phase 2 로 미룸 — `erd.md` §3).

---

## 2. 컴포넌트 설명

### 2.1 FE — Vue 3 + Vite + axios

| 구성 | 역할 | 호출 API(CONTRACT §4 번호) |
|---|---|---|
| 로그인·회원가입 (`WRA_C_00`/`C_01`) | 로그인 성공 시 서버가 `redirectPath` 를 내려주고 FE 는 그대로 이동(엔지니어→`/home`, 안전관리자→`/manage/requests`). 회원가입은 ENGINEER/SAFETY_MANAGER 만 선택 가능 | #1 `POST /auth/signup`, #2 `POST /auth/login`, #3 `GET /auth/me` |
| 엔지니어 메인 (`E_01`, `/home`) | KPI 4(작성중·진행중·승인대기·반려), 평균 승인시간 없음. `nextAction` 은 서버가 계산해 내려줌(`DRAFT`→이어쓰기, `AI_RUNNING`→진행, `AI_DONE`→결과, 그 외→상세) | #4 `GET /dashboard/summary?role=engineer`, #6 `GET /work-requests?mine=true`, #7 |
| 요청 등록 (`E_02`, `/requests/new`) | 동적 스펙 5종(`ProductType`) + 사진(최대 5장, `multipart/form-data` 필드명 `files`) | #5 `POST /work-requests`(`draft=`), #9 `POST .../photos`, #11 `POST /agent-runs` |
| AI 검증 진행 (`E_03`, `/requests/{id}/run`) | `steps[]`·`allDone`·`pollIntervalMs`(서버 지정, 2500ms) 폴링. `allDone:true` 시 폴링 중단 | #12 `GET /agent-runs/{runId}`(폴링), #7 |
| 결과 확인·수정 (`E_04`, `/requests/{id}/result`) | 결과 편집(전체 치환), `engineerNote` 작성 후 제출 | #7, #13 `PATCH /agent-results/{id}`, #8 `PATCH /work-requests/{id}`, #14 `PATCH .../submit-approval` |
| 내 요청 목록 (`E_05`, `/my/requests`) | 상태 필터(콤마 다중), 거절 사유 열람·재제출 | #6, #7, #14(재제출) |
| 요청 관리 (`S_01`, `/manage/requests`) | KPI 4 + `status=PENDING` 승인 대기 목록 | #4(`role=safety`), #6 |
| 요청 상세 (`S_02`, `/manage/requests/{id}`) | AI 결과 **읽기 전용**(`results[].editable` 항상 `false`) + 승인/거절(사유 필수) | #7, #10 `GET .../photos`, #15 `POST /approvals` |
| axios api client | base URL `/api/v1`, `Authorization: Bearer <token>` 헤더 필수(auth 제외), 단일 에러 포맷 `{code, message, fieldErrors?}`(**FastAPI 기본 `{detail}` 아님** — 예외 핸들러로 강제), 필드는 camelCase | — |

FE 가 의존하는 것은 `WorkRequestDetail`(`agentRun.steps[]`, `agentRun.results[]`, `approval`) JSON 뿐이다. `POST /agent-runs`·`POST /approvals` 는 **`/work-requests/{id}/...` 하위 경로가 아니라 최상위 경로**이고 body 에 `workRequestId` 를 담는다 — v1.0/v2.0 과 가장 크게 달라진 지점이라 Q&A 리스크가 있다.

### 2.2 BE — FastAPI (Python 3.10+)

#### Controller (routers, 실제 디렉터리 `backend/app/api/v1/routers/` — v1.0/v2.0 세션에서 존재를 확인한 경로. **단, 아래 엔드포인트 내용은 CONTRACT v3.0 계약이며 이 절 작성 시점에 BE 트랙이 v3.0 에 맞춰 재구현 중이라 라우터 파일명·1:1 매핑은 단정하지 않는다** — Q&A 에서 파일 위치를 물으면 "BE 트랙 확인"으로 답한다.)

| # | Method | Path | 화면 | 권한 |
|---|---|---|---|---|
| 1 | POST | `/auth/signup` | C_01 | 공개 |
| 2 | POST | `/auth/login` | C_00 | 공개 |
| 3 | GET | `/auth/me` | 공통 | 인증 |
| 4 | GET | `/dashboard/summary?role=engineer\|safety` | E_01, S_01 | 인증(토큰 role 불일치 403) |
| 5 | POST | `/work-requests` | E_02 | ENGINEER |
| 6 | GET | `/work-requests?mine=&status=&page=&size=&sort=` | E_01, E_05, S_01 | 인증 |
| 7 | GET | `/work-requests/{id}` | E_04, E_05, S_02 | 인증(본인 아니면 403 `FORBIDDEN_NOT_OWNER`) |
| 8 | PATCH | `/work-requests/{id}` | E_02, E_04 | ENGINEER(`PENDING`/`APPROVED` 는 409 `IMMUTABLE_STATUS`) |
| 9 | POST | `/work-requests/{id}/photos` | E_02 | ENGINEER |
| 10 | GET | `/work-requests/{id}/photos` | S_02 | 인증 |
| 11 | POST | `/agent-runs`(**최상위**, body `{workRequestId}`) | E_02 | ENGINEER |
| 12 | GET | `/agent-runs/{runId}` | E_03 | 인증 |
| 13 | PATCH | `/agent-results/{id}` | E_04 | ENGINEER(`RESULT_LOCKED` 409) |
| 14 | PATCH | `/work-requests/{id}/submit-approval` | E_04 | ENGINEER |
| 15 | POST | `/approvals`(**최상위**, body `{workRequestId, decision, reason?}`) | S_02 | SAFETY_MANAGER |

라우터는 요청 검증과 HTTP 코드 매핑만 담당한다. 전 엔드포인트(1~3 제외)가 `Authorization: Bearer <token>` 필요(CONTRACT §1). 에러는 `{code, message, fieldErrors?}` 단일 포맷 — FastAPI 기본 `{"detail": ...}` 를 그대로 쓰지 않고 예외 핸들러로 강제한다(§2.7).

#### Service

| 서비스 | 책임 |
|---|---|
| `AuthService` | `signup`(이메일 중복 409 `EMAIL_ALREADY_EXISTS`, 비밀번호 확인 불일치 400 `PASSWORD_MISMATCH`), `login`(JWT 발급 + `redirectPath` 계산, 401 `INVALID_CREDENTIALS`), `me`. `password_hash` 는 bcrypt, 응답에 절대 미포함 |
| `WorkRequestService` | 요청 생성(`draft` 여부로 필수 검증 분기), `PATCH` 부분 수정(`IMMUTABLE_STATUS` 가드), `WorkRequestDetail`(`agentRun`, `approval` 최신 1건, `photos`) 조립, `nextAction` 계산 |
| **`AgentOrchestrator`** | `POST /agent-runs` 시 `work_requests` 전체 스냅샷 구성 → `agent_runs` 1행 + `agent_steps`/`agent_results` **고정 3행**(A1/A2/A3) 생성, 상태 `DRAFT/REJECTED`→`AI_RUNNING` 전이. 마지막 step DONE 시 `allDone:true`, `work_requests.status`→`AI_DONE`. step 실패는 해당 step 만 `FAILED`+`errorMessage`(HTTP 200 유지) |
| **`AgentService` 인터페이스 x3(A1/A2/A3)** | 공통 시그니처 `run(context) -> dict`. Mock 은 payload_json 을 `{"items":[...]}`(A1/A2) 또는 `{"documents":[...]}`(A3) 형태로 채운다. `ai_configs`(제안 테이블)로 provider(MOCK/LOCAL_LLM/OPENAI) 선택. **A4(벤더) 는 Phase 2, 지금은 존재하지 않는다** |
| `ApprovalService` | `submit-approval`: A1·A2·A3 결과 전부 존재 + `engineerNote` 비어있지 않음 + A2 결과 1건 이상 + 상태가 `AI_DONE`/`REJECTED` — 하나라도 실패 시 422 `SUBMIT_REQUIRED_FIELD_MISSING`. `POST /approvals`: SAFETY_MANAGER 만(403 `FORBIDDEN_ROLE`), `PENDING` 아니면 409 `NOT_PENDING`, 이미 결정됐으면 409 `ALREADY_DECIDED`, `REJECT` 인데 사유 없거나 10자 미만이면 400 `REJECT_REASON_REQUIRED`. **체크리스트 blocking 없음** — 승인은 즉시, 거절만 사유 필수. append-only(새 `approvals` 행 추가, 재제출 시 직전 이력 보존) |
| `DashboardService` | `role=engineer`(작성중·진행중·승인대기·반려보완 4개, 평균 승인시간 없음) / `role=safety`(승인대기·오늘처리·이번달승인·이번달거절 + `rejectReasonsTop`) |

#### Repository (SQLAlchemy, `backend/app/repositories/`)

CONTRACT v3.0 테이블 8개(`users`, `work_requests`, `work_request_photos`, `agent_runs`, `agent_steps`, `agent_results`, `approvals`, `ai_configs`)에 대응하는 Repository 구성은 BE 트랙 재구현 진행 중이다. v1.0/v2.0 에서 검증된 패턴(테이블 성격이 가까운 것끼리 Repository 를 묶는 방식, 예: `AgentRunRepository` 가 `agent_runs`/`agent_steps`/`agent_results` 를 함께 다루는 식)이 유지될 가능성이 높지만, 정확한 클래스 분할은 BE 트랙 확인 필요. 모든 PK 가 UUID 로 바뀌어(CONTRACT §1) v1.0/v2.0 의 접두어 문자열 채번 로직(`ids.py`)은 v3.0 에서 `gen_random_uuid()`/`uuid4()` 로 대체된다.

### 2.3 DB — PostgreSQL(Supabase), 로컬 SQLite 폴백

**v3.0: 16 → 8테이블**(v2.0 확장분 전량 폐기, 팀 ERD 로 재작성). 전체 컬럼·인덱스·설계 원칙 5가지·N:M 부재 근거는 `docs/06_erd/erd.md` 가 상세 소유 문서다.

| 층 | 테이블 | 비고 |
|---|---|---|
| 사용자 | `users` | `email`/`password_hash`(bcrypt)/`role`(ENGINEER\|SAFETY_MANAGER 만) |
| 요청(사실) | `work_requests`(`request_no` UNIQUE, `equipment`/`line`/`substance`/`operating_condition`/`product_name`/`product_type`/`spec_json` 전부 자유 입력·마스터 없음), `work_request_photos`(최대 5장, 앱 레벨) | `status` 6종(`DRAFT`~`REJECTED`) |
| AI 산출(append-only) | `agent_runs`, `agent_steps`(run 당 A1/A2/A3 고정 3행), `agent_results`(run 당 고정 3행, `payload_json`+`edited`) | 재실행 시 `agent_runs` 새 행 추가(UPDATE 아님) |
| 사람의 결정(append-only) | `approvals`(`decision`, `reason`, `reason_category`, `decided_at`) | 재제출 후 재결정도 새 행 |
| 설정([제안]) | `ai_configs`(`agent_code` 당 활성 설정 1개, 부분 유니크) | API 키는 두지 않음(환경변수) |

PK 는 전 테이블 **UUID v4**(`gen_random_uuid()`) — v1.0/v2.0 의 `WR-`/`RUN-` 같은 접두어 문자열 PK 를 v3.0 에서 전량 폐기했다. **마스터 테이블(설비·부품·법령) 이 없어 N:M 관계가 0개다** — 의도적 스코프 조정이며 Phase 2 예비 설계는 `erd.md` §3 에 미리 첨부돼 있다.

### 2.4 외부 · 확장(Phase 2)

| 구성 | PoC(v3.0) | 확장 |
|---|---|---|
| 설비·부품 마스터 | 없음 — `work_requests` 자유 입력 컬럼 | A1 부품 마스터·호환표 연동(N:M `equipments`↔`parts`, `erd.md` §3 예비 설계) |
| 법령 지식원 | 없음 — A2 가 텍스트로만 조문 인용(`agent_results.payload_json.items[].text`) | 법령 마스터 + `agent_results`↔`law_index` N:M(`erd.md` §3 예비 설계) |
| 벤더 견적(A4) | 없음(Phase 2) | `agent_code` ENUM 에 `A4` 추가, `ai_configs`/`agent_results` 는 재확장 가능하게 설계됨 |
| 사내 GPU LLM / A.X 플랫폼 | 미구축(`provider = MOCK`) | `ai_configs.provider = LOCAL_LLM`/`OPENAI` 전환 |
| 실시간 갱신 | 폴링(`pollIntervalMs=2500`, 서버 지정) | SSE/WebSocket(CONTRACT §8-9, 팀 확인 필요) |
| Queue | 없음 | 실 병렬 실행·재시도 |

### 2.5 설정 · 인증

| 위치 | 내용 |
|---|---|
| `ai_configs` 테이블([제안]) | `agent_code`(A1/A2/A3), `provider`(MOCK/LOCAL_LLM/OPENAI — CONTRACT 7종 Enum 에 없어 VARCHAR+CHECK), `model_name`, `prompt_version`, `temperature`, `max_tokens`, `egress_allowed`(기본 `false`), `is_active`(부분 유니크: `agent_code` 당 활성 1개) |
| 인증 | JWT Bearer, `/auth/signup`·`/auth/login` 제외 전 API 필수. 3일 범위에서는 서명된 토큰이면 충분(구체 알고리즘은 BE 트랙 결정) |
| `.env` / 환경변수 | `DATABASE_URL`, `AGENT_MODE=mock\|llm`, `LLM_ENDPOINT`, `SECRET_KEY`(JWT 서명), API 키. 코드·레포에 값을 두지 않는다 |

---

## 3. AI-Ready 4원칙 매핑

| 원칙 | 설계 | 구체 참조 |
|---|---|---|
| **Interface First** | FE와 BE는 API 계약(`WorkRequestDetail`/`AgentRun` JSON)으로만 결합. BE 내부는 `AgentService` 추상 인터페이스에 Mock/LLM 구현체를 꽂는다 | 엔드포인트 #12 `GET /agent-runs/{runId}` → `steps[]`+`allDone` · 코드 `services/agents/base.py`, `services/agents/mock_agents.py`, `services/agents/llm_agents.py`, `services/orchestrator.py`(BE 재구현 진행 중, §2.2 참고) · 문서 `docs/07_api/openapi.yaml`(v3.0 반영은 API 트랙 소유) |
| **Structured Data** | 에이전트 산출을 `agent_steps`(진행 상태, 오케스트레이터가 초 단위 갱신) / `agent_results`(결과, 엔지니어가 편집) 로 분리해 갱신 경합을 없앤다(`erd.md` §4). 집계 키(`status`, `agent_code`, `reason_category`, `edited`)는 컬럼, 가변 구조(`spec_json`, `payload_json`, `original_json`)만 jsonb | `agent_steps`/`agent_results`(UNIQUE `run_id,agent_code`) · `approvals.reason_category`(TOP5 집계용) · `work_requests.spec_json`(`product_type` 별 동적 스펙) · 문서 `docs/06_erd/argus.dbml` |
| **Asynchronous Pipeline** | `POST /agent-runs` 는 즉시 202, 진행 상태는 폴링(`pollIntervalMs=2500`, 서버 지정)으로 본다. `allDone:true` 시 폴링 중단·`AI_DONE` 전환. step 실패는 HTTP 200 유지, 해당 step 만 `FAILED` | #11 `POST /agent-runs` → 202 · #12 `GET /agent-runs/{runId}`(폴링) · Mock 규칙: 호출마다 A1→A2→A3 순 1 step `DONE` · FE `frontend/src/components/AgentTimeline.vue`(폴링 로직 위치, 간격 값은 v3.0 서버 지정으로 갱신 필요) · 확장: SSE/WebSocket 으로 교체해도 `WorkRequestDetail` 계약 불변 |
| **Security & Config Isolation** | v3.0 신규: **JWT Bearer 인증**이 전 API(auth 제외) 필수, `ENGINEER`=본인만/`SAFETY_MANAGER`=PENDING 이상 전체라는 권한 분리가 라우터가 아니라 서비스 계층에서 강제된다(위반 403). 비밀번호는 bcrypt 해시로만 저장 | `users.password_hash`(bcrypt, 응답 미포함) · `SECRET_KEY`(JWT 서명, `.env`) · `POST /auth/login`·`GET /auth/me` · `ai_configs.egress_allowed`(기본 `false`) · 프롬프트 파일 `docs/05_ai_ready/prompts.md`(`## <AGENT_TYPE>` 섹션 단위) 버전 관리 |

---

## 4. 계층 구조 (Controller → Service → Repository)

```
app/
├─ main.py                       # FastAPI app, /api/v1 prefix, 라우터 등록
├─ api/v1/routers/               # Controller: HTTP 입출력, 상태코드 매핑 (파일 분할은 BE 트랙 확인 필요, §2.2)
│  auth / work_requests / agent_runs / agent_results / approvals / dashboard  (CONTRACT §4 15개 API 기준)
├─ schemas/                      # Pydantic: camelCase 응답 모델(CONTRACT §1 필드 표기), 단일 에러 포맷 {code,message,fieldErrors}
├─ services/                     # 비즈니스 규칙
│  ├─ auth_service.py(예정)      # JWT 발급·bcrypt 해시
│  ├─ work_request_service.py, orchestrator.py, approval_service.py, dashboard_service.py
│  └─ agents/
│     ├─ base.py                 # AgentService(ABC): run(context) -> dict
│     ├─ mock_agents.py          # A1MockAgent / A2MockAgent / A3MockAgent (A4 는 Phase 2, 존재하지 않음)
│     └─ llm_agents.py           # A1LLMAgent / A2LLMAgent / A3LLMAgent (확장)
├─ repositories/                 # SQLAlchemy: 8테이블 대응(§2.2), UUID 채번은 gen_random_uuid()/uuid4()
├─ models/                       # ORM 8 테이블(v3.0: users/work_requests/work_request_photos/agent_runs/agent_steps/agent_results/approvals/ai_configs) — v2.0 의 16테이블(equipments/parts/law_index 등)은 전량 폐기
├─ core/config.py                # Settings(.env): DATABASE_URL, AGENT_MODE, LLM_ENDPOINT, SECRET_KEY, prompts_path
└─ seed.py                       # 샘플 데이터 — WorkRequestStatus 6종 각 1건(CONTRACT 에 샘플 데이터 절 없음, docs/06_erd/seed_data.sql 이 설계 기준)
```
v3.0 은 v2.0 대비 도메인 모델이 근본적으로 바뀌어(마스터 테이블 제거, UUID PK, 엔드포인트 경로 변경) 위 트리는 CONTRACT 계약 기준 목표 구조다. **`docs/05_ai_ready/prompts.md`, `frontend/src/components/AgentTimeline.vue`, `backend/app/api/v1/routers/` 디렉터리 자체의 실재는 이전 세션에 확인됐고 유효하다** — 그 안의 라우터별 엔드포인트 내용만 v3.0 으로 다시 구현되는 중이다.

호출 방향은 항상 Router → Service → Repository 한 방향이다. 상태 전이는 `AgentOrchestrator`(`DRAFT/REJECTED → AI_RUNNING → AI_DONE`)와 `ApprovalService`(`AI_DONE/REJECTED → PENDING → APPROVED/REJECTED`) 두 곳에서만 일어난다.

---

## 5. 확장 시 교체 지점

| 교체 대상 | 지금(v3.0 PoC) | 확장 후 | 바뀌는 곳 | 바뀌지 않는 곳 |
|---|---|---|---|---|
| 에이전트 구현체 | `services/agents/mock_agents.py` | `services/agents/llm_agents.py`(사내 GPU LLM/A.X) | `AGENT_MODE=llm`, `ai_configs.provider` | `AgentService` 시그니처, `agent_results.payload_json` 구조, FE |
| 설비·부품 마스터(A1) | 없음(자유 입력 varchar) | 마스터 테이블 + `equipments`↔`parts` N:M 호환표(`erd.md` §3 예비 설계) | `work_requests` 컬럼→FK 전환, A1 구현체 | `product_type`/`spec_json` 계약 |
| 법령 지식원(A2) | 없음(텍스트만 인용) | 법령 마스터 + `agent_results`↔`law_index` N:M | A2 구현체, 적재 배치 | `agent_results.payload_json` 항목형 구조 |
| 벤더 에이전트(A4) | 없음 | `agent_code` ENUM 확장, 신규 `A4MockAgent`/`A4LLMAgent` | ENUM, `ai_configs` 행 추가 | `agent_steps`/`agent_results` 스키마(고정 N행 → N+1행으로 자연 확장) |
| 실행 방식 | 폴링(2500ms, Mock 은 호출마다 1 step) | Queue 워커 실 병렬 실행·재시도, 또는 SSE/WebSocket | `orchestrator.py` 내부 전략 | `agent_steps` 상태값, 폴링 API 계약(전환 전까지) |
| DB | SQLite(로컬) / PostgreSQL(Supabase) | PostgreSQL 사내 인스턴스 | `DATABASE_URL` | Repository 이상 전 계층 |
| LLM provider | `MOCK` | `LOCAL_LLM`, `OPENAI`(egress 허용 시) | `ai_configs.provider`, `egress_allowed` | 코드 |

원칙은 하나다: **교체는 구현체와 설정에서 일어나고, 계약(API JSON·DB 스키마·상태값)은 유지된다.**
