# ReplaceFlow — 반도체 설비 부품 교체 승인 프로세스 에이전트

> 설비 이상이 확인되면 엔지니어가 작업요청 하나만 올리고, AI 에이전트 4개가 규격·법령·안전서류·벤더 견적을 병렬로 준비하고, 안전관리자는 근거가 붙은 승인 패널에서 결재만 한다 — **일주일 걸리던 교체 승인을 하루로.**

SKALA 4기 Full-Stack Engineering "AI 웹 서비스 설계 Mini-project" · 2026-09-02 ~ 09-04 · 5인조
프레임: 우리는 SK AX AI 도메인팀이며, 유해가스 취급 설비를 가진 반도체 제조사(하이닉스 협력사·후공정)에 B2B AX 솔루션을 제안한다.

---

## 1. 문제와 솔루션

| | 내용 |
|---|---|
| **문제 (As-Is)** | 팹 가스 라인에서 밸브 하나 교체하는 데 실제 작업은 2시간, 그 전에 **규격 확인(1~2일) · 법령 조사(1~2일) · 안전관리자 승인(1~2일)** 이 일주일. 정보(규격·법령·승인)가 벤더·법제처·메신저에 흩어져 있고, 사내 AI는 법령 데이터가 부실하며, 외부 클라우드 AI는 보안상 못 쓴다. |
| **솔루션 (To-Be)** | 온프레미스에서 도는 **에이전트 팀**. 오케스트레이터가 A1 규격·호환 / A2 법령 / A3 안전서류 / A4 벤더 4개 에이전트를 병렬 실행하고, 결과를 **승인 패널**(적용 조문 · 필수 절차 체크리스트 · 서류 초안)로 묶어 안전관리자에게 넘긴다. 승인·발주 확정은 사람 (Human-in-the-loop). |
| **AI 확장 지점** | `AgentOrchestrator` + 4개 `AgentService` 인터페이스. 3일 범위는 Mock(고정 JSON, 호출마다 step 전이) 구현체, 이후 LLM+RAG 구현체로 교체. `ai_configs.provider=LOCAL_LLM`, `egress_allowed=false` 기본. |

## 2. 아키텍처 한 줄

`Vue 3 + Vite (화면 2개)` ⇄ REST JSON ⇄ `FastAPI (WorkRequest API · AgentOrchestrator[Mock/LLM] · ApprovalService 상태머신)` ⇄ `PostgreSQL(Supabase) / 로컬 SQLite` + `law_index(법제처 사전 적재)` — 상세: [docs/04_architecture](docs/04_architecture/)

```
[웹 Vue/Vite] ◀─REST─▶ [FastAPI] ─┬─ AgentOrchestrator ─ SPEC / LEGAL / SAFETY_DOC / VENDOR (Mock → LLM)
                                   ├─ ApprovalService (REQUESTED→RUNNING→REVIEW→PENDING_APPROVAL→APPROVED|REJECTED→DONE)
                                   └─ ai_configs (provider=LOCAL_LLM, egress_allowed=false)
                                            │
                                   [PostgreSQL / SQLite] + [law_index]
```

## 3. 폴더 구조

```
replaceflow/
├── README.md                      ← 이 문서
├── .gitignore / .github/PULL_REQUEST_TEMPLATE.md
├── docs/
│   ├── CONTRACT.md                ← 공통 계약서 (상태값·API·JSON 스키마·샘플 데이터) — 모든 산출물의 기준
│   ├── 01_planning/               ← 기획서, R&R·일정, GitHub 운영 가이드
│   ├── 02_usecase/                ← Actor·Use-Case 7개 (UC-01~07)
│   ├── 03_wireframe/              ← 핵심 화면 2개 와이어프레임 (목록/대시보드, 상세=타임라인+승인 패널)
│   ├── 04_architecture/           ← FE-BE-DB 아키텍처 다이어그램, AI 확장 지점
│   ├── 05_ai_ready/               ← 프롬프트(A2 법령 에이전트), AgentRun JSON 스키마, AI-Ready 4원칙
│   ├── 06_erd/                    ← ERD (dbdiagram DBML, 14개 테이블, 1:N / N:M, 정규화 근거)
│   ├── 07_api/                    ← OpenAPI 3.0 명세, Method/Path/Status 표
│   ├── 08_presentation/           ← 발표 스크립트(15분), 예상 Q&A
│   └── 09_qa/                     ← E2E 연동 테스트 체크리스트, 루브릭 자체 점검표
├── frontend/                      ← Vue 3 + Vite + axios (mock 모드 지원)
│   └── src/ (router, store, views, components, api, mock)
├── backend/                       ← FastAPI (Python 3.11)
│   └── app/ (api/v1/routers, services/agents, repositories, models, schemas, db, core)
└── postman/                       ← Postman Collection + Mock 서버 예시 응답
```

## 4. 빠른 시작

> **사전 요구**: Python **3.10 이상** · Node **18 이상**.
> 모델 정의가 `Mapped[str | None]` (PEP 604) 문법을 쓰므로 Python 3.9 이하에서는
> `MappedAnnotationError` 로 기동이 실패한다. macOS 기본 `python3` 은 3.9 이므로
> `python3.11 -m venv` 처럼 버전을 명시해서 만든다.

### Backend (FastAPI)
```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -V                                              # 3.10 이상인지 확인
pip install -r requirements.txt
cp .env.example .env                                   # 기본값: SQLite, AI_PROVIDER=MOCK, EGRESS_ALLOWED=false
uvicorn app.main:app --reload --port 8000
# Swagger: http://localhost:8000/docs   (샘플 데이터는 기동 시 자동 시드)
```

### Frontend (Vue 3 + Vite)
```bash
cd frontend
npm install
cp .env.example .env
npm run dev              # http://localhost:5173  — vite proxy 가 /api → localhost:8000 으로 전달
npm run dev:mock         # 백엔드 없이 src/mock/data.js 인메모리 Mock 으로 동작 (VITE_USE_MOCK=true)
```

### Postman Mock (백업 경로)
`postman/` 컬렉션을 Import → Mock Server 생성 → `frontend/.env` 의 `VITE_API_BASE` 를 Mock URL 로 교체.

## 5. 데모 시나리오 (90초)

| 초 | 화면 | 행동 | API | 상태 |
|---|---|---|---|---|
| 0~10 | 화면1 목록/대시보드 | KPI(진행 중 5 · 승인 대기 2 · 평균 승인 26.5h vs As-Is 168h) 확인 | `GET /dashboard/summary`, `GET /work-requests` | |
| 10~25 | 작업요청 생성 | EQ-GC-02 가스캐비닛#2 · P-VLV-001 · "가스 유량 이상, 밸브 누설 의심" 입력 | `POST /work-requests` → 201 | `REQUESTED` |
| 25~50 | 화면2 에이전트 타임라인 | "에이전트 실행" 클릭 → 3초 폴링마다 SPEC → LEGAL → SAFETY_DOC → VENDOR 카드가 `PENDING → DONE` | `POST …/agent-runs` → 202, `GET /agent-runs/{runId}` ×4 | `RUNNING` → `REVIEW` |
| 50~60 | 결과 검토 | LEGAL 카드 클릭: 산안규칙 92조 인용 · 필수 절차 4개 / SAFETY_DOC: 작업허가서 누락 "작업자 2명 이름" 보완 → 승인 요청 | `PATCH …/submit-approval` → 200 | `PENDING_APPROVAL` |
| 60~80 | 승인 패널 | 안전관리자(이정호) 로 전환 → 체크리스트 4개 미체크 상태에서 승인 시도 → **409** 안내 → 4개 체크 → 승인 | `POST …/approvals` → 201 | `APPROVED` |
| 80~90 | 화면1 복귀 | 승인 대기 수 감소 · 평균 승인 소요시간 갱신 | `GET /dashboard/summary` | |

## 6. 산출물 ↔ 루브릭 매핑

### 정량 60% — 서비스 기획 & 아키텍처 (30점)
| 루브릭 항목 | 근거 산출물 |
|---|---|
| Use-Case · 와이어프레임 완성도 | `docs/02_usecase/`, `docs/03_wireframe/`, 기획서 `docs/01_planning/` §5·§6 |
| AI 확장 지점 · 프롬프트/JSON 타당성 | `docs/05_ai_ready/` (프롬프트, AgentRun JSON), `docs/CONTRACT.md` §핵심 JSON, `backend/app/services/agents/` |
| GitHub 관리 · R&R 적절성 | `docs/01_planning/rnr_and_schedule.md`, `docs/01_planning/github_guide.md`, `.github/PULL_REQUEST_TEMPLATE.md`, 커밋 이력 |
| FE-BE-DB 다이어그램 명확성 | `docs/04_architecture/` |

### 정량 60% — 시스템 설계 & 스캐폴딩 (30점)
| 루브릭 항목 | 근거 산출물 |
|---|---|
| ERD 1:N / N:M · 정규화 | `docs/06_erd/` (DBML · 14개 테이블 · `equipment_parts`, `part_compatibility` N:M · 3층 분리 정규화) |
| Mock API RESTful 규격 준수 (Method/Path/Status) | `docs/07_api/` (OpenAPI 3.0), `docs/CONTRACT.md` §REST API, `postman/` |
| FE/BE 구조 · DB 연동 | `frontend/src/`, `backend/app/` (routers → services → repositories → models), `backend/.env.example` (`DATABASE_URL`) |
| Mock API 데이터 바인딩 화면 시연 | `frontend/src/views/` (화면1·화면2), `docs/09_qa/e2e_test_checklist.md`, 데모 시나리오 §5 |

### Peer 40%
| 항목 | 근거 |
|---|---|
| 기획 · UX | 문제 정의(현업 As-Is 표) · 핵심 화면 2개 · 90초 데모 |
| 시스템 설계 | ERD · OpenAPI · 상태머신·체크리스트 게이트(409) |
| AI-Ready 확장성 | Interface First · Structured Data · Async Pipeline(202+폴링) · Security & Config Isolation(`ai_configs`) |
| 구현 · Pitch | 살아 움직이는 타임라인 시연, `docs/08_presentation/` |

## 7. 팀 R&R

| 이름 | 역할 | 담당 산출물 | 담당 파일/폴더 |
|---|---|---|---|
| **은태현** | PM · DBA | 일정·R&R, 기획서 확정, 샘플 데이터, ERD·DB 연결, 발표 슬라이드 | `docs/01_planning/`, `docs/06_erd/`, `backend/app/models/`, `backend/app/db/`, `docs/08_presentation/` (슬라이드) |
| **문승은** | Product & UX · FE | Use-Case 7개, 와이어프레임 2장, FE 화면 2개(타임라인·승인 패널), Mock 데이터 바인딩 | `docs/02_usecase/`, `docs/03_wireframe/`, `frontend/src/` |
| **신서현** | DevOps & Infra | GitHub 레포·브랜치·PR 템플릿, 환경 구성(.env·CORS·proxy), FE-BE 연동, E2E 테스트, 데모 운영 | `.github/`, `.gitignore`, `docs/01_planning/github_guide.md`, `docs/09_qa/`, `frontend/vite.config.js`, `backend/.env.example` |
| **정구현** | API Architect · BE | 아키텍처 다이어그램, OpenAPI 3.0, Postman Mock, 요청·run·승인 라우터 | `docs/04_architecture/`, `docs/07_api/`, `postman/`, `backend/app/api/v1/routers/`, `backend/app/schemas/` |
| **장병헌** | BE · 발표 | 에이전트 JSON·프롬프트·상태머신, 오케스트레이터·승인 게이트 구현, 발표·Q&A | `docs/05_ai_ready/`, `backend/app/services/`, `backend/app/services/agents/`, `docs/08_presentation/` (스크립트) |

상세 일정(시간 단위)·리스크는 [docs/01_planning/rnr_and_schedule.md](docs/01_planning/rnr_and_schedule.md), 협업 규칙은 [docs/01_planning/github_guide.md](docs/01_planning/github_guide.md).

## 8. 라이선스 · 주의

- 본 저장소는 SKALA 교육 과정의 Mini-project 산출물이며, 코드는 팀 내부 학습·발표 목적으로 사용한다 (별도 명시 없는 한 MIT).
- **샘플 데이터는 전부 가상**이다. 회사명(○○반도체), 사용자(김민준·이정호·박수진), 설비·부품 번호, 구매 이력은 예시이며 실제 기업·개인과 무관하다.
- **법령 요약·조문 인용(산업안전보건기준에 관한 규칙 91·92·93·319조, 화학물질관리법 24조, 고압가스 안전관리법 시행규칙 별표)은 발표용 예시 발췌**이다. 실제 적용 시 법제처 국가법령정보(https://www.law.go.kr) 원문과 최신 개정 사항을 반드시 확인해야 하며, 에이전트 출력은 안전관리자의 판단을 대체하지 않는다.
- 에이전트 4개는 모두 Mock(고정 JSON) 구현이며, LLM·RAG·ERP·벤더 포털 연동은 확장 범위다 (기획서 §12).
