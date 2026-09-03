# ReplaceFlow — 루브릭 자체 점검표

실행: 3일차 11:00 CP5 (전원) · 진행: PM 은태현 · 기록: 신서현
사용법: "현재 상태" 는 ☐ 미착수 / ◐ 진행 중 / ✔ 완료 로 표시하고, ✔ 가 아니면 "보완 필요 사항" 에 담당자·마감시각을 적는다. 근거 산출물은 **레포 안의 파일**이어야 한다 (채점자는 레포와 발표만 본다).

채점 구조: 정량 60% (서비스 기획 & 아키텍처 30점 + 시스템 설계 & 스캐폴딩 30점) · Peer 40% (기획·UX / 시스템설계 / AI-Ready 확장성 / 구현·Pitch)

---

## 1. 정량 — 서비스 기획 & 아키텍처 (30점)

### 1-1. Use-Case · 와이어프레임 완성도
| 점검 항목 | 근거 산출물 | 현재 상태 | 보완 필요 사항 |
|---|---|---|---|
| Actor 5개(엔지니어·안전관리자·구매·모니터링·에이전트) 정의 | `docs/02_usecase/` | ☐ | |
| UC-01~07 각각 Actor·전제·흐름·결과 상태(`REQUESTED`…`DONE`) 기재 | `docs/02_usecase/` | ☐ | |
| UC 다이어그램 1장 (mermaid 또는 이미지) | `docs/02_usecase/` | ☐ | |
| 화면1 목록/대시보드 와이어프레임: KPI 5개 · 요청 테이블 · 반려 사유 TOP | `docs/03_wireframe/` | ☐ | |
| 화면2 상세 와이어프레임: 요청 정보 · 타임라인 4카드 · 승인 패널(체크리스트·승인/반려/보완) | `docs/03_wireframe/` | ☐ | |
| 와이어프레임 각 요소에 호출 API 표기 (화면 ↔ API 매핑) | `docs/03_wireframe/` | ☐ | |
| 구현 화면이 와이어프레임과 일치 | `frontend/src/views/` 스크린샷 vs 와이어프레임 | ☐ | |

### 1-2. AI 확장 지점 · 프롬프트/JSON 타당성
| 점검 항목 | 근거 산출물 | 현재 상태 | 보완 필요 사항 |
|---|---|---|---|
| AI 확장 지점이 코드 인터페이스로 존재 (`AgentOrchestrator`, `AgentService` 4개, Mock 구현체) | `backend/app/services/agents/`, `docs/05_ai_ready/` | ☐ | |
| Interface First / Structured Data / Async Pipeline / Security & Config Isolation 4원칙이 각각 어디에 구현됐는지 표로 정리 | `docs/05_ai_ready/`, 기획서 §7 | ☐ | |
| 프롬프트(A2 법령 에이전트) System/User 분리, 출력 JSON 강제, 근거 없는 답 `required=UNKNOWN` 규칙 | `docs/05_ai_ready/prompts.md` | ☐ | |
| AgentRun JSON 스키마가 CONTRACT와 동일하고 실제 응답과 필드명 일치 | `docs/CONTRACT.md`, `GET /agent-runs/{runId}` 실응답 | ☐ | |
| `ai_configs.provider` / `egress_allowed` 가 DB·API·.env 세 곳에 모두 존재 | `docs/06_erd/`, `GET /tenants/{id}/ai-config`, `backend/.env.example` | ☐ | |
| `model_name`, `prompt_version` 이 agent_runs 에 저장·응답됨 | `backend/app/models/`, 실응답 | ☐ | |
| Human-in-the-loop (승인은 사람) 이 상태머신·체크리스트 게이트로 구현 | `backend/app/services/` (409) | ☐ | |

### 1-3. GitHub 관리 · R&R 적절성
| 점검 항목 | 근거 산출물 | 현재 상태 | 보완 필요 사항 |
|---|---|---|---|
| README 에 팀 R&R 표(역할·산출물·파일) | `README.md` §7 | ☐ | |
| R&R 상세 + 3일 일정 + 리스크 문서 | `docs/01_planning/rnr_and_schedule.md` | ☐ | |
| 브랜치 전략·커밋 규칙·PR 템플릿·라벨 문서 + 실제 적용 | `docs/01_planning/github_guide.md`, `.github/PULL_REQUEST_TEMPLATE.md` | ☐ | |
| 5명 전원 커밋 존재, 편중 없음 (`git shortlog -sn`) | GitHub Insights → Contributors | ☐ | |
| PR 5건 이상, 리뷰 코멘트 존재 | GitHub Pull requests | ☐ | |
| 이슈에 담당자·라벨(role/rubric) 지정 | GitHub Issues | ☐ | |
| `.gitignore` 로 `.env`·DB 파일 미커밋, `.env.example` 은 커밋 | 레포 트리 | ☐ | |
| Contributors 그래프 캡처 슬라이드 1장 | `docs/08_presentation/` | ☐ | |

### 1-4. FE-BE-DB 다이어그램 명확성
| 점검 항목 | 근거 산출물 | 현재 상태 | 보완 필요 사항 |
|---|---|---|---|
| FE(Vue) ⇄ BE(FastAPI) ⇄ DB(PostgreSQL/SQLite) 3계층 + 외부(모니터링·법령 인덱스) 표시 | `docs/04_architecture/` | ☐ | |
| BE 내부: 라우터 → 서비스(오케스트레이터·승인) → 리포지토리 → 모델 계층이 폴더 구조와 일치 | `docs/04_architecture/`, `backend/app/` | ☐ | |
| AI 확장 지점(Mock → LLM)과 확장 컴포넌트(Queue·GPU LLM·Vector DB·ERP) 점선 표시 | `docs/04_architecture/` | ☐ | |
| 시퀀스 다이어그램: 요청 생성 → 202 → 폴링 → REVIEW → 승인 | `docs/04_architecture/` | ☐ | |
| 온프레미스 경계(egress=false) 표시 | `docs/04_architecture/` | ☐ | |

## 2. 정량 — 시스템 설계 & 스캐폴딩 (30점)

### 2-1. ERD 1:N / N:M · 정규화
| 점검 항목 | 근거 산출물 | 현재 상태 | 보완 필요 사항 |
|---|---|---|---|
| 14개 테이블 전부 DBML 로 작성, 렌더 이미지 첨부 | `docs/06_erd/` | ☐ | |
| 1:N 관계 명시: tenants→users/equipments/parts, equipments→work_requests, work_requests→agent_runs/approvals, agent_runs→legal_findings/documents | `docs/06_erd/` | ☐ | |
| N:M 관계 2개: `equipment_parts` (equipments↔parts), `part_compatibility` (parts↔parts 자기참조) | `docs/06_erd/` | ☐ | |
| 정규화 근거: 요청(사실) / 에이전트 산출 / 사람의 결정 3층 분리, `law_index` ↔ `legal_findings` 분리 이유 | `docs/06_erd/` | ☐ | |
| PK/FK·ENUM(status·role·decision 등) 이 CONTRACT 문자열과 동일 | `docs/06_erd/`, `docs/CONTRACT.md` | ☐ | |
| SQLAlchemy 모델이 ERD 와 일치 (테이블명·컬럼명) | `backend/app/models/` | ☐ | |
| `audit_logs` 존재 및 승인 시 기록 | `backend/app/models/`, E2E NF-09 | ☐ | |

### 2-2. Mock API RESTful 규격 준수 (Method / Path / Status)
| 점검 항목 | 근거 산출물 | 현재 상태 | 보완 필요 사항 |
|---|---|---|---|
| OpenAPI 3.0 파일 존재, 15개 엔드포인트, `/api/v1` prefix | `docs/07_api/openapi.yaml` | ☐ | |
| 리소스 명사·복수형, 동사 없는 경로 (예외: `submit-approval` 은 상태 전이 액션으로 PATCH — 문서에 근거 기재) | `docs/07_api/` | ☐ | |
| 상태코드: 생성 201, 비동기 수락 202, 없음 404, 상태 충돌 409, 검증 422 | `docs/07_api/`, E2E ERR-* | ☐ | |
| 페이지네이션 `?status=&page=&size=` → `{items, total}` | `GET /work-requests` | ☐ | |
| Swagger UI 에서 전 엔드포인트 호출 가능, 응답 예시 CONTRACT 샘플과 동일 | http://localhost:8000/docs | ☐ | |
| Postman Collection + Mock 서버 예시 응답 (데모 순서) | `postman/` | ☐ | |
| Mock 전이 규칙(호출마다 step 1개 DONE) 이 BE·Postman·FE Mock 세 곳에서 동일 | `backend/app/services/agents/`, `postman/`, `frontend/src/mock/` | ☐ | |

### 2-3. FE/BE 구조 · DB 연동
| 점검 항목 | 근거 산출물 | 현재 상태 | 보완 필요 사항 |
|---|---|---|---|
| FE 구조: router / store / views / components / api / mock 분리 | `frontend/src/` | ☐ | |
| FE API 클라이언트가 axios 한 곳(`src/api/`) 에 집중, `VITE_USE_MOCK` 으로 Mock/실 API 스위치 | `frontend/src/api/`, `.env.example` | ☐ | |
| BE 구조: api/v1/routers → services → repositories → models/schemas → db | `backend/app/` | ☐ | |
| DB 연동: `DATABASE_URL` 로 SQLite ↔ PostgreSQL(Supabase) 전환, 기동 시 시드 | `backend/app/db/`, `.env.example` | ☐ | |
| 실제 DB 에 데이터가 쓰이고 읽힘 (생성 → 새로고침 후 유지) | E2E NF-10 | ☐ | |
| README 빠른 시작대로 클린 환경에서 5분 내 기동 | `README.md` §4 (제3자 재현 테스트) | ☐ | |
| pytest 1개 이상 (예: agent-runs 4회 폴링 후 REVIEW, 체크리스트 미완료 409) | `backend/tests/` | ☐ | |

### 2-4. Mock API 데이터 바인딩 화면 시연
| 점검 항목 | 근거 산출물 | 현재 상태 | 보완 필요 사항 |
|---|---|---|---|
| 화면1: KPI·목록이 API 응답으로 렌더 (하드코딩 아님) | `frontend/src/views/`, Network 탭 | ☐ | |
| 화면2: 타임라인 카드가 `steps[].status` 로 PENDING→DONE 전이, 3초 폴링 | `frontend/src/views/`, E2E-08~11 | ☐ | |
| 승인 패널: 체크리스트 4개 미완료 시 버튼 비활성, 409 응답 처리 | E2E ERR-409-04 | ☐ | |
| 오류 케이스 화면 표시 (404 안내, 422 필드 하이라이트, 409 토스트) | E2E ERR-* | ☐ | |
| 90초 데모 시나리오 3회 이상 리허설 통과 | `docs/09_qa/e2e_test_checklist.md` §4 | ☐ | |
| 백업 경로(Postman Mock / dev:mock) 동작 확인 | E2E NF-06, NF-07 | ☐ | |

## 3. Peer 40%

### 3-1. 기획 · UX
| 점검 항목 | 근거 산출물 | 현재 상태 | 보완 필요 사항 |
|---|---|---|---|
| 문제가 현업 경험(As-Is 표: ③④⑤ 일주일 vs ⑥ 2시간) 으로 구체적 | 기획서 §2, 슬라이드 | ☐ | |
| 타깃 고객·페르소나 2명이 명확 (엔지니어·안전관리자) | 기획서 §1 | ☐ | |
| SK AX·하이닉스 근거 출처 표기 | 기획서 §3 | ☐ | |
| 화면이 2개로 압축되어 사용 흐름이 90초 안에 이해됨 | 데모 | ☐ | |
| 승인자 코멘트가 "메신저 왕복" 을 대체한다는 UX 포인트 설명 | 기획서 §6, 화면2 | ☐ | |

### 3-2. 시스템 설계
| 점검 항목 | 근거 산출물 | 현재 상태 | 보완 필요 사항 |
|---|---|---|---|
| 상태머신 다이어그램 (REQUESTED→…→DONE) 슬라이드 1장 | `docs/04_architecture/` 또는 `docs/05_ai_ready/` | ☐ | |
| 202 + 폴링 비동기 설계 이유를 설명할 수 있음 (LLM 지연·Queue 확장) | 발표 스크립트 | ☐ | |
| ERD 3층 분리·법령 스냅샷 설계 이유를 30초 안에 설명 | 발표 스크립트 | ☐ | |
| API 표를 슬라이드에 Method/Path/Status 로 제시 | `docs/08_presentation/` | ☐ | |

### 3-3. AI-Ready 확장성
| 점검 항목 | 근거 산출물 | 현재 상태 | 보완 필요 사항 |
|---|---|---|---|
| "Mock 을 LLM 으로 바꾸려면 어느 파일 하나를 바꾸면 되는지" 즉답 가능 | `backend/app/services/agents/` | ☐ | |
| 온프레미스 제약 → `provider=LOCAL_LLM`, `egress_allowed=false` 설명 | `ai_configs`, `.env.example` | ☐ | |
| 법령 RAG 확장 경로 (law_index 사전 적재 → Vector DB) 설명 | 기획서 §12, 아키텍처 확장 영역 | ☐ | |
| 예상 Q&A 5개 답변 준비 (자동화 범위·외부 클라우드·법 개정·오답·글라스) | 기획서 §13, `docs/08_presentation/` | ☐ | |

### 3-4. 구현 · Pitch
| 점검 항목 | 근거 산출물 | 현재 상태 | 보완 필요 사항 |
|---|---|---|---|
| 발표 15분 이내 (리허설 2회 측정) | E2E 체크리스트 §4.5 | ☐ | |
| 데모가 "살아 움직이는 타임라인 → 409 → 승인" 클라이맥스를 보여줌 | 데모 | ☐ | |
| 발표자·데모 조작자·Q&A 응답자 역할 분담 | `docs/01_planning/rnr_and_schedule.md` 3일차 | ☐ | |
| 슬라이드에 GitHub·Swagger·ERD 캡처 포함 | `docs/08_presentation/` | ☐ | |
| 한계(§12)를 먼저 말하고 확장으로 마무리 | 발표 스크립트 | ☐ | |

---

## 4. 점검 결과 요약 (CP5 에서 기입)

| 영역 | 항목 수 | ✔ | ◐ | ☐ | 보완 담당 · 마감 |
|---|---|---|---|---|---|
| 1-1 Use-Case·와이어프레임 | 7 | | | | |
| 1-2 AI 확장 지점·프롬프트/JSON | 7 | | | | |
| 1-3 GitHub·R&R | 8 | | | | |
| 1-4 FE-BE-DB 다이어그램 | 5 | | | | |
| 2-1 ERD | 7 | | | | |
| 2-2 Mock API RESTful | 7 | | | | |
| 2-3 FE/BE 구조·DB 연동 | 7 | | | | |
| 2-4 데이터 바인딩 시연 | 6 | | | | |
| 3 Peer | 18 | | | | |

미완료 항목은 이슈로 등록(`rubric:*` 라벨)하고 14:00 코드 프리즈 전까지 처리한다. 처리 불가 항목은 발표에서 "한계" 로 먼저 언급한다.
