# ReplaceFlow 시스템 아키텍처

문서 버전: v1.0 (2026-09-02) · 기준: `docs/CONTRACT.md`, 기획서 v3 7~10장
다이어그램: `architecture.mmd`(전체 구성), `state_machine.mmd`(`work_requests.status`), `sequence_agent_run.mmd`(에이전트 실행~승인 시퀀스)

---

## 1. 전체 구성 개요

```
[모니터링(Mock)] ─알람─▶ ┌──────────── BE FastAPI ────────────┐
[FE Vue 3] ◀─REST JSON─▶ │ Router → Service → Repository       │──▶ [PostgreSQL / SQLite]
  화면1 목록·대시보드      │  AgentOrchestrator ─┬ SpecAgent      │
  화면2 타임라인·승인패널  │                     ├ LegalAgent ────┼──▶ [law_index ← 법제처 Open API]
  /glass (선택)           │                     ├ SafetyDocAgent │
                          │                     └ VendorAgent    │
                          │  ApprovalService(상태머신·게이트)     │
                          │  ai_configs: provider=LOCAL_LLM,      │
                          │              egress_allowed=false     │
                          └────────────────────────────────────────┘
확장: [Queue] [사내 GPU LLM / A.X 플랫폼] [Vector DB] [ERP·BOM·벤더 포털] [사내 메신저]
```

설계 전제는 **온프레미스**다. 외부 클라우드 AI를 쓸 수 없는 팹 환경이므로 LLM·법령 지식·설정이 모두 사내에 머무는 구조로 잡고, PoC(3일)에서는 에이전트 4개를 Mock 구현체로 대체하되 인터페이스·상태머신·JSON 계약을 실제 산출물로 남긴다.

---

## 2. 컴포넌트 설명

### 2.1 FE — Vue 3 + Vite + axios

| 구성 | 역할 | 사용 API |
|---|---|---|
| 화면 1 작업요청 목록 / 대시보드 | KPI 타일, 요청 테이블(상태·에이전트 진행률·승인자), 반려 사유 TOP5, 상태 필터·페이징 | `GET /api/v1/dashboard/summary`, `GET /api/v1/work-requests?status=&page=&size=` |
| 화면 2 작업요청 상세 = 에이전트 타임라인 + 승인 패널 | 상단 요청 정보, 중앙 `SPEC`/`LEGAL`/`SAFETY_DOC`/`VENDOR` 4카드(`대기 → 실행 중 → 완료`), 우측 승인 패널(조문 링크, 체크리스트 4항목, 서류 초안, 승인/반려/보완요청) | `GET /work-requests/{id}`, `POST /work-requests/{id}/agent-runs`, `GET /agent-runs/{runId}`(3초 폴링), `GET /documents/{docId}`, `GET /parts/{partId}/compatibility`, `PATCH /work-requests/{id}/submit-approval`, `POST /work-requests/{id}/approvals` |
| `/glass` 선택 채널 | 같은 API를 쓰는 현장 확인용 축약 뷰. 필수 아님 | 화면 2와 동일 |
| axios api client | base URL `/api/v1`, 응답 코드(202/409/422) 분기, 폴링 타이머 | — |

FE는 에이전트 내부를 모른다. FE가 의존하는 유일한 것은 `AgentRun` JSON(`steps[].agent`, `steps[].status`, `steps[].result`, `summary`, `overall_status`)이다.

### 2.2 BE — FastAPI (Python 3.11)

#### Controller (routers)

| 라우터 | 엔드포인트 | 응답 코드 |
|---|---|---|
| `work_requests` | `GET /work-requests`, `POST /work-requests`, `GET /work-requests/{id}`, `POST /work-requests/{id}/agent-runs`, `PATCH /work-requests/{id}/submit-approval`, `POST /work-requests/{id}/approvals` | 200 / 201 / 202 / 404 / 409 / 422 |
| `agent_runs` | `GET /agent-runs/{runId}` | 200 / 404 |
| `documents`, `parts`, `equipments`, `laws` | `GET /documents/{docId}`, `GET /parts`, `GET /parts/{partId}/compatibility`, `GET /equipments`, `GET /laws/search?q=&equipmentType=&substance=` | 200 / 404 |
| `dashboard`, `tenants` | `GET /dashboard/summary`, `GET /tenants/{id}/ai-config`, `PUT /tenants/{id}/ai-config` | 200 |

라우터는 요청 검증(Pydantic 스키마)과 HTTP 코드 매핑만 담당하고 비즈니스 규칙은 갖지 않는다.

#### Service

| 서비스 | 책임 |
|---|---|
| `WorkRequestService` | 작업요청 생성·조회, `WorkRequestDetail`(latest_run, approvals 포함) 조립 |
| **`AgentOrchestrator`** | `agent_runs` 생성(4 step `PENDING`), `work_requests.status`를 `RUNNING`으로 전이, 4개 `AgentService` 실행·상태 관리, 결과 통합(`summary`, `approval_required_by = SAFETY_MANAGER`), 4 step `DONE` 시 `overall_status = REVIEW` 및 `work_requests.status = REVIEW`. step 실패 시 `FAILED` 기록 |
| **`AgentService` 인터페이스 x4** | `SpecAgent(SPEC)`, `LegalAgent(LEGAL)`, `SafetyDocAgent(SAFETY_DOC)`, `VendorAgent(VENDOR)`. 공통 시그니처 `run(context) -> StepResult`. 구현체는 `Mock`(고정 JSON, 폴링마다 다음 step 1개 `DONE`)과 `LLM`(확장: `LOCAL_LLM` / `AX_PLATFORM` / `OPENAI`)이며 `ai_configs` + 환경변수로 선택 |
| **`ApprovalService`** | `work_requests.status` 상태머신 보호. `submit-approval`(REVIEW → PENDING_APPROVAL, 누락 시 422, run 미완료 시 409)과 `approvals` 생성(PENDING_APPROVAL → APPROVED / REJECTED / REVIEW). **체크리스트 게이트**: `WORK_PERMIT`, `RISK_ASSESSMENT`, `LOTO_GAS_ISOLATION`, `GAS_DETECTOR_CHECK` 모두 `true`가 아니면 `APPROVE`는 409 |
| `DashboardService` | `DashboardSummary` 집계(`in_progress`, `pending_approval`, `avg_approval_hours`, `as_is_baseline_hours = 168`, `completed_this_month`, `reject_reasons_top`) |
| `LawSearchService` | `law_index` 검색(`q`, `equipmentType`, `substance`) |
| `AiConfigService` | 테넌트별 `ai_configs` 조회·갱신, `egress_allowed` 정책 검증 |

#### Repository (SQLAlchemy)

`WorkRequestRepo`, `AgentRunRepo`, `ApprovalRepo`, `DocumentRepo`, `LegalFindingRepo`, `LawIndexRepo`, `PartRepo`, `EquipmentRepo`, `AiConfigRepo`, `AuditLogRepo`. 서비스는 Repository 인터페이스만 보며 PostgreSQL/SQLite 전환은 `DATABASE_URL`만 바꾼다.

### 2.3 DB — PostgreSQL (Supabase), 로컬 SQLite 폴백

| 층 | 테이블 | 비고 |
|---|---|---|
| 마스터 | `tenants`, `users`, `equipments`, `parts`, `equipment_parts`, `part_compatibility` | 멀티테넌트 기준 `tenant_id` |
| 요청(사실) | `work_requests` | `status` 7단계 |
| 에이전트 산출 | `agent_runs`(`steps_json`, `overall_status`, `summary`, `model_name`, `prompt_version`), `legal_findings`(조문 단위), `documents`(`type`, `body`, `missing_json`, `version`) | `legal_findings`는 건별 스냅샷 |
| 사람의 결정 | `approvals`(`decision`, `checklist_json`, `comment`, `decided_at`) | 승인 이력 |
| 지식·설정·감사 | `law_index`(법제처 사전 적재), `ai_configs`, `audit_logs` | |

정규화 포인트: 요청(사실) / 에이전트 산출 / 사람의 결정을 3층으로 분리하고, 법령은 `law_index`(원문)와 `legal_findings`(이 건에 적용된 조문)를 분리하여 법 개정 시 과거 판단을 보존한다.

### 2.4 외부 · 확장

| 구성 | PoC | 확장 |
|---|---|---|
| 모니터링 시스템 | Mock 알람(수동 입력) | 알람 → 자동 작업요청 생성 |
| 법제처 국가법령정보 Open API | 샘플 6조문 시드(산안규칙 91·92·93·319조, 화관법 24조, 고압가스법 시행규칙 별표) | 전량 배치 적재, 개정 이력 관리 |
| 사내 GPU LLM / SK AX A.X 플랫폼 | 미구축(`model_name = mock-v1`) | `LegalAgent` 등 LLM 구현체가 `provider`에 따라 연결 |
| Vector DB | 없음(`law_index` 테이블 검색) | `LEGAL` RAG 인덱스 |
| ERP · BOM · 벤더 포털 · 사내 메신저 | 없음 | `SpecAgent`/`VendorAgent` 실연동, 승인 코멘트 알림 |
| Queue | 없음(폴링 1회당 step 1개 전이) | 실 병렬 실행·재시도 |

### 2.5 설정

| 위치 | 내용 |
|---|---|
| `ai_configs` 테이블 | `tenant_id`, `agent_type`(`SPEC`/`LEGAL`/`SAFETY_DOC`/`VENDOR`), `provider`(`LOCAL_LLM`/`AX_PLATFORM`/`OPENAI`), `model_name`, `prompt_version`, `egress_allowed`(기본 `false`) — `GET/PUT /tenants/{id}/ai-config`로 운영 중 변경 |
| `.env` / 환경변수 | `DATABASE_URL`, `AGENT_MODE=mock|llm`, `LLM_ENDPOINT`, API 키. 코드·레포에 값을 두지 않는다 |

---

## 3. AI-Ready 4원칙 매핑

| 원칙 | 설계 | 구체 참조 |
|---|---|---|
| **Interface First** | FE와 BE는 OpenAPI 계약(`AgentRun` JSON)으로만 결합. BE 내부는 `AgentService` 추상 인터페이스에 Mock/LLM 구현체를 꽂는다. 오케스트레이터도 구현체를 모른다 | 엔드포인트 `GET /api/v1/agent-runs/{runId}` → `AgentRun{run_id, overall_status, steps[], summary, approval_required_by, model_name, prompt_version}` · 코드 `services/agents/base.py`(`AgentService.run`), `services/agents/mock/*.py`, `services/agents/llm/*.py`, `services/orchestrator.py` · 문서 `docs/07_api/openapi.yaml` |
| **Structured Data** | 에이전트 산출을 자유 텍스트가 아닌 스키마 고정 JSON으로 저장하고, 검색·추적이 필요한 값은 컬럼·정규화 테이블로 뺀다 | `agent_runs.steps_json`(step별 `agent`/`status`/`result`), 검색 컬럼 `agent_runs.overall_status`, `model_name`, `prompt_version` · `legal_findings`(`law`, `article`, `title`, `quote`, `procedure_name`, `phase`, `required`) · `documents`(`type`, `missing_json`, `version`) · `approvals.checklist_json` · `law_index`(원문) 분리 · 문서 `docs/06_erd/erd.dbml` |
| **Asynchronous Pipeline** | 실행 요청은 즉시 202로 돌려주고 진행 상태는 폴링으로 본다. step 단위 상태(`PENDING`/`RUNNING`/`DONE`/`FAILED`)가 타임라인 UI의 데이터원이다 | `POST /api/v1/work-requests/{id}/agent-runs` → 202 `{run_id, overall_status:"RUNNING"}` · `GET /api/v1/agent-runs/{runId}` 3초 폴링 · Mock 규칙: 호출마다 `SPEC → LEGAL → SAFETY_DOC → VENDOR` 순으로 1 step `DONE`, 4개 `DONE` 시 `overall_status = REVIEW`, `work_requests.status = REVIEW` · 코드 `services/orchestrator.py`, FE `useAgentRunPolling.ts` · 확장: Queue 워커로 교체해도 API 계약 불변 |
| **Security & Config Isolation** | 온프레미스 전제를 데이터로 표현. 에이전트별 모델·프롬프트 버전·외부 전송 허용 여부를 테넌트 단위로 분리하고 비밀값은 환경변수에만 둔다 | `ai_configs`(`provider = LOCAL_LLM` 기본, `egress_allowed = false` 기본, `agent_type`별 `model_name`/`prompt_version`) · `GET/PUT /api/v1/tenants/{id}/ai-config` · `law_index` 사내 사전 적재(외부 조회 없음) · `.env`(`DATABASE_URL`, `LLM_ENDPOINT`, 키) · `audit_logs`(`before_json`/`after_json`) · 프롬프트 파일 `prompts/legal/replaceflow-v0.1.md` 버전 관리 |

---

## 4. 계층 구조 (Controller → Service → Repository)

```
app/
├─ main.py                       # FastAPI app, /api/v1 prefix, 라우터 등록
├─ routers/                      # Controller: HTTP 입출력, 상태코드 매핑
│  ├─ work_requests.py           # GET/POST /work-requests, /{id}, /{id}/agent-runs, /{id}/submit-approval, /{id}/approvals
│  ├─ agent_runs.py              # GET /agent-runs/{runId}
│  ├─ catalog.py                 # /documents, /parts, /equipments, /laws/search
│  └─ admin.py                   # /dashboard/summary, /tenants/{id}/ai-config
├─ schemas/                      # Pydantic: WorkRequest, WorkRequestDetail, AgentRun, Approval, DashboardSummary, AiConfig ...
├─ services/                     # 비즈니스 규칙
│  ├─ work_request_service.py
│  ├─ orchestrator.py            # AgentOrchestrator
│  ├─ approval_service.py        # 상태머신 + 체크리스트 게이트
│  ├─ dashboard_service.py, law_search_service.py, ai_config_service.py
│  └─ agents/
│     ├─ base.py                 # AgentService(Protocol): run(context) -> StepResult
│     ├─ mock/  spec.py legal.py safety_doc.py vendor.py
│     └─ llm/   spec.py legal.py safety_doc.py vendor.py   (확장)
├─ repositories/                 # SQLAlchemy: 테이블당 1 Repo
├─ models/                       # ORM 14 테이블
├─ core/config.py                # Settings(.env): DATABASE_URL, AGENT_MODE, LLM_ENDPOINT
└─ seed/                         # 샘플 데이터 (T-001, U-001~U-004, EQ-*, P-*, law_index 6건, work_requests 5건)
```

호출 방향은 항상 Router → Service → Repository 한 방향이다. Router는 Repository를 직접 호출하지 않고, Service는 HTTP 개념(Request/Response/status code)을 모른다. 상태 전이는 오직 `AgentOrchestrator`(`REQUESTED → RUNNING → REVIEW`)와 `ApprovalService`(`REVIEW → PENDING_APPROVAL → APPROVED/REJECTED/REVIEW`, `APPROVED → DONE`) 두 곳에서만 일어난다.

---

## 5. 확장 시 교체 지점

| 교체 대상 | 지금 | 확장 후 | 바뀌는 곳 | 바뀌지 않는 곳 |
|---|---|---|---|---|
| 에이전트 구현체 | `services/agents/mock/*` | `services/agents/llm/*` (사내 GPU LLM 또는 A.X 플랫폼 호출) | `AGENT_MODE=llm`, `ai_configs.provider` | `AgentService` 시그니처, `AgentRun` JSON, FE 전체 |
| `LEGAL` 지식원 | `law_index` 테이블 검색(6조문) | 법제처 Open API 전량 적재 + Vector DB RAG | `LawIndexRepo` 구현, 적재 배치 | `legal_findings` 스키마, 승인 패널 |
| 실행 방식 | 폴링 1회당 step 1개 전이(Mock) | Queue 워커 실 병렬 실행, 재시도 | `orchestrator.py` 내부 실행 전략 | 202/폴링 API, step 상태값 |
| 규격·벤더 데이터 | 사내 DB(`parts`, `part_compatibility`, 구매 이력) | ERP·BOM·벤더 포털 연동 | `SpecAgent`/`VendorAgent` 구현체, 커넥터 | `SPEC`/`VENDOR` result 스키마 |
| 알림 | 없음(화면 내 코멘트) | 사내 메신저 알림 | `ApprovalService` 후처리 훅 | `approvals` 스키마 |
| 요청 생성 트리거 | 사람 입력 | 모니터링 알람 → 자동 생성 | 알람 수신 라우터 추가 | `POST /work-requests` 계약 |
| DB | SQLite(로컬) / PostgreSQL(Supabase) | PostgreSQL 사내 인스턴스 | `DATABASE_URL` | Repository 이상 전 계층 |
| LLM provider | `LOCAL_LLM`(Mock) | `AX_PLATFORM`, `OPENAI`(외부 허용 테넌트만) | `ai_configs.provider`, `egress_allowed` | 코드 |

원칙은 하나다: **교체는 구현체와 설정에서 일어나고, 계약(API JSON·DB 스키마·상태값)은 유지된다.**
