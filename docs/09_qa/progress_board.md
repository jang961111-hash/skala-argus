# Argus 진척 보드 (Day 2 스탠드업 — D2-13)

작성: PM·DBA 은태현 · 기준시각 **2026-09-03 (Day 2)** · 발표 **2026-09-04 15:00**
판정 기준: 팀 노션 계획표 30개 태스크(D1-1~D3-7)를 **레포 실물 파일과 대조**했다.
문서에 "했다"고 적힌 문장은 근거로 인정하지 않았다. 근거는 전부 파일 경로(가능하면 줄번호)다.

**요약: 완료 18 · 부분 10 · 미착수 2** (D2-12 아키텍처 v2, D3-7 발표가 미착수)

> # 기준: **CONTRACT v3.0 최종 확정** (2026-09-03)
> 팀 노션 「API 명세서 v1.0」+「FixGuide 데이터 모델 정의서 v3.0」+「WRA 화면정의서 v2.0」 원문 이관본(255줄).
> v2.0(오케스트레이터 추론본)은 **폐기** → `CONTRACT_v2.0_superseded.md`.
>
> **확정 사실**: 테이블 **8개** · 1:N **8개** · **N:M 0개** · API **15개**(12 paths/15 ops) · Postman **16요청/67예시**
> · 에러코드 **23종** · 화면 **9종**(`views/` vue 10) · 에이전트 **3종**(A4 Phase 2). BE `services/` 구현 중.
>
> ⛔ **무효**: `pytest 8/8` · `e2e_live.sh 35/35` 는 **v1.0 기준이라 근거로 쓸 수 없다.**
> ⛔ **내 정규화 지적 3건은 소멸** — 대상 테이블(`part_compatibility`·`legal_findings`·`tenants`)이 v3.0 범위에서 빠졌다.
> **"고쳤다"가 아니라 "범위 축소로 사라졌다"가 사실이다**(`erd.md:21`). Phase 2 에서 테이블이 부활하면 지적도 부활한다.
>
> **⚠️ 아래 Epic 1·2 판정은 v1.0 스냅샷이다.** v3.0 재판정은 §6.

---

## 1. Epic 1 — Day 1 (기획 & Architecture)

| ID | 업무 | 담당 | 판정 | 근거 (레포 실물) |
|---|---|---|---|---|
| D1-1 | 페르소나 + 문제 정의 | UX(B) | **부분** | 문제 정의는 강함: `docs/01_planning/planning_final.md:35-51` As-Is 6단계 표(③④⑤ 일주일 / ⑥ 2시간). 페르소나는 `planning_final.md:32` **한 줄**("설비 엔지니어 + 안전관리자")뿐 — 노션이 요구한 **페르소나 시트 산출물 없음**. `docs/08_presentation/pitch_outline_and_script.md:14`에 슬라이드4 항목으로만 예약됨 |
| D1-2 | Actor 도출 · Use-Case 정의 | UX(B) | **완료** | `docs/02_usecase/usecase_spec.md:8` Actor 정의표, `:24-247` UC-01~07 7건 정식 명세(전제·흐름·결과상태). 다이어그램 `usecase_diagram.svg`(343KB), `user_flow.svg`(134KB) + `.mmd` 원본 |
| D1-3 | AI 확장 지점 식별·표시 | API(D) | **완료** | `usecase_spec.md:248-291` §3.1 원칙 / §3.2 확장 지점 / §3.3 **사람이 유지하는 곳** / §3.4 상태전이별 책임주체. 문서만이 아니라 코드로 실재: `backend/app/services/agents/base.py`, `mock_agents.py`, `llm_agents.py` |
| D1-4 | UI/UX 화면 흐름도 (**Figma**) | UX(B) | **부분** | 대체물은 실재: `docs/03_wireframe/wireframe.html` **51,760 bytes** 동작 목업 + `wireframe_spec.md` 117줄(`:1` 제목이 "Figma **재작업용**", `:77` §5 "Figma 페이지 구조 **제안**"). 레포 전수 grep 결과 **Figma 파일·URL 0건**. `docs/00_INDEX.md:47`이 스스로 "Figma 실제 제작"을 미완 수동항목으로 적어둠 |
| D1-5 | 시스템 아키텍처 초안 | PM(A)+API(D) | **완료** | `docs/04_architecture/architecture.md` 156줄 + SVG 3종(`architecture.svg` 82KB, `state_machine.svg` 87KB, `sequence_agent_run.svg` 64KB) + `.mmd` 원본 3종 |
| D1-6 | FE 프로젝트 생성 (Vue+Vite) | FE(E) | **완료** | `frontend/src/` 12파일, `main.js`·`router/index.js`·`vite.config.js`(프록시 `/api`→8000) |
| D1-7 | **BE 프로젝트 생성 (Spring Boot)** | BE(F) | **완료 (스택 대체)** | `backend/app/` 5계층 실재(`main.py`·`api/v1/routers/`·`services/`·`repositories/`·`models/`). **Spring Boot 아님 — FastAPI**. 판정은 아래 §2 |
| D1-8 | DB 인스턴스 생성 (Supabase/Neon) | DA(C) | **부분** | DDL·적용절차는 완비: `docs/06_erd/schema_postgres.sql` 285줄, `erd.md` §6 Supabase 적용 6단계. 그러나 **실제 구동 DB는 SQLite**: `backend/app/core/config.py:31` `database_url = "sqlite:///./argus.db"`, `backend/.env.example:3` 동일. 호스팅 인스턴스 접속 근거 레포에 없음 |
| D1-9 | AI 프롬프트 초안 + JSON 사전 검증 | API(D) | **완료** | `docs/05_ai_ready/prompts.md` 337줄 — §0 공통 가드레일, A1~A4 각각 System/User/입력샘플/기대출력, §6 Playground 검증 절차, §7 버전 관리. JSON Schema 6종(`schemas/agent_run.schema.json` 834줄 포함) |
| D1-10 | Day1 정리 스탠드업 | PM(A) | **부분** | `docs/00_INDEX.md:6-20`이 1일차 산출물 8행을 ☑ 표로 정리해 사실상 체크리스트 역할. 다만 **스탠드업 기록 문서 자체는 없음** |

## 2. Epic 2 — Day 2 (설계 & Scaffolding)

| ID | 업무 | 담당 | 판정 | 근거 (레포 실물) |
|---|---|---|---|---|
| D2-1 | ERD 데이터 모델링 | DA(C) | **완료** | `docs/06_erd/argus.dbml` 402줄 = Table 14개, `erd.md` 189줄(§2 관계, §3 정규화, §4 JSON 사유, §5 인덱스). 1:N·N:M 실물 검증은 아래 §3 |
| D2-2 | DB 스키마 생성 (DDL 적용) | DA(C)+BE(F) | **부분** | DDL·시드 작성 완료(`schema_postgres.sql` 285줄, `seed_data.sql` 270줄), ORM 14 테이블 실재(`backend/app/models/*.py`의 `__tablename__` 14개 = ERD 14개와 1:1). 실행 테이블은 `main.py`의 `Base.metadata.create_all` → **SQLite**. `erd.md` §8의 "PostgreSQL 16 실제 실행"은 **문서 주장이라 근거로 채택하지 않음**, 팀 공용 PostgreSQL 인스턴스는 미생성 |
| D2-3 | REST API 명세 (Method/Path/Status) | API(D) | **완료** | `docs/07_api/openapi.yaml` **1,731줄**, `api_spec.md` 119줄, `redocly.yaml` |
| D2-4 | Mock API Endpoint 설계 | API(D) | **완료** | `postman/Argus.postman_collection.json` — 요청 **21개**(고유 엔드포인트 15개 + "데모 시나리오(90초)" 6스텝이 그중 6개를 재사용), **예시 응답 78개**(폴링 `GET /agent-runs/{runId}` 는 7개 = 5단계 시뮬), `Argus.postman_environment.json`. ⚠ `docs/00_INDEX.md:16` 의 "52 예시 응답"은 **데모 폴더를 뺀 수**라 총계로는 틀렸다 — 정구현 실측(`postman_verification.md` §0)이 맞다 |
| D2-5 | BE Entity·Repository 구성 | BE(F) | **완료** | `backend/app/models/` 5파일에 `__tablename__` **14개** — tenants·users·ai_configs·audit_logs·equipments·parts·equipment_parts·part_compatibility·work_requests·approvals·agent_runs·legal_findings·documents·law_index. `repositories/` 5파일(`work_request_repo`·`agent_run_repo`·`approval_repo`·`master_repo`·`ids`) |
| D2-6 | BE Service·Controller (핵심 1~2개) | BE(F) | **완료 (초과 달성)** | `api/v1/routers/` 7파일 **16 라우트** = CONTRACT 15개 전부 + `PATCH /{id}/complete`(`work_requests.py:85`). 노션은 "핵심 API 1~2개"만 요구. `services/` 4종(`orchestrator`·`work_request_service`·`approval_service`·`dashboard_service`) |
| D2-7 | FE 공통 레이아웃·라우팅 | FE(E) | **완료** | `frontend/src/router/index.js` 3라우트(`/`, `/work-requests/:id`, catch-all), `App.vue` 85줄, `assets/main.css` |
| D2-8 | FE 핵심 화면 1~2개 | FE(E) | **완료** | `views/WorkRequestListView.vue` 243줄, `views/WorkRequestDetailView.vue` 119줄 + 컴포넌트 3종(`AgentTimeline.vue` 251줄, `ApprovalPanel.vue` 220줄, `StatusChip.vue` 48줄) |
| D2-9 | FE ↔ BE 실제 API 연동 | FE(E)+BE(F) | **완료** | `frontend/src/api/client.js:33-46` httpApi 12메서드(axios), `vite.config.js` 프록시. 팀장 실측: 프록시 200 · 브라우저 렌더 · **콘솔 에러 0건** · `npm run build` 182KB |
| D2-10 | FE ↔ Mock API 연동 | FE(E)+API(D) | **완료** | `client.js:14` `USE_MOCK` 토글, `client.js:50~` 동일 계약 인메모리 Mock(CONTRACT 폴링 동작 시뮬), `mock/data.js` 165줄(CONTRACT 샘플과 동일 ID) |
| D2-11 | E2E 데이터 흐름 검증 | DevOps | **완료** | `scripts/e2e_live.sh` — 실 uvicorn 기동 후 HTTP status 실측, **35/35 통과**(상태머신·409·422·404·설정격리). `backend/tests/test_flow.py` **8 test 8/8**. `docs/09_qa/e2e_test_checklist.md` 123줄(정상 22·오류 14·비기능 10) |
| D2-12 | 아키텍처 다이어그램 **확정본(v2)** | PM(A) | **미착수** | `docs/04_architecture/architecture.md:3` 이 여전히 `문서 버전: v1.0 (2026-09-02)`. v2 갱신 흔적 없음 — **내(PM) 몫, 오늘 처리** |
| D2-13 | Day2 정리 스탠드업 | PM(A) | **진행 중** | **이 문서(`docs/09_qa/progress_board.md`)가 산출물** |

## 3. Epic 3 — Day 3 (검증 & 발표)

| ID | 업무 | 담당 | 판정 | 근거 (레포 실물) |
|---|---|---|---|---|
| D3-1 | API 테스트 정리 (Postman·Status Code) | API(D)+BE(F) | **완료 (내 스캔 직후 도착)** | `docs/09_qa/postman_verification.md` 91줄 — 실서버 36회 호출로 Postman 예시와 필드 단위 대조. **상태 코드 21/21·36/36 전부 일치**. 단 **필드 불일치 4건**(`GET /work-requests`, `GET /work-requests/{id}`, `GET /documents/{docId}`, 409·422 에러 포맷)이 새로 드러남 → §4-1 에 후속 과제로 추가 |
| D3-2 | 설계 문서 최종 보완 | 각 담당 | **부분** | 문서 세트는 갖춰짐(`docs/` 41파일). 미결: D2-12 v2, D1-1 페르소나 시트, D1-4 Figma |
| D3-3 | 발표 자료 6개 목차 | PM(A) | **부분** | `docs/08_presentation/pitch_outline_and_script.md` 92줄 — 슬라이드 16장 구성안 + 대본 + 시간 배분. **실제 슬라이드 파일(PPT/PDF) 레포에 없음** — 내 몫 |
| D3-4 | Live Demo 시나리오·리허설 | FE(E)+PM(A) | **부분** | 시나리오 실재: `pitch_outline_and_script.md:69-87` 90초 데모. 리허설 절차: `e2e_test_checklist.md:76-121`(환경·브라우저·데이터리셋·Postman 백업 30초 전환·타이밍). **리허설 실시 기록 없음** |
| D3-5 | 회고 (한계+로드맵+R&R별) | 전원 | **부분** | `docs/09_qa/retrospective_template.md` §1 한계 4항·§2 로드맵 4단계·§5 한줄요약 **작성 완료**. §3 R&R별 5명 **전원 공란**, §4 KPT **공란** |
| D3-6 | Peer Review 질의 1개 | 전원 | **완료** | `docs/09_qa/qa_bank.md:51` §F "우리가 다른 조에 할 질문", `pitch_outline_and_script.md:88` "다른 조에 던질 질문(필수 1개)". 예상 질문 25개도 `qa_bank.md` A~E절에 준비됨 |
| D3-7 | Project Pitch & Live Demo | 전원 | **미착수** | 9/4 15:00 |

---

# §2. D1-7 판정 — Spring Boot → FastAPI

## 규정 판정: **위반 아님. 계획표를 고쳐야 한다.**

강의안 Tool Guide 는 Java/Spring Boot · Python/FastAPI · Node/Express 를 **모두 허용 스택**으로 제시했다.
따라서 이건 규정 위반이 아니라 **팀이 허용 범위 안에서 내린 기술 선택**이다.
문제는 노션 계획표 D1-7 이 아직 "Spring Boot"라고 적혀 있어서, 채점자가 계획표와 레포를 대조하면
**"계획을 못 지킨 팀"으로 오독될 수 있다는 것**뿐이다. 이건 기술 리스크가 아니라 문서 리스크다.

**→ 조치: 노션 D1-7 을 "BE 프로젝트 생성 (FastAPI)"로 고치고, 변경 사유 한 줄을 계획표에 남긴다.**
몰래 고치는 게 아니라 **변경 이력으로 남기는 것**이 핵심이다. 계획표를 조용히 덮어쓰면 "원래 그랬던 척"이 되어
발표 중 질문이 들어왔을 때 방어가 안 된다. 이력이 남아 있으면 아래 설명이 그대로 근거가 된다.

## 발표에서 이 변경을 감점이 아니라 가점으로 만드는 설명 (한 문단)

> "1일차 계획에는 Spring Boot 로 적었는데 FastAPI 로 바꿨습니다. 이유는 이 서비스의 본질이 CRUD 가 아니라
> **에이전트 4개의 비동기 오케스트레이션과 JSON 계약**이기 때문입니다. 저희 설계에서 가장 중요한 산출물은
> `AgentRun` JSON 인데, FastAPI 는 Pydantic 스키마가 곧 OpenAPI 명세이자 런타임 검증이라 **계약이 코드와
> 갈라질 수가 없습니다.** 그래서 CONTRACT.md 한 장으로 BE·FE·Postman·JSON Schema 네 산출물의 필드명을
> 문자 단위로 맞출 수 있었고, 실제로 `GET /agent-runs/{runId}` 응답과 명세가 일치하는지 자동 검증까지 넣었습니다.
> 또 하나는 확장 방향입니다. 이 서비스의 다음 단계는 사내 LLM·RAG 연동인데 그 생태계가 Python 이라,
> Mock 에이전트를 실제 LLM 으로 바꿀 때 `llm_agents.py` 구현체만 갈아끼우면 됩니다 — 라우터·스키마·FE 는 그대로입니다.
> 즉 스택을 바꾼 게 아니라, **AI-Ready 라는 이번 과제의 요구에 맞춰 스택을 고른 것**입니다.
> Tool Guide 가 제시한 세 스택 중 하나이므로 범위 안의 선택이었고, 판단 근거와 시점을 계획표에 남겼습니다."

핵심은 "바꿨습니다, 죄송합니다"가 아니라 **"과제 요구(AI-Ready)에서 역산해 골랐습니다"** 로 프레이밍하는 것이다.
근거로 들 실물: `backend/app/services/agents/base.py`(인터페이스) ↔ `mock_agents.py` ↔ `llm_agents.py`(교체 지점).

---

# §3. DBA 검증 — `docs/06_erd/` 실물 대조

DDL(`schema_postgres.sql`) 을 직접 열어 확인했다. 테이블 14개, FK 20개, 복합 PK 3개 실재.

## 3-1. 1:N 관계 — 실재하는 테이블명

| 부모 | 자식 | FK 컬럼 | DDL 위치 |
|---|---|---|---|
| `tenants` | `users` | `users.tenant_id` | `schema_postgres.sql:63` |
| `equipments` | `work_requests` | `work_requests.equipment_id` | `:152` |
| `work_requests` | `agent_runs` | `agent_runs.work_request_id` | `:167` |
| `work_requests` | `approvals` | `approvals.work_request_id` | `:216` |
| `agent_runs` | `legal_findings` | `legal_findings.agent_run_id` | `:184` |
| `agent_runs` | `documents` | `documents.agent_run_id` | `:202` |
| ~~`law_index` → `legal_findings`~~ | — | **삭제됨** (아래 주의) | — |

대표 축은 **`work_requests` → `agent_runs` → `documents`** 다 (요청 1건 → 재실행 N회 → 서류 N건). 총 FK **19개**.

> ⚠️ **재검증 중 변경 감지 (9/3 저녁).** 팀원이 `docs/06_erd/` 3파일을 수정하면서 **`legal_findings.law_index_id` 컬럼을 삭제**했다.
> FK 가 20 → 19 로 줄었고, `law_index` → `legal_findings` **1:N 관계가 사라졌다.**
> 이건 `erd.md` §2·§3 이 "원문 추적을 `law_index_id` 가 담당한다"고 써 둔 설계 의도와 정면으로 어긋난다 —
> 스냅샷(`legal_findings`)에서 원문(`law_index`)으로 되돌아갈 길이 없어져, **아래 (2)번 중복이 추적 불가능한 순수 중복이 됐다.**
> 의도한 변경인지 확인이 필요하다. 의도였다면 `erd.md` 의 해당 서술도 같이 고쳐야 한다.

## 3-2. N:M 관계 — 실재하는 연결 테이블명

| 관계 | 연결 테이블 | 복합 PK | DDL 위치 |
|---|---|---|---|
| `equipments` ↔ `parts` (설비 BOM) | **`equipment_parts`** | `PRIMARY KEY (equipment_id, part_id)` | `:101-108` |
| `parts` ↔ `parts` (부품 호환표, 자기참조) | **`part_compatibility`** | `PRIMARY KEY (part_id, alt_part_id)` + `CHECK (part_id <> alt_part_id)` | `:112-118` |

둘 다 실재하고 복합 PK 로 정상 구현돼 있다. 자기참조 N:M 이 있는 건 발표에서 강조할 만하다.

## 3-3. 정규화 위반 — **"없음"이 아니다. 3건 지목한다.**

`erd.md` §3 은 3NF 를 만족한다고 단언하지만, DDL 과 시드를 대조하니 실제로는 아래 3건이 걸린다.
발표 전날에 스키마를 고치는 건 리스크가 크므로, **고치지 말고 "알고 있고 이유가 있다"로 방어**하는 걸 권한다(§4 참조).

### (1) `part_compatibility.allowed_for_toxic_gas` — 2NF 부분함수종속 + **안전 게이트 이중 저장** (가장 위험)

- 컬럼 위치: `schema_postgres.sql:116`. 같은 의미의 컬럼이 `parts.toxic_gas_allowed`(`:92`)에 **이미 있다.**
- 시드 대조: `seed_data.sql:41` 의 `P-VLV-002` → `parts.toxic_gas_allowed = FALSE`,
  `seed_data.sql:62` 의 `(P-VLV-001, P-VLV-002)` → `part_compatibility.allowed_for_toxic_gas = FALSE`. **같은 값이 두 곳에 복제됨.** (9/3 저녁 재확인)
- 판정: 이 값이 "대체 부품 **자체**의 유독가스 적합성"이라면 복합 PK `(part_id, alt_part_id)` 의
  **진부분집합 `alt_part_id` 에만 종속** → **2NF 위반**. `erd.md` §3 이 "복합 PK 테이블의 비키 컬럼은 모두 PK 전체에 종속"이라고
  쓴 문장은 이 컬럼에서 성립하지 않는다.
- **왜 이게 제일 위험한가**: 이 값이 장식이 아니라 **안전 판정을 실제로 구동한다**.
  `backend/app/services/orchestrator.py:154` 가 `allowed_for_toxic_gas` 로 유독가스 차단 여부를 결정하고,
  그 값은 `mock_agents.py:32` 가 `part_compatibility` 에서 읽어 넣는다. 두 컬럼을 동기화하는 제약·트리거가 **DDL 에 없다.**
  누가 `parts.toxic_gas_allowed` 만 고치면 안전 게이트는 낡은 값으로 계속 돈다.
- 정석 해법: 컬럼을 없애고 `parts.toxic_gas_allowed` 를 단일 진실 원천으로 읽는다.
  쌍 단위 판단이 정말 필요하다면 컬럼명을 `pair_override_allowed` 처럼 바꿔 **의미가 다르다는 걸 이름으로 못 박아야** 한다.

### (2) `legal_findings` — 조문과 절차를 한 행에 섞어 조문 스냅샷이 중복 (3NF)

- 시드 대조: `seed_data.sql:180-181` 두 행이 **같은 조문**(산안규칙 제92조)인데
  `law`·`article`·`title`·`quote` 4컬럼이 **글자 단위로 동일하게 반복**된다. 절차가 2개(작업허가서, LOTO·가스차단)라서 행이 갈라진 것.
- 판정: 표면상 PK 가 `id SERIAL`(대리키)이라 교과서적 판정은 피해 가지만, 자연키를
  `(agent_run_id, law, article, procedure_name)` 으로 보면 `(law, article) → title/quote` 가
  **비키 속성 경유 이행종속** → **3NF 위반**. 갱신 이상은 실재한다: 제92조 `quote` 를 고치려면 N행을 동시에 고쳐야 한다.
- 정석 해법: `legal_findings`(조문 스냅샷) **1:N** `required_procedures`(절차) 로 분해.
- 참고: 조문 본문을 `law_index` 에서 복사한 것 자체는 **의도적 스냅샷**이고 `erd.md` §3 에 사유가 적혀 있어 정당하다.
  문제는 스냅샷이 아니라 **한 테이블에 두 종류의 사실(조문/절차)을 섞은 것**이다.

### (3) `work_requests.tenant_id` — 이행종속 + **교차 테넌트 무결성 구멍**

- `work_requests.tenant_id`(`:151`) 는 `work_requests.equipment_id` → `equipments.tenant_id`(`:74`) 로 **유도 가능**하다 → 이행종속.
- 테넌트 파티션 키로서의 **의도적 비정규화**로 볼 여지는 있다. 다만 `erd.md` §3 에 이 건은 언급이 없어서, 지금은 "의도"가 아니라 "누락"으로 보인다.
- 진짜 문제는 정규화가 아니라 무결성이다: FK 가 전부 단일 컬럼이라
  `FOREIGN KEY (tenant_id, equipment_id) REFERENCES equipments(tenant_id, id)` 같은 **복합 FK 가 없다.**
  → A 테넌트 설비 + B 테넌트 부품 + C 테넌트 요청인 행이 **DB 제약을 하나도 어기지 않고 저장된다.**
  멀티테넌시를 내세우는 설계에서 이건 뼈아픈 구멍이다. `parts.tenant_id`(`:87`) 도 같은 상황. (복합 FK 개수 실측 = **0건**)

**총평**: 관계 설계(1:N 7종, N:M 2종, 자기참조 포함)와 CHECK 제약 활용은 이 수준의 프로젝트에서 훌륭하다.
다만 "3NF 완전 준수"라는 `erd.md` §3 의 단언은 과하다. **(1)번은 안전 기능이 걸려 있어 발표 Q&A 에서 가장 아플 지점**이니 미리 준비한다.

---

# §4. 발표(9/4 15:00)까지 남은 일 — v3.0 기준

역산: **코드 프리즈 14:00** · 리허설 13:00/14:00/14:40 · 발표 15:00.

## 4-0. 오늘 밤 결정해야 끝나는 것 (미루면 내일 못 함)

| 결정 | 담당 | 왜 오늘인가 |
|---|---|---|
| **명칭 통일** — FixGuide / Argus / 부품 교체 요청·승인 시스템 | 팀장 | **발표 표지에 들어간다.** 슬라이드 제작 전에 확정돼야 함 |
| **Figma vs Stitch** 도구 선택 | 팀장 | 제작 착수 시점이 밀린다. 가이드(`figma_build_guide.md` 319줄)는 이미 있음 |
| **N:M 0개 대응 서사** 확정 | 은태현 | 발표에서 먼저 꺼낼지 방어할지 — 대본이 갈린다 |
| **커밋·PR 방침** 최종 확인 | 팀장 | 통합 커밋 + 본문에 역할·이름 명시로 정해졌으나 `develop`·`feature/*`·PR 은 미생성 |

## 4-1. 구현 (BE·FE 트랙)

| 담당 | 항목 | 소요 | 마감 |
|---|---|---|---|
| BE | `services/` 5종 완성 (auth·photo·agent·approval·dashboard) | 150분 | 9/4 09:00 |
| BE | **단일 에러 포맷** `{code,message,fieldErrors}` 예외 핸들러 (FastAPI 기본 `detail` 아님) + 23종 매핑 | 60분 | 9/4 09:30 |
| BE | JWT Bearer + 권한 가드 (403 `FORBIDDEN_ROLE`/`FORBIDDEN_NOT_OWNER`) | 60분 | 9/4 09:30 |
| BE | 사진 업로드 — `files` 배열·10MB·5장·EXIF 제거·320px 썸네일 (400/409/**413**) | 75분 | 9/4 10:30 |
| BE | `PATCH /agent-results` **전체 치환**(itemId 없으면 신규, 빠지면 삭제) | 45분 | 9/4 10:00 |
| BE | `submit-approval` 4가지 검증 → 422 · 재제출 시 이력 보존 | 40분 | 9/4 10:30 |
| BE | pytest **v3.0 재작성** (기존 8/8 폐기) | 60분 | 9/4 11:30 |
| FE | 9화면 ↔ API 연동 (`CONTRACT.md` §7 매트릭스대로) | 180분 | 9/4 11:00 |
| FE | JWT 인터셉터 + `redirectPath` 역할 분기 (서버가 내려준 값 그대로 사용) | 45분 | 9/4 10:00 |
| FE | E_03 폴링 `pollIntervalMs:2500` · `allDone` 시 중단 | 40분 | 9/4 10:30 |
| FE | E_04 결과 편집(항목 추가/삭제) + `engineerNote` | 60분 | 9/4 11:00 |
| DevOps | `scripts/e2e_live_v3.sh` 작성 + CI 갱신 | 75분 | 9/4 12:00 |
| API | Swagger UI 전 엔드포인트 실호출 검증 | 30분 | 9/4 12:00 |

## 4-2. 문서·발표 (PM 은태현)

| 항목 | 소요 | 마감 |
|---|---|---|
| 아키텍처 v3.0 재작성 (3계층·상태머신 6상태·시퀀스) | 60분 | 9/4 09:00 |
| 발표 슬라이드 실물 제작 (명칭 확정 후 착수) | 120분 | 9/4 12:00 |
| **N:M 0개 방어 슬라이드** — 1:N 8개 + 왜 없는지 + `erd_phase2.mmd` 확장 설계 | 30분 | 9/4 12:00 |
| 루브릭 ⏳ 19건 재판정 | 40분 | 9/4 13:00 |
| 데모 클라이맥스 재설계 (장병헌과) — 폴링 3종 완료 → 결과 편집 → 승인 | 30분 | 9/4 12:00 |
| 전원 회고 §3·§4 취합 | 20분 | 9/4 12:00 |

## 4-3. **사람이 직접 해야만 하는 것** (에이전트 대행 불가)

| 담당 | 항목 | 왜 사람인가 | 소요 | 마감 |
|---|---|---|---|---|
| 문승은 | **Figma 또는 Stitch 제작** — 필수 4화면(E_02·E_03·E_04·S_02) 우선 | 계정·캔버스 조작. **산출물 0건 = 루브릭 ✖** | 60분 | 9/4 10:00 |
| 신서현 | **Supabase 프로젝트 + DDL·seed 실행** | 계정 가입·SQL Editor. 런북은 `supabase_runbook.md` | 45분 | 9/4 11:00 |
| 은태현 | 발표 슬라이드 조판 | 계정·디자인 판단 | (4-2 포함) | 9/4 12:00 |
| 문승은 | 구현 화면 스크린샷 | 브라우저 캡처 | 20분 | 9/4 12:00 |
| 전원 | 브랜치·PR 생성 여부 결정 후 실행 | GitHub 계정 | 30분 | 9/4 13:00 |
| 전원 | 회고 각자 2줄 | 본인 경험 | 각 10분 | 9/3 23:00 |
| 전원 | **리허설 3회 → 발표** | | 각 20분 | 9/4 14:40 |

## 4-4. 절단 순서 (빠듯하다 — 이 순서로 뺀다)

1. **절대 사수**: 인증·상태전이·승인 3종 API · 9화면 연동 · 슬라이드 · 리허설 · 명칭 통일
2. 다음: Figma 필수 4화면 · Supabase 실행 · e2e_live_v3 · pytest 재작성
3. **먼저 버림**: **사진 업로드**(EXIF 제거·썸네일까지 75분인데 **데모 90초에 안 나온다**) → 화면에 자리만 두고 "Phase 2" 표기 · `ManageHistoryView`(처리 이력) · Postman Mock 퍼블리시

> 사진 업로드를 1순위 절단 대상으로 두는 이유는 비용이 가장 큰데 **데모 서사에 등장하지 않기** 때문이다. 잘라도 흐름이 안 무너진다.

# §5. 화면정의서 v2.0 범위 델타 판정 (2026-09-03 10:23 도착)

대상: `/Users/jangbyeongheon/Downloads/WRA_화면정의서_v2.0.html` — **2026-09-03 10:23 작성**.
저장소 산출물(9/2 16:00경)과 제출 PDF 11종(**전부 9/2 16:24**, `find` 로 mtime 실측)보다 **약 18시간 최신**이다.
전문(911줄)을 텍스트로 추출해 **Acceptance Criteria 43개**를 저장소 실제 16개 라우트와 1:1 대조했다.

## 5-1. 팀장 갭 표 검증 — 확인 6 · **수정 1** · **추가 3**

팀장이 뽑은 9개 항목은 **6개 그대로 확인**됐다. 아래는 고칠 것 하나와, 놓친 것 셋이다.

### ✏️ 수정 1건 — "AI 결과 읽기 전용 → 전체 편집"은 절반만 맞다

v2.0 에서도 **안전관리자 화면(S_02)의 AI 결과물은 여전히 읽기 전용**이다(원문 S_02 Description 4번: "AI 결과물(규격·법령·안전서류) **읽기 전용**").
편집권은 **엔지니어 E_04 에만** 신설된다. 정확히는 "읽기 전용 → 전체 편집"이 아니라
**"엔지니어에게만 편집권 신설, 안전관리자는 읽기 전용 유지"** 다. 승인자가 근거를 못 고친다는 원칙은 v1.0·v2.0 공통이고, 이건 발표에서 지켜야 할 원칙이라 구분이 중요하다.

### ⚠️ 추가 갭 (1) — **A4만 빠진 게 아니라 A1도 축소됐다**

v2.0 공통 규칙 원문: "A1의 **부품 마스터·호환표 연동**, A4 벤더는 Phase 2."
즉 A1 이 살아남긴 하지만 **DB 호환표를 안 보고 입력 스펙만으로** 판정하는 형태로 격하된다.
저장소 A1 은 정반대다 — `backend/app/services/agents/mock_agents.py:32` 가 `part_compatibility` 를 실제로 읽는다.
"4종 → 3종"보다 실제 델타가 크다.

### 🚨 추가 갭 (2) — **`parts` FK 소멸 → N:M 관계 2종이 통째로 죽는다** (DBA 판정, 가장 중요)

v2.0 의 E_02 는 부품을 `part_id` **선택**이 아니라 **제품명(자유 입력) + 제품 유형(5종) + 유형별 동적 스펙**으로 받는다.
그러면 `work_requests.part_id` FK(`schema_postgres.sql:149`)가 사라지고, `parts` 마스터를 참조하던
**`equipment_parts`·`part_compatibility` 두 N:M 테이블이 아무데서도 안 쓰인다.**

노션 D2-1 이 명시적으로 요구하는 항목이 "테이블·관계 **1:N/N:M**·정규화"다.
**v2.0 을 전면 채택하면 우리 ERD 의 N:M 근거가 사라진다** — 그것도 자기참조 N:M(`part_compatibility`)이라는, 발표에서 제일 내세울 만한 부분이. 팀장 표에 이 항목이 없었다.

### 🚨 추가 갭 (3) — **평균 승인 소요시간 KPI 제거 = 발표의 숫자 축 제거**

v2.0 은 엔지니어 메인에서 평균 승인 소요시간 KPI 를 뺀다. 그런데 그 숫자가 발표 전체를 떠받치고 있다:
- `pitch_outline_and_script.md:34` 슬라이드 1 부제 "교체는 2시간, **승인은 일주일**"
- `:125` 데모 KPI "평균 승인 소요시간 **26.5h (As-Is 168h → 84% 단축)**"
- `:135` 데모 0:00 첫 대사가 이 숫자를 훑는 장면
- `:49` 슬라이드 16 마무리 "일주일을 하루로"
- 백엔드 실물: `dashboard_service.py:51-52` `avg_approval_hours` / `as_is_baseline_hours`

**이 KPI 를 화면에서 빼면 내일 데모의 첫 30초가 통째로 사라진다.** 팀장 표에는 "KPI 역할별 2세트 분리"로만 적혀 있어 이 파급이 드러나지 않았다.

### 그 외 확인된 소소한 충돌

| 항목 | 저장소 | v2.0 | 비고 |
|---|---|---|---|
| 거절 사유 | `ApprovalCreate.comment: str \| None` (선택, 강제 없음) | **필수** | 강제 로직 신규 |
| 상태 문자열 | `PENDING_APPROVAL` | AC 7-2 가 `status=PENDING` | 문자열 불일치 |
| 재제출 | 상태머신에 역방향 전이 없음 | REJECTED → 수정 → PENDING 복귀 | 상태머신 확장 |
| 사진 | 파일 스토리지 **전무**(멀티파트·정적서빙·용량제한 0) | 업로드·썸네일·원본 열람 | PoC 최고가 신규 기능 |
| 요청 필드 | 6개(`WorkRequestCreate`) | +line, operating_condition, product_name, product_type, spec_json, photos, engineer_note | **7개 신규** |

## 5-2. Acceptance Criteria 43개 대조 — 되는 것 / 안 되는 것

| 구분 | 개수 | 해당 AC |
|---|---|---|
| **FE 화면만 만들면 됨** (API 무관) | 12 | 0-1, 0-4, 1-1, 1-2, 1-3, 2-3, 3-1, 3-2, 3-3, 4-3, 7-5, 8-3 |
| **저장소 API로 지금 그대로 충족** | 10 | 2-4, 4-1, 4-2, 4-4, 5-1, 5-4, 5-5, 6-3, 7-4, 8-1 |
| **파라미터·상태값 보정하면 충족** | 8 | 2-1·7-1·7-3(`role=`), 2-2·6-1·6-2(`mine=`), 3-5(필드 확장), 7-2(`PENDING` 문자열) |
| **신규 개발 필요** | 11 | 0-2·0-3(`POST /auth/login`), 1-4·1-5(`/auth/signup`), 3-4·8-5(사진), 3-6·6-5(DRAFT), 5-2(`PATCH /agent-results/{id}`), 5-3(`PATCH /work-requests/{id}`), 6-4(재제출 전이) |
| **기존 로직 삭제·변경** | 2 | 8-2(체크리스트 409 blocking 제거), 8-4(거절 사유 필수화) |

**요약: 43개 중 22개(FE 12 + 현행 10)는 백엔드 손 안 대고 되고, 8개는 보정, 13개가 진짜 신규다.**
신규 API 6종이 필요하다: `/auth/login`, `/auth/signup`, `POST/GET photos`, `PATCH /agent-results/{id}`, `PATCH /work-requests/{id}`.

## 5-3. 정합성 위험 판정 (PM)

제출 PDF 11종은 **9/2 16:24 로 이미 고정**됐고 전부 v1.0 기준이다(특히 `02_UseCase_명세`·`03_와이어프레임`·`07_REST_API_명세`).

**판정: 가장 위험한 시나리오는 v2.0 전면 채택이 아니라 "부분 반영"이다.**

- 제출본 v1.0 + 코드 v1.0 → **일관됨.** 심사자가 무엇을 대조해도 맞는다.
- 제출본 v1.0 + 코드 v2.0(전면) → 어긋나지만 **어긋나는 방향이 하나**라 "설계를 진화시켰다"고 설명은 된다.
- 제출본 v1.0 + 코드 v1.5(부분) → **최악.** 제출본과도 다르고 v2.0 화면정의서와도 다른 제3의 상태가 되어, 어느 문서를 들이대도 코드가 안 맞는다. 설명할 서사조차 없다.

루브릭 자체 점검표가 이걸 뒷받침한다 — `self_review_rubric.md:4` 는 "근거 산출물은 **레포 안의 파일**이어야 한다(채점자는 레포와 발표만 본다)"고 적었다.
즉 **Downloads 에만 있는 v2.0 화면정의서는 지금 상태로는 채점 대상이 아니다.** 이건 리스크이자 동시에 기회다(§5-5).

## 5-4. 세 선택지의 비용·위험

| 안 | 소요 추정 | 남은 시간 안에 가능? | 가장 큰 리스크 (한 줄) |
|---|---|---|---|
| **(A) v1.0 유지 + v2.0을 회고·로드맵으로** | **1시간** (v2.0 레포 커밋 30분 + 슬라이드 1장 30분) | ✅ 여유 | 오늘 아침 합의한 설계를 구현 못 한 것처럼 보일 수 있다 — 단 "다음 스프린트 설계 완료"로 프레이밍하면 오히려 가점 |
| **(B) 전면 v2.0** | **32시간+** (BE 15h: 인증 3·사진 3·결과편집 2·DRAFT 상태재설계 3·등록필드 2·역할KPI 2 / FE 9화면 12h / 제출본 11종 재생성 3h / ERD 수정 2h) | ❌ **불가능** | 지금 통과하는 E2E 35/35 와 pytest 8/8 이 전부 깨지고, **내일 15:00에 시연할 게 없어진다** |
| **(C) 선별 반영** | **7~10시간** (아래 항목별) | ⚠️ 산술상 가능·실질 위험 | 제출본과도 v2.0과도 다른 **제3의 상태**가 되어 어느 문서로도 코드를 설명할 수 없다 (§5-3) |

### (C) 후보 4개 개별 판정 — 팀장이 고른 4개 중 **2개는 하면 안 된다**

| 후보 | 비용 | 판정 |
|---|---|---|
| A4 벤더 제거 | 2h + 재검증 2h | ❌ **하지 마라.** "축소라 쉽다"가 함정이다. 오케스트레이터·상태머신·Postman 예시 78개·E2E 35케이스·프롬프트 4종·JSON 스키마 6종이 **전부 4단계 전제**로 짜여 있다. 삭제가 아니라 검증된 산출물 전부 재검증이다 |
| 체크리스트 blocking 제거 | 2h + 재검증 2h | ❌ **하지 마라.** v1.0 최대 차별점이다. DB CHECK(`chk_approvals_approve_requires_checklist`)·API 409·E2E 케이스로 **삼중 구현**돼 있고, "AI가 아니라 사람이 게이트를 연다"는 발표 서사의 핵심이다. 지우면 평범한 승인 버튼만 남는다 |
| 역할별 KPI 분리 | 2h | ⚠️ 저비용이나 **평균 승인시간 제거는 반대** — §5-1 추가갭(3) |
| E_02 요청 등록 화면 | FE 3h + BE 2h | ⭕ 유일하게 실익 있음. 지금 저장소엔 **요청 생성 화면이 없어** 데모가 시드·Postman에 의존한다. 화면 하나로 UC-01이 눈에 보인다 |

## 5-5. **추천안 — (A) v1.0 유지. 단 조건 2개를 붙인다.**

**나는 (A)를 고른다.** 근거 넷:

1. **N:M 을 잃는다** — v2.0 의 자유입력 제품 모델은 `parts` FK 를 없애 `equipment_parts`·`part_compatibility` 를 무력화한다. 노션 D2-1 이 대놓고 요구하는 "1:N/N:M"의 N:M 근거가 사라진다. 점수 직결 손실이다.
2. **숫자를 잃는다** — 평균 승인시간 KPI 제거는 26.5h/168h/84% 를 없애고, 그건 슬라이드 1·데모 0:00·슬라이드 16 을 동시에 비운다.
3. **일관성이 최고가치다** — 제출본이 9/2 로 고정된 이상, 코드를 반쯤 옮기는 건 §5-3 의 최악 시나리오다. (B)는 시간상 불가능하므로 (C)는 자동으로 최악으로 수렴한다.
4. **v2.0 은 로드맵 자리에 놓을 때만 자산이다.** 루브릭 D3-5 가 "한계 + AI 결합 로드맵"을 요구한다. "PoC 를 직접 만들어보니 한계가 보였고, **그래서 오늘 아침 팀이 v2.0 화면정의서 9종을 만들었다**"는 건 못 한 변명이 아니라 **설계가 살아 움직인 증거**다. 이미 완성된 문서가 있으니 슬라이드 한 장으로 바로 쓴다.

### 조건 (합쳐서 1시간, 오늘 밤 안)

| 할 일 | 담당 | 소요 | 마감 |
|---|---|---|---|
| `WRA_화면정의서_v2.0.html` 를 **레포로 커밋** (`docs/03_wireframe/screen_definition_v2.0.html`) — Downloads 에만 있으면 채점 대상이 아니다(`self_review_rubric.md:4`) | UX 문승은 | 30분 | 9/3 23:00 |
| 슬라이드 15(회고)에 **"v1.0 → v2.0 설계 진화"** 1장 추가 — 역할 분리·인증·결과 편집·A4 Phase 2 를 다음 스프린트로 제시 | PM 은태현 | 30분 | 9/4 11:00 |

### 발표에서 v2.0 을 꺼내는 말 (Q&A 대비)

> "PoC 를 끝내고 나니 저희 스스로 한계가 보였습니다. 역할이 화면에서 안 갈라지고, AI 결과를 엔지니어가 손볼 수 없고, 벤더 에이전트는 실연동 없이는 의미가 얇았습니다.
> 그래서 **오늘 아침 팀이 화면정의서 v2.0 을 만들었습니다** — 9화면으로 역할을 분리하고, 인증을 넣고, AI 결과를 엔지니어가 편집해 설명을 붙여 제출하는 흐름입니다. A4 벤더는 Phase 2 로 미뤘습니다.
> 오늘 시연하는 건 v1.0 입니다. 남은 하루에 v2.0 을 반쯤 구현하면 **설계 문서와 코드가 어긋나는 게 더 큰 손해**라고 판단했기 때문입니다. 대신 v2.0 설계는 레포에 함께 올렸습니다. 저희가 다음 스프린트에 무엇을 할지는 이미 문서로 결정돼 있습니다."

이게 "못 했다"를 "우선순위를 판단했다"로 바꾼다. **PM 이 범위를 통제했다는 증거**로 읽히는 게 목표다.

---

## 부록. 스캔 시점 주의

이 보드는 내 레포 스캔 시점 기준이다. 스캔 **직후** 팀원 산출물 4건이 추가로 들어왔다:
`docs/09_qa/postman_verification.md`(91줄, D3-1 판정에 반영함), `docs/09_qa/devops_report.md`(116줄),
`docs/03_wireframe/figma_build_guide.md`(239줄), `.github/workflows/ci.yml`.
`figma_build_guide.md` 는 **제작 가이드이지 Figma 산출물이 아니다** — `figma.com` URL 0건이라 D1-4 판정은 **부분 유지**다.
`devops_report.md`·`ci.yml` 은 D2-11 을 보강하지만 D2-11 은 이미 완료였다.


---

# §6. v2.0 전환에 따른 Epic 1·2 재판정

위 Epic 표는 v1.0 기준 스냅샷이다. B 채택으로 **판정이 내려가는 항목**만 추린다.

| ID | v1.0 판정 | v2.0 재판정 | 사유 |
|---|---|---|---|
| D1-3 AI 확장 지점 | 완료 | **🔄 재작업** | 에이전트 4종 → 3종 (VENDOR Phase 2) |
| D1-4 Figma | 부분 | **🔄 확대** | 2화면 → **9화면**. `figma_build_guide.md` 3등급 우선순위 적용 |
| D2-1 ERD | 완료 | **🔄 재작업** | 14 → **16테이블**(`photos`·`agent_results`), FK 20 → 19 |
| D2-2 DB 스키마 | 부분 | **🔄 재작업** | v2.0 DDL 재생성 + Supabase 적용 |
| D2-3 REST API | 완료 | **🔄 확대** | 15 → **22 엔드포인트** |
| D2-4 Postman Mock | 완료 | **🔄 재생성** | 4스텝 → 3스텝, 인증 헤더 |
| D2-5 Entity·Repository | 완료 | **🔄 확대** | 14 → 16 모델 |
| D2-6 Service·Controller | 완료 | **🔄 확대** | 인증·사진·결과편집 신규 |
| D2-7 FE 라우팅 | 완료 | **🔄 재작업** | 3라우트 → **9라우트 + 역할 분기** |
| D2-8 FE 화면 | 완료 | **🔄 확대** | 2화면 → 9화면 |
| D2-11 E2E | 완료 | **🔄 재작성** | 35/35 중 체크리스트 409 케이스 무효 |
| D3-4 Live Demo | 부분 | **🔄 재설계** | 클라이맥스 409 가 폐지된 로직이었음 |

**유지되는 것** (B 에서도 안 건드림): D1-1·D1-2·D1-5·D1-6·D1-9·D2-9·D2-10·D3-6, 그리고 **N:M 2개**(CONTRACT §4 가 명시적으로 보호).

> B 의 최대 리스크는 여전히 §5-3 에서 지적한 **제출본(9/2 16:24 고정) ↔ 코드 불일치**다.
> B 를 완주하면 "설계를 진화시켰다"로 설명 가능하지만, **완주 못 하면 제3의 상태**가 된다.
> 그래서 §4-4 절단 순서를 미리 정해뒀다 — 완주 가능한 범위를 지키는 게 B 성공의 조건이다.


---

# §6. v3.0 확정에 따른 Epic 재판정

| ID | v1.0 판정 | v3.0 재판정 | 사유 |
|---|---|---|---|
| D1-3 AI 확장 지점 | 완료 | ⏳ | 4종 → **A1·A2·A3 3종** (A4 Phase 2) |
| D1-4 Figma | 부분 | **✖** | 2화면 → **9화면**, 산출물 여전히 **0건** |
| D1-7 BE 스캐폴딩 | 완료(스택대체) | ⏳ | `services/` 구현 중 |
| D2-1 ERD | 완료 | **✔ 재작성 완료** | 14 → **8테이블**, 1:N 8개, **N:M 0개**(정직 표기) |
| D2-2 DB 스키마 | 부분 | ◐ | DDL 완료, **Supabase 실행 대기** |
| D2-3 REST API | 완료 | **✔** | **12 paths / 15 ops**, 에러 23종 |
| D2-4 Postman Mock | 완료 | **✔** | **16요청 / 67예시** (구 21/78 무효) |
| D2-5 Entity·Repository | 완료 | ◐ | 모델 **7개** 실재 (`ai_configs` 제안 미구현) |
| D2-6 Service·Controller | 완료 | ⏳ | 인증·사진·결과편집 신규 구현 중 |
| D2-7·D2-8 FE | 완료 | ◐ | **9화면**, `views/` vue 10개 (auth·engineer·safety 분리) |
| D2-11 E2E | 완료 | **⛔ 무효** | 35/35 는 v1.0 기준. `e2e_live_v3.sh` 작성 중 |
| D3-4 Live Demo | 부분 | 🔄 | 클라이맥스 재설계 (체크리스트 409 폐지) |

**§3 DBA 판정의 현재 상태**: 정규화 지적 3건은 **대상 테이블이 v3.0 범위에서 빠져 소멸**했다.
§3 본문은 **v1.0 시점 기록**으로 보존한다 — Phase 2 에서 `part_compatibility`·법령 마스터가 부활하면 그대로 다시 유효해지기 때문이다(`erd.md:148` 이 이미 그 재활용을 설계에 반영했다).

**새 최대 리스크는 N:M 0개다.** 루브릭이 "1:N, N:M"을 명시하는데 범위 내 0개다.
`erd.md:88-109` 가 1:N 8개 표 + 부재 사유 + Phase 2 예비 설계로 대응하고 있으나, **감점 위험을 안고 가는 항목**이라 발표에서 먼저 꺼내는 편이 낫다.
