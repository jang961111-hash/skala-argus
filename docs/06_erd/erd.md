# ReplaceFlow ERD 설명서

- 서비스: **ReplaceFlow** — 반도체 설비 부품 교체 승인 프로세스 에이전트
- 기준 문서: `docs/CONTRACT.md`, 기획서 9장(ERD)
- 산출물
  - `replaceflow.dbml` — dbdiagram.io 용 DBML (테이블 14개, Enum 9개, Ref 20개, TableGroup 4개)
  - `schema_postgres.sql` — PostgreSQL(Supabase) DDL: ENUM 타입, 테이블, FK, CHECK, 인덱스, `updated_at` 트리거
  - `seed_data.sql` — CONTRACT 샘플 데이터 (테넌트 1 · 사용자 4 · 설비 3 · 부품 4 · 법령 6 · 요청 5 · run 4 · 서류 3 · 승인 1 · AI 설정 4 · 감사로그 2)
- 상태값·필드명은 CONTRACT.md 와 문자 단위로 동일하다 (`work_requests.status`, `agent_runs.overall_status`, `steps_json` 구조 등).

---

## 1. 테이블 설명 (14)

### 마스터

| 테이블 | PK | 설명 | 주요 컬럼 |
|---|---|---|---|
| `tenants` | `id` | 테넌트(협력사 단위). 모든 업무 데이터의 최상위 파티션 키 | `name`, `plan` |
| `users` | `id` | 사용자. `role` 로 화면·권한 분기 | `tenant_id`, `name`, `email`, `role(ENUM user_role)` |
| `equipments` | `id` | 설비 마스터 | `tenant_id`, `name`, `type`(GAS_CABINET/VALVE/PIPING/SCRUBBER… 개방형), `line`, `substances(jsonb 배열)` |
| `parts` | `id` | 부품 마스터 | `tenant_id`, `part_no`, `spec(jsonb)`, `grade(ENUM part_grade)`, `toxic_gas_allowed`, `stock` |
| `equipment_parts` | (`equipment_id`,`part_id`) | 설비-부품 BOM (N:M 연결) | `installed_at`, `last_replaced_at`, `qty` |
| `part_compatibility` | (`part_id`,`alt_part_id`) | 부품 호환표 (parts 자기참조 N:M) | `diff`, `allowed_for_toxic_gas` |

### 트랜잭션 — 요청(사실) → 에이전트 산출 → 사람의 결정

| 테이블 | PK | 설명 | 주요 컬럼 |
|---|---|---|---|
| `work_requests` | `id` (WR-…) | 교체 작업 요청. 상태머신 `REQUESTED→RUNNING→REVIEW→PENDING_APPROVAL→APPROVED\|REJECTED→DONE` | `equipment_id`, `part_id`, `symptom`, `site_check_note`, `requested_by`, `status`, `created_at`, `updated_at` |
| `agent_runs` | `id` (RUN-…) | 에이전트 실행 1회. `steps_json` 이 API `AgentRun.steps` 원본 | `work_request_id`, `overall_status`, `steps_json`, `summary`, `approval_required_by`, `model_name`, `prompt_version`, `completed_at` |
| `legal_findings` | `id` (serial) | 이 건에 적용된 법령 조문 + 요구 절차 **스냅샷** | `agent_run_id`, `law_index_id(nullable)`, `law`, `article`, `title`, `quote`, `procedure_name`, `phase`, `required` |
| `documents` | `id` (DOC-…) | A3/A4 가 만든 서류 초안 | `agent_run_id`, `type(ENUM document_type)`, `title`, `body`, `missing_json`, `version` |
| `approvals` | `id` (AP-…) | 사람의 결정. 승인 주체는 `SAFETY_MANAGER` | `work_request_id`, `approver_id`, `decision(ENUM)`, `checklist_json`, `comment`, `decided_at` |

### AI

| 테이블 | PK | 설명 | 주요 컬럼 |
|---|---|---|---|
| `law_index` | `id` (serial) | 법령 조문 인덱스(법제처 사전 적재, Structured Data). A2 LEGAL 검색 원천 | `law`, `article`, `title`, `text`, `equipment_type`, `substance`, `effective_date`, `source_uri` |

### 설정

| 테이블 | PK | 설명 | 주요 컬럼 |
|---|---|---|---|
| `ai_configs` | (`tenant_id`,`agent_type`) | 테넌트×에이전트별 모델·프롬프트·egress 설정 (Security & Config Isolation) | `provider(ENUM ai_provider)`, `model_name`, `prompt_version`, `egress_allowed` |
| `audit_logs` | `id` (bigserial) | 변경 전/후 스냅샷 감사 로그 | `tenant_id`, `user_id(nullable=시스템)`, `entity`, `entity_id`, `action`, `before_json`, `after_json` |

### ENUM (CONTRACT 상태값 그대로)

| 타입 | 값 |
|---|---|
| `work_request_status` | REQUESTED, RUNNING, REVIEW, PENDING_APPROVAL, APPROVED, REJECTED, DONE |
| `agent_run_status` | RUNNING, REVIEW, FAILED |
| `step_status` (steps_json 내부 값) | PENDING, RUNNING, DONE, FAILED |
| `agent_type` | SPEC, LEGAL, SAFETY_DOC, VENDOR |
| `user_role` | ENGINEER, SAFETY_MANAGER, BUYER, ADMIN |
| `approval_decision` | APPROVE, REJECT, REQUEST_INFO |
| `document_type` | WORK_PERMIT, RISK_ASSESSMENT, LOTO_CHECKLIST, RFQ |
| `part_grade` | OEM, EQUIVALENT, REFURB |
| `ai_provider` | LOCAL_LLM, AX_PLATFORM, OPENAI |

---

## 2. 관계 요약

### 1:N

| 부모 | 자식 (FK) | 의미 |
|---|---|---|
| `tenants` | `users.tenant_id`, `equipments.tenant_id`, `parts.tenant_id`, `work_requests.tenant_id`, `ai_configs.tenant_id`, `audit_logs.tenant_id` | 테넌트 격리 |
| `users` | `work_requests.requested_by`, `approvals.approver_id`, `audit_logs.user_id` | 요청자 / 승인자 / 행위자 |
| `equipments` | `work_requests.equipment_id` | 어떤 설비의 요청인가 |
| `parts` | `work_requests.part_id` | 어떤 부품을 교체하는가 |
| `work_requests` | `agent_runs.work_request_id`, `approvals.work_request_id` | 요청 1건에 실행 여러 번(재실행), 결정 여러 번(보완요청→승인) |
| `agent_runs` | `legal_findings.agent_run_id`, `documents.agent_run_id` | 실행 1회가 낳은 법령 판단·서류 |
| `law_index` | `legal_findings.law_index_id` (nullable) | 스냅샷이 참조한 원문 |

### N:M

| 관계 | 연결 테이블 | 비고 |
|---|---|---|
| `equipments` ↔ `parts` | `equipment_parts (equipment_id, part_id)` | 한 설비에 여러 부품, 한 부품이 여러 설비에 장착 (BOM) |
| `parts` ↔ `parts` (자기참조) | `part_compatibility (part_id, alt_part_id)` | 기준 부품 → 대체 부품 방향성 호환표. `CHECK part_id <> alt_part_id` |

### 3층 분리 (기획서 9장 정규화 포인트)

```
[사실]       work_requests ──1:N──▶ [에이전트 산출] agent_runs ──1:N──▶ legal_findings
                   │                                     └──1:N──▶ documents
                   └────────1:N──▶ [사람의 결정] approvals
```

법령은 `law_index`(원문, 개정 시 재적재) 와 `legal_findings`(건별 적용 스냅샷) 로 분리한다. 법이 바뀌어도 과거 승인 시점의 판단 근거(`quote`)는 그대로 남는다 — 기획서 13장 Q&A "법령이 바뀌면?" 의 답을 스키마로 구현한 것.

---

## 3. 정규화 근거 (3NF)

| 원칙 | 적용 |
|---|---|
| **1NF** 반복 그룹 제거 | 설비-부품 장착 목록을 `equipments` 컬럼에 나열하지 않고 `equipment_parts` 행으로 분리. 호환 부품 목록도 `part_compatibility` 행으로. |
| **2NF** 부분 함수 종속 제거 | 복합 PK 테이블(`equipment_parts`, `part_compatibility`, `ai_configs`) 의 비키 컬럼은 모두 PK 전체에 종속 (`installed_at` 은 설비+부품 조합에, `provider` 는 테넌트+에이전트 조합에). |
| **3NF** 이행 종속 제거 | `work_requests` 에 설비명·부품명을 두지 않고 FK 만 보관 (설비명은 `equipment_id` 를 통해 결정). 승인자 이름·역할은 `users` 에서만. 법령 본문은 `law_index` 에서만. |
| 의도적 비정규화 (스냅샷) | `legal_findings.law/article/title/quote` 는 `law_index` 와 중복되지만 **시점 보존**이 목적이라 별도 컬럼으로 복사. `law_index_id` 는 nullable 참조로 원문 추적만 담당 (`ON DELETE SET NULL`). |

---

## 4. JSON 컬럼을 쓴 이유와 승격 컬럼

| JSON 컬럼 | 쓴 이유 | 구조 | 승격(별도 컬럼/테이블)한 것 |
|---|---|---|---|
| `agent_runs.steps_json` | API `AgentRun.steps` 를 **가공 없이** 저장·반환 (폴링 응답 원본). 에이전트 4개 결과 스키마가 서로 다르고, Mock→실제 LLM 전환 시 result 형태가 바뀔 수 있어 고정 컬럼으로 두면 마이그레이션이 잦아짐 | `[{agent, status, started_at, completed_at, result}]` | 조회·집계가 필요한 부분만 승격: `overall_status`, `summary`, `approval_required_by`, `completed_at`(컬럼) · 법령 판단 → `legal_findings`(테이블) · 서류 → `documents`(테이블) |
| `equipments.substances` | 설비 1대가 취급하는 물질이 0~N개. 조회는 "이 설비의 물질 목록" 단위라 배열이 자연스러움. 법령 매칭은 애플리케이션이 배열을 풀어 `law_index.substance` 와 대조 | `["SiH4","NH3"]` | 없음 (물질 마스터가 생기면 `equipment_substances` 로 승격 예정) |
| `parts.spec` | 밸브·조정기·필터마다 규격 항목이 다름(재질/시트/유량/등급…). 부품군마다 테이블을 나누면 과설계 | `{"material":"SS316","seat":"PCTFE",…}` | `grade`, `toxic_gas_allowed`, `stock` 은 필터·게이트 조건이라 컬럼으로 승격 |
| `documents.missing_json` | 누락 항목이 자유 문자열 0~N개. 비어 있는지(`[]`)만 게이트에서 판단 | `["작업자 2명 이름"]` | 없음 |
| `approvals.checklist_json` | CONTRACT 의 4개 키 고정 객체. 감사 증적으로 **입력 그대로** 보존 | `{"WORK_PERMIT":true,…}` | 컬럼으로 풀지 않고 CHECK 제약으로 게이트 강제 (아래) |
| `audit_logs.before_json/after_json` | 엔터티마다 스키마가 달라 변경 전/후 스냅샷은 JSON 이 유일한 선택 | 임의 객체 | 없음 |

모든 JSON 컬럼은 `jsonb` 이며 `jsonb_typeof` CHECK 로 배열/객체 형태를 강제한다.

### 데이터베이스에서 강제하는 업무 규칙 (CHECK)

| 제약 | 의미 | CONTRACT 매핑 |
|---|---|---|
| `chk_approvals_approve_requires_checklist` | `decision='APPROVE'` 이면 `checklist_json` 4항목이 모두 `true` 여야 저장 가능 (`COALESCE` 로 누락 키는 false 취급) | `POST /approvals` 409 |
| `chk_ai_configs_openai_requires_egress` | `provider='OPENAI'` 이면 `egress_allowed=true` 필수 — 폐쇄망 설정에서 외부 API 지정 자체를 차단 | 온프레미스 제약 |
| `chk_part_compat_not_self` | 자기 자신을 호환품으로 등록 금지 | |
| `chk_agent_runs_review_has_completed` | `overall_status='REVIEW'` 이면 `completed_at` 필수 | 4 step DONE → REVIEW |
| `chk_legal_findings_phase`, `chk_legal_findings_procedure_has_phase` | phase 는 BEFORE/AFTER, 절차가 있으면 phase 필수 | required_procedures |
| `chk_parts_stock_nonneg`, `chk_documents_version_pos`, `chk_work_requests_updated_after_created` 등 | 값 범위 | |

---

## 5. 인덱스 전략

| 인덱스 | 대상 | 근거 (API) |
|---|---|---|
| `idx_work_requests_status` | `work_requests(status)` | `GET /work-requests?status=` 목록 필터, `GET /dashboard/summary` 의 상태별 집계 |
| `idx_work_requests_tenant_created` | `work_requests(tenant_id, created_at DESC)` | 테넌트별 최신순 목록·페이징 |
| `idx_agent_runs_work_request_id` | `agent_runs(work_request_id, created_at DESC)` | `GET /work-requests/{id}` 의 **latest_run** 조회 (최신 1건) |
| `idx_law_index_type_substance` | `law_index(equipment_type, substance)` | `GET /laws/search?equipmentType=&substance=`, A2 LEGAL 매칭. NULL 은 "공통 조문" 이라 `(col IS NULL OR col = ?)` 패턴으로 조회 |
| `uq_law_index_law_article` | `law_index(law, article)` UNIQUE | 재적재 시 upsert 키 |
| `idx_legal_findings_run`, `idx_documents_run_type`, `idx_approvals_work_request_id` | FK 컬럼 | 상세 화면 조인 |
| `idx_audit_logs_entity`, `idx_audit_logs_created_at` | 감사 로그 | 엔터티 이력 조회, 기간 조회 |
| `uq_parts_tenant_part_no` | `parts(tenant_id, part_no)` UNIQUE | 품번 중복 방지, A1 SPEC 의 part_no 조회 |

PoC 데이터 규모에서는 성능보다 **조회 의도를 스키마에 문서화**하는 목적이 크다. 전문 검색(`law_index.text`) 은 확장 단계에서 `GIN(to_tsvector)` 또는 pgvector 로 추가한다.

---

## 6. Supabase 적용 절차

1. Supabase 프로젝트 → 좌측 **SQL Editor** → **New query**
2. `schema_postgres.sql` 전체를 붙여넣고 **Run**
   - 파일 상단의 `DROP TABLE/TYPE IF EXISTS` 블록 덕분에 재실행해도 깨끗하게 다시 만들어진다 (개발용; 운영 전환 시 해당 블록 주석 처리)
   - 성공 시 테이블 14개, ENUM 9개, 트리거 1개 생성
3. 새 쿼리에 `seed_data.sql` 을 붙여넣고 **Run**
   - `BEGIN … COMMIT` 트랜잭션이라 중간 실패 시 아무것도 남지 않는다
   - 성공 시 Table Editor 에서 `work_requests` 5행(상태 5종), `agent_runs` 4행, `law_index` 6행 확인
4. 확인 쿼리
   ```sql
   SELECT wr.id, wr.status, r.id AS run_id, r.overall_status
   FROM work_requests wr LEFT JOIN agent_runs r ON r.work_request_id = wr.id
   ORDER BY wr.id;
   ```
5. FastAPI 연결: Project Settings → Database → **Connection string (URI)** 를 `DATABASE_URL` 로 설정.
   로컬 개발은 SQLite 폴백(CONTRACT) — ENUM 은 문자열 컬럼으로, `jsonb` 는 `JSON` 으로 매핑된다.
6. RLS: PoC 에서는 비활성. 확장 시 `tenant_id = current_setting('app.tenant_id')` 정책으로 테넌트 격리.

---

## 7. 발표용 요약

ReplaceFlow 의 데이터 모델은 14개 테이블을 **마스터(설비·부품·호환표) / 트랜잭션(요청→에이전트 산출→사람의 결정) / AI(법령 인덱스) / 설정(에이전트 모델·egress, 감사로그)** 네 묶음으로 나눈다. 핵심은 3층 분리다. `work_requests` 는 현장의 사실만 담고, 에이전트 4개가 만든 결과는 `agent_runs.steps_json` 에 원본 그대로 두되 조회가 필요한 법령 판단과 서류는 `legal_findings`·`documents` 로 승격했으며, 승인·반려는 사람이 `approvals` 에 남긴다. 법령은 사전 적재한 `law_index` 와 건별 스냅샷 `legal_findings` 를 분리해 법이 개정돼도 과거 승인 근거가 보존되고, 승인 게이트(체크리스트 4항목 모두 true)와 폐쇄망 제약(OPENAI 는 egress 허용 필수)은 API 뿐 아니라 DB CHECK 제약으로도 강제된다. 온프레미스 요구는 `ai_configs.provider/egress_allowed` 라는 데이터로 표현되어, 에이전트를 Mock 에서 사내 LLM·A.X 플랫폼으로 바꿀 때 스키마 변경 없이 설정 행만 바꾸면 된다.

---

## 8. 검증 결과 (2026-09-02)

| 검증 | 결과 |
|---|---|
| `sqlglot` (dialect=postgres) 파싱 | `schema_postgres.sql` 76문, `seed_data.sql` 17문 파싱 성공 (plpgsql 함수 본문은 Command 폴백 — 정상) |
| `pglast` (libpg_query, 실제 PostgreSQL 파서) | 두 파일 모두 문법 오류 없음 |
| PostgreSQL 16 실제 실행 (`psql -v ON_ERROR_STOP=1`) | schema → seed 성공, 재실행(idempotent) 성공, 14개 테이블 행수 = 샘플 규모와 일치 |
| 제약 동작 테스트 | 체크리스트 미완료 APPROVE → CHECK 위반(409 게이트), OPENAI + egress=false → CHECK 위반, 자기 호환 → CHECK 위반, `updated_at` 트리거 동작 확인 |
| `@dbml/cli dbml2sql --postgres` | DBML 파싱 성공: 테이블 14, ENUM 9, FK 20, 인덱스 10 생성 |

주의: 샘플 `WR-20260902-011` 은 CONTRACT 의 요청 시점 JSON(`REQUESTED`) 이후 실행(RUN-0042)·승인(AP-0007)까지 진행된 상태이므로 seed 에서는 `APPROVED` 로 적재했다. `law_index.text` 는 조문 **요약**이며(`[요약]` 표기) 원문은 `source_uri` 의 법제처 링크를 따른다.
