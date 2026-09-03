# Argus — R&R 상세 · 3일 일정표 · 리스크

작성: PM 은태현 · 2026-09-02 · 기준 문서: `docs/CONTRACT.md`, 기획서 §11
발표: **3일차(09-04) 15:00 · 15분 발표 + 5분 Q&A**

---

## 1. R&R 상세 (가이드 R&R Guide ↔ 우리 팀 매핑)

가이드가 정의한 5개 Role의 Responsibilities와 산출물을 팀원에게 배정한다. DBA는 5인조라 PM이 겸임한다. 모든 산출물은 `docs/CONTRACT.md` 의 상태값·API·JSON 필드명을 그대로 따른다.

| Role (가이드) | 담당 | Responsibilities | 담당 산출물 | 파일 경로 | 완료 기준 (DoD) |
|---|---|---|---|---|---|
| **PM** | 은태현 | 범위 확정(기획서 v3), 일정·체크포인트 운영, 데일리 스탠드업, 산출물 통합 검수, 발표 슬라이드 | 기획서, R&R·일정표, 샘플 데이터, 슬라이드 | `docs/01_planning/`, `docs/08_presentation/`(슬라이드), `docs/CONTRACT.md`(샘플 데이터) | 매 체크포인트에 산출물 상태표 갱신, 3일차 13:00 슬라이드 완성 |
| **Product & UX / FE** | 문승은 | Actor·Use-Case 정의, 핵심 화면 와이어프레임, Vue 화면 구현, Mock/실 API 데이터 바인딩 | UC 7개, 와이어프레임 2장, 화면1(목록/대시보드), 화면2(타임라인+승인 패널) | `docs/02_usecase/`, `docs/03_wireframe/`, `frontend/src/views/`, `frontend/src/components/`, `frontend/src/api/`, `frontend/src/mock/` | `npm run dev:mock` 으로 90초 데모 전 구간 화면 동작, 2일차 오후 실 API 연동 |
| **DevOps & Infra** | 신서현 | GitHub 레포·브랜치·PR 템플릿·라벨, 로컬 환경(.env·CORS·vite proxy), FE-BE 연동, E2E 테스트, 데모 환경·백업(Postman Mock) | GitHub 가이드, .gitignore·PR 템플릿, E2E 체크리스트, 데모 리허설 체크리스트 | `docs/01_planning/github_guide.md`, `.github/`, `.gitignore`, `docs/09_qa/`, `frontend/vite.config.js`, `backend/.env.example` | 1일차 레포 세팅 완료·전원 첫 커밋, 2일차 17:00 FE→BE 실호출 성공, 3일차 E2E 전 항목 통과 |
| **API Architect / BE** | 정구현 | FE-BE-DB 아키텍처 다이어그램, OpenAPI 3.0 명세, Postman Mock 서버, FastAPI 라우터·스키마(Pydantic) | 아키텍처 문서, `openapi.yaml`, Postman Collection, 라우터 | `docs/04_architecture/`, `docs/07_api/`, `postman/`, `backend/app/api/v1/routers/`, `backend/app/schemas/` | Swagger에 CONTRACT의 15개 엔드포인트가 Method/Path/Status 그대로 노출, Postman Mock으로 FE 단독 구동 가능 |
| **BE / 발표** | 장병헌 | AI 확장 지점 설계(오케스트레이터·에이전트 인터페이스), 프롬프트·AgentRun JSON, Mock step 전이·승인 상태머신·체크리스트 게이트(409) 구현, 발표·Q&A | AI-Ready 문서, 프롬프트, 오케스트레이터·승인 서비스, 발표 스크립트 | `docs/05_ai_ready/`, `backend/app/services/`, `backend/app/services/agents/`, `docs/08_presentation/`(스크립트·Q&A) | `GET /agent-runs/{runId}` 4회 호출로 REVIEW 도달, 체크리스트 미완료 APPROVE → 409, 15분 리허설 2회 |
| **DBA** (겸임) | 은태현 | ERD(DBML) 작성, 1:N / N:M · 정규화 근거, SQLAlchemy 모델, 시드 데이터, Supabase/SQLite 연결 | ERD, 모델, 시드 스크립트 | `docs/06_erd/`, `backend/app/models/`, `backend/app/db/` | dbdiagram 렌더 이미지 첨부, 기동 시 샘플 5건 시드, `DATABASE_URL` 교체만으로 Postgres 전환 |

### 공통 규칙
- 산출물 간 불일치가 생기면 **CONTRACT.md 가 우선**이며, CONTRACT 변경은 PM 승인 후 PR로만 한다.
- 각자 담당 폴더는 본인이 커밋한다 (R&R 채점 대비, `github_guide.md` §6).
- 데일리 스탠드업 09:30 / 체크포인트 12:00·17:00, 10분 이내.

---

## 2. 3일 일정표 (시간 단위)

범례: ◆ 체크포인트(PM 진행) · ★ 최우선 · ⚠ 지연 시 범위 축소 후보

### 1일차 (09-02, 화) — 기획 · 아키텍처 · 환경

| 시간 | 블록 | 은태현 (PM/DBA) | 문승은 (UX/FE) | 신서현 (DevOps) | 정구현 (API/BE) | 장병헌 (BE/발표) |
|---|---|---|---|---|---|---|
| 09:00~09:30 | 킥오프 | 기획서 v3 확정, 범위 선언 | 참여 | 참여 | 참여 | 참여 |
| 09:30~10:30 | 계약 확정 | **CONTRACT.md 낭독·확정**(상태값·API·샘플) | 화면 2개 ↔ API 매핑 확인 | 레포 생성, 브랜치·라벨·PR 템플릿 | 엔드포인트 15개 Method/Path/Status 확정 | AgentRun JSON·Mock 전이 규칙 확정 |
| 10:30~12:00 | 오전 작업 | 샘플 데이터(설비 3·부품 4·법령 6·요청 5) 정리 | UC-01~07 표 작성 | FE/BE 스캐폴딩, .env.example, CORS·proxy | 아키텍처 다이어그램 초안 | AI-Ready 4원칙 문서, 프롬프트(A2) |
| 12:00~12:15 | ◆ CP1 | 전원: CONTRACT 이견 없음 확인, 레포 접근 확인 | | | | |
| 13:00~15:00 | 오후 작업 1 | ERD 초안(DBML) 시작 | 와이어프레임 화면1·화면2 | 전원 첫 커밋 유도, CI 없음/로컬 실행 확인 | `openapi.yaml` 초안 | 상태머신 다이어그램, 오케스트레이터 인터페이스 정의 |
| 15:00~17:00 | 오후 작업 2 | 기획서 §11·§12 정리, 슬라이드 목차 | 와이어프레임 보완, FE 라우터·화면 뼈대 | `README` 빠른 시작 실제 재현 테스트 | Postman Collection 예시 응답 | `services/agents/` Mock 구현 시작 |
| 17:00~17:30 | ◆ CP2 | 1일차 산출물 상태표: 기획서·UC·와이어프레임·아키텍처·레포 ✔ 여부 | | | | |

**1일차 종료 기준**: 기획서 v3 · UC 7개 · 와이어프레임 2장 · 아키텍처 다이어그램 · 레포(전원 커밋 1건 이상) · 샘플 데이터 확정.

### 2일차 (09-03, 수) — ERD · API · 스캐폴딩 · E2E

| 시간 | 블록 | 은태현 (PM/DBA) | 문승은 (UX/FE) | 신서현 (DevOps) | 정구현 (API/BE) | 장병헌 (BE/발표) |
|---|---|---|---|---|---|---|
| 09:00~09:30 | 스탠드업 | 블로커 확인, 오후 연동 순서 공지 | | | | |
| 09:30~12:00 | 오전 작업 | ★ ERD 완성(14개 테이블, N:M 2개, 정규화 근거) → SQLAlchemy 모델·시드 | ★ 화면1 목록/대시보드 + 화면2 타임라인 (Mock 모드) | Postman Mock 서버 기동 → FE `VITE_API_BASE` 전환 테스트, 데이터 리셋 스크립트 | ★ 라우터: work-requests · agent-runs · dashboard · equipments/parts (Swagger) | ★ 오케스트레이터 Mock step 전이, `submit-approval` 422, `approvals` 409 게이트 |
| 12:00~12:15 | ◆ CP3 | BE 단독: Swagger에서 15개 호출 응답 코드 확인 / FE 단독: Mock 모드 90초 시나리오 | | | | |
| 13:00~14:30 | 오후 작업 1 | DB 연결(SQLite → Supabase 전환 확인), `legal_findings`·`documents` 정규화 저장 | 승인 패널(체크리스트 → 승인 버튼 활성/비활성), 409·422 에러 표시 | **연동 준비**: CORS, proxy, 응답 필드명 CONTRACT 대조 | documents · laws/search · ai-config 라우터 | 승인 상태머신 마무리, audit_logs 기록 |
| **14:30~17:00** | **★ FE-BE 연동 (핵심 체크포인트 구간)** | 시드 데이터로 목록 5건 노출 확인 | `VITE_USE_MOCK=false` 로 전환, 화면 바인딩 확인 | **연동 주도**: 순서 ① `GET /work-requests` ② `POST` 생성 ③ `POST …/agent-runs` 202 ④ `GET /agent-runs` ×4 ⑤ `PATCH submit-approval` ⑥ `POST approvals` 409→201 | 필드명·상태코드 불일치 즉시 수정 | Mock 전이·게이트 불일치 즉시 수정 |
| **17:00~17:30** | **◆ CP4 (필수)** | **실 API로 90초 데모 전 구간 1회 완주.** 실패 항목은 담당자 지정 후 당일 마감 | | | | |
| 17:30~19:00 | 보정 | 산출물 상태표 갱신, 슬라이드 본문 | 스타일·문구 다듬기 | E2E 체크리스트 1차 실행 | OpenAPI ↔ 실제 응답 대조 | 발표 스크립트 초안 |

**2일차 종료 기준**: ERD · Swagger(OpenAPI) · Postman Mock · FE 화면 2개 · BE 핵심 API · DB 연결 · **실 API 90초 데모 완주**.

### 3일차 (09-04, 목) — E2E · 발표 자료 · 리허설 · 15:00 발표

| 시간 | 블록 | 은태현 (PM/DBA) | 문승은 (UX/FE) | 신서현 (DevOps) | 정구현 (API/BE) | 장병헌 (BE/발표) |
|---|---|---|---|---|---|---|
| 09:00~09:30 | 스탠드업 | 남은 결함 우선순위 | | | | |
| 09:30~11:00 | E2E · 마감 | 슬라이드 완성(문제→해결→아키텍처→ERD→API→AI-Ready→데모→확장) | 화면 마무리, 에러 토스트 문구 | **E2E 체크리스트 전 항목 실행**(`docs/09_qa/e2e_test_checklist.md`), Postman Mock 백업 경로 재확인 | Swagger 스크린샷, API 표 슬라이드용 | 발표 스크립트 완성, Q&A 답변 정리 |
| 11:00~12:00 | ◆ CP5 | **루브릭 자체 점검**(`docs/09_qa/self_review_rubric.md`) 전원 함께 체크, 보완 항목 배정 | | | | |
| 13:00~14:00 | 리허설 1 | 타이머 15분 측정 | 데모 클릭 담당(또는 신서현) | 데모 환경 세팅(브라우저·데이터 리셋) | Q&A 보조 | 발표 |
| 14:00~14:40 | 리허설 2 + 코드 프리즈 | main 최종 머지, README 최종 확인 | | 데이터 리셋, 백업 탭 준비 | | 시간 초과 구간 삭감 |
| 14:40~15:00 | 이동·세팅 | | | 화면 공유·해상도 확인 | | |
| **15:00~15:20** | **발표 15분 + Q&A 5분** | 슬라이드 넘김 | | 데모 조작 | Q&A(설계) | 발표·Q&A(AI·BE) |

---

## 3. 리스크 · 대응

| # | 리스크 | 영향 | 징후 | 대응 (Plan B) | 담당 |
|---|---|---|---|---|---|
| R1 | 2일차 오후 FE-BE 연동 실패 (CORS·필드명·상태코드 불일치) | 데모 불가 | CP4 에서 90초 완주 실패 | 필드명은 CONTRACT 대조로 즉시 수정. 17:30 까지 미해결 시 **3일차 데모는 `npm run dev:mock` 또는 Postman Mock** 으로 진행하고 BE는 Swagger로 별도 시연 | 신서현 |
| R2 | Supabase(PostgreSQL) 연결 지연·네트워크 제한 | DB 연동 항목 감점 | 2일차 오전 연결 실패 | **SQLite 폴백**으로 개발·데모, 슬라이드에 `DATABASE_URL` 교체만으로 전환됨을 다이어그램·.env 로 증명 | 은태현 |
| R3 | 범위 과다 (UC 7개·엔드포인트 15개 전부 구현 시도) | 핵심 화면 미완 | 2일차 12:00 화면2 미완 | 데모 경로 6개 엔드포인트(work-requests·agent-runs·submit-approval·approvals·dashboard)만 실구현, 나머지는 Mock 응답 고정 | 은태현 |
| R4 | Mock step 전이 타이밍 (폴링 3초 × 4 = 12초가 데모에서 길게 느껴짐) | 데모 지루 | 리허설 1 | 폴링 간격 2초로 조정하거나 발표자가 각 카드 결과를 설명하며 시간 채움 | 문승은·장병헌 |
| R5 | 커밋이 특정 인원에 편중 (R&R 채점) | GitHub 관리 감점 | 1일차 저녁 기여자 그래프 | 담당 폴더는 본인이 커밋, 페어 작업 시 `Co-authored-by` 트레일러, PM이 매일 `git shortlog -sn` 확인 | 신서현 |
| R6 | 발표 시간 초과 (15분) | Q&A 시간 잠식 | 리허설 1 에서 17분 이상 | 확장(§12)·SK AX 근거 슬라이드는 1장으로 압축, 데모는 90초 고정 | 장병헌 |
| R7 | 데모 중 데이터 오염 (리허설로 요청이 APPROVED 상태로 남음) | 시나리오 재현 불가 | 목록에 중복 요청 | 데이터 리셋 명령(`rm argus.db` 후 재기동 → 시드) 을 리허설 직후 실행, 체크리스트에 포함 | 신서현 |
| R8 | 법령 인용 정확성 질문 | Q&A 신뢰도 | Q&A | "샘플 6개 조문은 예시 발췌, 실제는 법제처 API 사전 적재 + 조문 인용 없는 답은 `required=UNKNOWN`" 으로 답변 준비 | 장병헌 |
| R9 | 팀원 부재·환경 문제 (노트북 고장 등) | 담당 산출물 지연 | 스탠드업 불참 | 모든 산출물은 레포에 매일 push, 데모 환경은 신서현·문승은 2대에 동일 구성 | 전원 |

### 범위 축소 우선순위 (지연 시 이 순서로 뺀다)
1. `GET/PUT /tenants/{id}/ai-config` 화면 (문서·API만 유지)
2. `/glass` 선택 채널
3. `GET /laws/search` 화면 (API만 유지)
4. 대시보드 반려 사유 TOP (KPI 4개만 유지)
5. **절대 빼지 않는 것**: 화면2 타임라인 + 승인 패널 + 409 게이트, ERD, OpenAPI
