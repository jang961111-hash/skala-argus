# ReplaceFlow — 루브릭 자체 점검표 (v3.0 최종 사양 기준)

실행: 3일차 11:00 CP5 (전원) · 진행: PM 은태현 · 기록: 신서현
**3차 기입: 2026-09-03 15:37, PM 은태현** — `bash scripts/collect_evidence.sh` 직접 실행 후 그 출력만 인용.
근거는 전부 레포 실물 파일 + `docs/10_project_record/02_evidence/` 원본 로그.

## 실측 증거 (내가 직접 돌린 값 — `20260903_1537`)

| 항목 | 값 | 원본 로그 |
|---|---|---|
| `pytest -q` | **30 passed** (2 warnings, 2.20s) | `02_evidence/test_results/pytest_20260903_1537.log` |
| `scripts/e2e_live_v3.sh` | **64 통과 / 0 실패** | `..._/e2e_live_v3_20260903_1537.log` |
| `npm run build` | 성공 · **223.58 kB** (gzip 81.73 kB) | `..._/fe_build_20260903_1537.log` |
| 화면 캡처 | v3.0 **9장** + v1.0 대조 2장 | `02_evidence/screenshots/` |
| 코드 규모 | backend .py **54** · frontend .vue **18** · docs **89** | `02_evidence/inventory/artifacts_inventory.md` |

> ⛔ **무효 수치(지우지 않고 표시)**: v1.0 의 `pytest 8/8` · `e2e_live.sh 35/35` · Postman 21요청/78예시.
> 틀린 게 아니라 **검증 대상이 바뀐 것**이다(v3.0 은 16요청/67예시).

## 3차 집계 (73항목) — 실측 반영

| 상태 | 개수 | 2차 대비 |
|---|---|---|
| ✔ 완료 | **41** | +12 (BE·FE 구현 완료 + 실측 확보) |
| ◐ 진행 중 | **14** | |
| ⏳ 구현 중 | **6** | 문서 트랙(아키텍처·프롬프트·UC) |
| ☐ 미착수 | **6** | 리허설·슬라이드·회고 |
| **✖ 미충족** | **6** | 변동 없음 |

### 🚨 ✖ 6건 — 위장하지 않고 정직하게 표기한 항목

| # | 항목 | 사실 | 대응 |
|---|---|---|---|
| 1 | **N:M 관계** (2-1) | **v3.0 범위에 N:M 0개.** 팀 ERD 원문이 명시 | `erd.md:88-109` 에 1:N **8개** 표 + **왜 없는지** 설명 + `erd_phase2.mmd` 예비 N:M 설계. **루브릭 명시 요구라 감점 위험을 안고 간다** |
| 2 | 5명 전원 커밋 (1-3) | **1인 명의 · 현재 변경분 134개 미커밋** | 팀 방침 = 통합 커밋 + 커밋 본문에 역할·이름 명시. `04_team/rnr_and_contributions.md` 가 담당별 산출물 근거 |
| 3 | PR 5건 이상 (1-3) | **PR 0건**, `develop`·`feature/*` 브랜치 미생성 | 미생성 상태 그대로 보고 |
| 4 | 이슈 담당자·라벨 (1-3) | **이슈 0건** | 동일 |
| 5 | Figma/Stitch 와이어프레임 (1-1) | **여전히 산출물 0건 · 미착수** | `figma_build_guide.md` 319줄 가이드만 존재. **다만 v3.0 실연동 캡처 9장**이 "구현 화면" 근거는 대신함 |
| 6 | 승인 체크리스트 409 (2-4) | **v3.0 에서 체크리스트 폐지** | 항목 자체가 무효 → 대체: `REJECT_REASON_REQUIRED` 400 (사유 10자 이상) |

> ⚠️ **무효가 된 과거 실측치**: `pytest 8/8` · `e2e_live.sh 35/35` 는 **v1.0 기준이라 근거로 쓸 수 없다.**
> `scripts/e2e_live.sh` 는 v1.0 증빙으로 보존하되, v3.0 검증은 `scripts/e2e_live_v3.sh`(작성 중)로 대체된다.

---

## 1. 정량 — 서비스 기획 & 아키텍처 (30점)

### 1-1. Use-Case · 와이어프레임 완성도
| 점검 항목 | 근거 산출물 | 상태 | 보완 필요 사항 |
|---|---|---|---|
| Actor 정의 (엔지니어·안전관리자 + 에이전트 3종) | `docs/02_usecase/` | ◐ | v3.0 `Role` 은 `ENGINEER`·`SAFETY_MANAGER` 2종으로 축소 — 반영 중 |
| UC 각각 Actor·전제·흐름·결과 상태 기재 | `docs/02_usecase/` | ⏳ | 상태 6종(`DRAFT`~`REJECTED`)으로 교체 중 |
| UC 다이어그램 1장 | `docs/02_usecase/usecase_diagram.svg` | ✔ | 실재 (v3.0 상태명 갱신 필요) |
| **화면 9종** 와이어프레임 (C_00·C_01·E_01~E_05·S_01·S_02) | `docs/03_wireframe/` | ✖ | **Figma 산출물 0건.** `figma_build_guide.md` 319줄 가이드만 존재 — Figma/Stitch 결정 대기 |
| 화면 요소에 호출 API 표기 (화면 ↔ API 매핑) | `docs/CONTRACT.md` §7 | ✔ | **9화면 × API 번호 매트릭스 완비** |
| 구현 화면이 화면정의서와 일치 | `frontend/src/views/` | ◐ | **v3.0 캡처 9장 확보**(실연동). 단 S_02 가 2장이라 **`WRA_C_01` 회원가입만 미캡처** — 1장 추가 필요 |
| 제품 유형 5종 동적 스펙 정의 | `CONTRACT.md` §2 | ✔ | `VALVE`/`FITTING_TUBE`/`REGULATOR`/`FILTER`/`ETC` 필수 키 표 |

### 1-2. AI 확장 지점 · 프롬프트/JSON 타당성
| 점검 항목 | 근거 산출물 | 상태 | 보완 필요 사항 |
|---|---|---|---|
| AI 확장 지점이 코드 인터페이스로 존재 | `backend/app/services/agent_service.py` | ✔ | `services/agents/base.py`·`mock_agents.py`·`llm_agents.py` 실재 · pytest 30 passed |
| AI-Ready 4원칙 매핑표 | `docs/04_architecture/` | ⏳ | v3.0 구조로 재작성 중 |
| 프롬프트 System/User 분리, 출력 JSON 강제 | `docs/05_ai_ready/prompts.md` | ⏳ | A4 절 제거 + `payload_json` 구조 정합 |
| 결과 JSON 스키마가 CONTRACT 와 동일 | `CONTRACT.md` §4-13 | ✔ | `docs/05_ai_ready/schemas/agent_result_items|documents.schema.json` 분리 실재 |
| `ai_configs` provider/egress 설계 | `CONTRACT.md` §5 테이블 8 [제안] | ◐ | **제안 상태.** 부분 유니크 `UNIQUE(agent_code) WHERE is_active`, API 키는 환경변수 |
| 에이전트 실패 처리 규격 | `CONTRACT.md` §4-12 | ✔ | step 만 `FAILED`+`errorMessage`, **HTTP 200 유지** |
| Human-in-the-loop 이 상태·권한으로 구현 | `CONTRACT.md` §3·§4-15 | ✔ | 승인은 `SAFETY_MANAGER` 만(403), 거절 사유 필수(400). **AI 는 결정하지 않는다** |

### 1-3. GitHub 관리 · R&R 적절성
| 점검 항목 | 근거 산출물 | 상태 | 보완 필요 사항 |
|---|---|---|---|
| README 에 팀 R&R 표 | `README.md` §7 | ✔ | 5명 역할·산출물·담당파일 |
| R&R 상세 + 3일 일정 + 리스크 | `docs/01_planning/rnr_and_schedule.md` | ✔ | 93줄 |
| 브랜치 전략·커밋 규칙·PR 템플릿 문서 | `docs/01_planning/github_guide.md`, `.github/` | ◐ | **문서만 존재.** `develop`·`feature/*` **미생성**, 현재 `main` 단독 |
| 5명 전원 커밋, 편중 없음 | `git shortlog -sn` | ✖ | **1인 명의.** 팀 방침 = 통합 커밋 + **커밋 본문에 담당 역할·이름 명시** |
| PR 5건 이상, 리뷰 코멘트 | `gh pr list` | ✖ | **0건** |
| 이슈에 담당자·라벨 지정 | `gh issue list` | ✖ | **0건** |
| `.gitignore` 로 `.env`·DB 미커밋 | 레포 트리 | ✔ | `.env` 미추적 확인, `.env.example` 은 커밋 |
| Contributors 캡처 슬라이드 | `docs/08_presentation/` | ☐ | **1인 명의라 캡처는 역효과** — 대신 "통합 커밋 방침" 슬라이드로 대체 권고 |

### 1-4. FE-BE-DB 다이어그램
| 점검 항목 | 근거 산출물 | 상태 | 보완 필요 사항 |
|---|---|---|---|
| FE(Vue) ⇄ BE(FastAPI) ⇄ DB 3계층 | `docs/04_architecture/` | ⏳ | v3.0 재작성 중 |
| BE 내부 계층이 폴더 구조와 일치 | `backend/app/` | ⏳ | `services/` 작업 중(auth·photo·agent·approval·dashboard) |
| AI 확장 지점(Mock → LLM) 표시 | `docs/04_architecture/` | ⏳ | |
| 시퀀스: 등록 → 202 → 폴링 → AI_DONE → 승인 | `docs/04_architecture/` | ⏳ | v3.0 상태명으로 재작성 |
| 온프레미스 경계(egress=false) 표시 | `ai_configs.egress_allowed` | ◐ | 제안 테이블에 근거 존재 |

## 2. 정량 — 시스템 설계 & 스캐폴딩 (30점)

### 2-1. ERD 1:N / N:M · 정규화
| 점검 항목 | 근거 산출물 | 상태 | 보완 필요 사항 |
|---|---|---|---|
| 테이블 전부 DBML 작성 + 렌더 이미지 | `docs/06_erd/replaceflow.dbml`, `erd.svg` | ✔ | **8테이블**(7+`ai_configs` 제안). sqlglot·dbml2sql 검증 통과 |
| **1:N 관계 명시** | `erd.md:88-102` | ✔ | **8개** — users→work_requests/approvals, work_requests→photos/agent_runs/approvals, agent_runs→agent_steps/agent_results, ai_configs→agent_runs |
| **N:M 관계** | `erd.md:103-109`, `erd_phase2.mmd` | ✖ | **0개. 루브릭 명시 요구 미충족.** 대응: 왜 없는지 설명(마스터 테이블 부재) + Phase 2 예비 N:M 설계 + 확장 ER 다이어그램 |
| 정규화 근거 | `erd.md`, `CONTRACT.md` §5 | ✔ | **사실/추론/행동 3층 분리** · 대리키 UUID + 업무키 UNIQUE · append-only 이력 · jsonb 는 가변 구조만 |
| PK/FK·ENUM 이 CONTRACT 문자열과 동일 | `docs/06_erd/`, `CONTRACT.md` §2 | ✔ | Enum 7종 일치 |
| SQLAlchemy 모델이 ERD 와 일치 | `backend/app/models/` | ◐ | **7개 실재** (`ai_configs` 제안은 미구현) |
| 인덱스 설계 근거 | `CONTRACT.md` §5 | ✔ | `(requester_id,status)` E_01·E_05 / `(status,submitted_at)` S_01 / `request_no` UNIQUE |

> **정규화 이슈 3건 소멸** — v1.0 에서 내가 지적한 `part_compatibility` 중복 저장 · `legal_findings` 스냅샷 중복 · `work_requests.tenant_id` 복합 FK 부재는 **대상 테이블이 v3.0 범위에서 빠지며 문제 자체가 사라졌다**(`erd.md:21`).
> ⚠️ 발표에서 **"고쳤다"고 말하면 안 된다. "범위 축소로 소멸했다"가 사실**이다. Phase 2 에서 해당 테이블이 부활하면 지적도 함께 부활한다.

### 2-2. Mock API RESTful 규격 준수
| 점검 항목 | 근거 산출물 | 상태 | 보완 필요 사항 |
|---|---|---|---|
| OpenAPI 3.0 파일, `/api/v1` prefix | `docs/07_api/openapi.yaml` | ✔ | **12 paths / 15 operations** 실측 |
| 리소스 명사·복수형 | `CONTRACT.md` §4 | ✔ | `POST /agent-runs`·`POST /approvals` 는 **최상위 경로**(body 에 `workRequestId`) |
| 상태코드 체계 | `CONTRACT.md` §6 | ✔ | **에러코드 23종** — 400·401·403·404·409·**413**·422·500 |
| 페이지네이션 `page`(0-base)·`size`·`sort` | `CONTRACT.md` §1 | ✔ | 응답 `content[]` + `page{}`, `status` 콤마 다중 지정 |
| 단일 에러 포맷 `{code,message,fieldErrors}` | `CONTRACT.md` §1.1 | ✔ | `backend/app/core/errors.py` 실재 · **E2E 64/0 이 23종 에러코드 경로 포함** |
| Postman Collection + 예시 응답 | `postman/` | ✔ | **요청 16개 / 예시 67개** 실측 |
| Swagger UI 전 엔드포인트 호출 | `/docs` | ◐ | BE 구현 완료(라우터 5종). **내가 직접 열어보진 않음 — 미검증** |

### 2-3. FE/BE 구조 · DB 연동
| 점검 항목 | 근거 산출물 | 상태 | 보완 필요 사항 |
|---|---|---|---|
| FE 구조: router/store/views/components/api 분리 | `frontend/src/` | ✔ | `views/` 가 **auth·engineer·safety 폴더로 역할 분리** |
| FE API 클라이언트 axios 집중 + JWT 주입 | `frontend/src/api/` | ✔ | `frontend/src/api/client.js` + `store/session.js` |
| BE 구조: routers → services → repositories → models | `backend/app/` | ✔ | `routers` 5 · `services` 6 · `repositories` 5 · `models` 4 · `schemas` 7 실재 |
| DB 연동: `DATABASE_URL` SQLite ↔ Supabase | `backend/app/db/`, `docs/09_qa/supabase_runbook.md` | ◐ | 런북 `docs/06_erd/supabase_apply.md`·`09_qa/supabase_runbook.md` 실재. **Supabase 실제 실행은 미검증** |
| 실제 DB 쓰기·읽기 유지 | E2E | ✔ | **E2E 64/0** — 실 uvicorn 상대 등록→폴링→편집→승인 왕복 |
| README 빠른 시작 5분 내 기동 | `README.md` | ◐ | v3.0 절차로 갱신 필요 |
| pytest 1개 이상 | `backend/tests/` | ✔ | **30 passed** (`pytest_20260903_1537.log`) |

### 2-4. 데이터 바인딩 화면 시연
| 점검 항목 | 근거 산출물 | 상태 | 보완 필요 사항 |
|---|---|---|---|
| E_01/S_01: 역할별 KPI 4개가 API 로 렌더 | `views/engineer/`, `views/safety/` | ✔ | 캡처 `v3.0_WRA_E_01`·`v3.0_WRA_S_01` + E2E 64/0 |
| E_03: 폴링(`pollIntervalMs:2500`)으로 3종 카드 전이 | `views/engineer/AgentRunView.vue` | ✔ | 캡처 `v3.0_WRA_E_03_AI검증진행_폴링.jpg` |
| ~~승인 체크리스트 409~~ | — | ✖ | **v3.0 폐지.** 대체 항목: `REJECT_REASON_REQUIRED` 400 (사유 10자 이상) |
| 오류 케이스 화면 표시 | 23종 에러코드 | ✔ | E2E 64/0 에 403·409·413·422 포함 |
| 90초 데모 3회 리허설 | `docs/09_qa/e2e_test_checklist.md` | ☐ | 9/4 13:00·14:00·14:40 |
| 백업 경로(Postman Mock) 동작 | `postman/` | ◐ | 컬렉션 16요청/67예시 실재. 퍼블리시 미실시 |

## 3. Peer 40%

### 3-1. 기획 · UX
| 점검 항목 | 근거 산출물 | 상태 | 보완 필요 사항 |
|---|---|---|---|
| 문제가 현업 경험(As-Is 표)으로 구체적 | `planning_final.md:35-51` | ✔ | ③④⑤ 일주일 vs ⑥ 2시간 |
| 페르소나 2명 명확 | `planning_final.md:32` | ◐ | **한 줄뿐** — 페르소나 시트 없음 |
| SK AX·하이닉스 근거 출처 | `planning_final.md` §3 | ✔ | |
| 역할 분리 흐름이 90초 안에 이해됨 | 데모 | ⏳ | **9화면 역할 분리** 서사로 교체(구 "2화면 압축" 무효) |
| 승인자 코멘트가 메신저 왕복 대체 | `planning_final.md` §6 | ✔ | |

### 3-2. 시스템 설계
| 점검 항목 | 근거 산출물 | 상태 | 보완 필요 사항 |
|---|---|---|---|
| 상태머신 다이어그램 슬라이드 1장 | `CONTRACT.md` §3 | ✔ | 6상태 전이도 + 조건·오류코드 표 완비 |
| 202 + 폴링 비동기 설계 이유 설명 | `CONTRACT.md` §4-11·12 | ✔ | `pollIntervalMs` 를 **서버가 내려주는** 설계 근거 |
| ERD 3층 분리 설계 이유 30초 설명 | `erd.md`, `CONTRACT.md` §5 | ✔ | 사실/추론/행동 + append-only |
| API 표를 Method/Path/Status 로 슬라이드 제시 | `docs/08_presentation/` | ☐ | 슬라이드 실물 미제작 |

### 3-3. AI-Ready 확장성
| 점검 항목 | 근거 산출물 | 상태 | 보완 필요 사항 |
|---|---|---|---|
| Mock → LLM 교체 지점 즉답 | `backend/app/services/agent_service.py` | ✔ | `services/agents/llm_agents.py` — `mock_agents.py` 와 동일 인터페이스 |
| 온프레미스 제약 설명 | `ai_configs.egress_allowed` | ◐ | `ai_configs` 는 **[제안] 테이블로 미구현** |
| 법령 RAG 확장 경로 | `erd_phase2.mmd`, `erd.md:148` | ✔ | **조문 마스터 ↔ 결과 N:M + quote 스냅샷** 설계 존재 |
| Phase 2 범위가 명시적 | `CONTRACT.md` §2·§8-10 | ✔ | A1 호환표 연동 · A4 벤더 에이전트 |

### 3-4. 구현 · Pitch
| 점검 항목 | 근거 산출물 | 상태 | 보완 필요 사항 |
|---|---|---|---|
| 발표 15분 이내 (리허설 2회 측정) | | ☐ | |
| 데모 클라이맥스 | | ☐ | **재설계 필요** — 구 클라이맥스(체크리스트 409)가 폐지됨. 대안: 폴링 3종 완료 → 결과 편집 → 승인 |
| 발표자·데모·Q&A 역할 분담 | `rnr_and_schedule.md` | ✔ | |
| 슬라이드에 GitHub·Swagger·ERD 캡처 | | ☐ | |
| 한계를 먼저 말하고 확장으로 마무리 | `retrospective_template.md` | ◐ | §1·§2 작성됨, §3·§4 공란 |
| **명칭 통일** (FixGuide / ReplaceFlow) | `CONTRACT.md` 머리말 ⚠ | ☐ | **팀 확인 필요 — 발표 전 반드시 하나로** |

---

## 4. 점검 결과 요약 (2차 기입 2026-09-03 저녁)

| 영역 | 항목 | ✔ | ⏳ | ◐ | ☐ | ✖ | 보완 담당 · 마감 |
|---|---|---|---|---|---|---|---|
| 1-1 Use-Case·와이어프레임 | 7 | 3 | 1 | 2 | 0 | 1 | 문승은 · 9/4 10:00 |
| 1-2 AI 확장·프롬프트 | 7 | 3 | 3 | 1 | 0 | 0 | 정구현 · 9/4 11:00 |
| 1-3 GitHub·R&R | 8 | 3 | 0 | 1 | 1 | 3 | **전원 · 9/4 13:00** |
| 1-4 다이어그램 | 5 | 0 | 4 | 1 | 0 | 0 | 은태현 · 9/4 09:00 |
| 2-1 ERD | 7 | 5 | 0 | 1 | 0 | 1 | 은태현 · 완료(N:M 제외) |
| 2-2 API RESTful | 7 | 5 | 2 | 0 | 0 | 0 | 정구현 · 9/4 11:00 |
| 2-3 FE/BE 구조 | 7 | 1 | 4 | 2 | 0 | 0 | 장병헌·문승은 · 9/4 11:00 |
| 2-4 데이터 바인딩 | 6 | 0 | 3 | 1 | 1 | 1 | 문승은 · 9/4 12:00 |
| 3-1 기획·UX | 5 | 3 | 1 | 1 | 0 | 0 | 문승은 · 9/4 10:00 |
| 3-2 시스템 설계 | 4 | 3 | 0 | 0 | 1 | 0 | 은태현 · 9/4 12:00 |
| 3-3 AI-Ready | 4 | 2 | 1 | 1 | 0 | 0 | 정구현 · 9/4 11:00 |
| 3-4 구현·Pitch | 6 | 1 | 0 | 1 | 4 | 0 | 은태현·장병헌 · 9/4 13:00 |
| **합계** | **73** | **29** | **19** | **12** | **7** | **6** | |

*3-4 에 "명칭 통일" 1항목을 추가해 73항목이 됐다 — 발표 전 반드시 해소해야 할 사안이라 점검표에 올렸다.*

### 처리 순서 (3차 기준)

1. **✖ 6건은 성격이 갈린다** — N:M 0개·체크리스트 항목은 **설계 사실이라 설명으로 방어**한다. Figma·커밋·PR·이슈는 **오늘 밤~내일 오전에 실행하면 해소**된다
2. **☐ 6건이 실질 병목** — 리허설 3회·슬라이드 캡처·회고 §3§4·명칭 통일. 전부 사람이 해야 하고 내일 오전에 몰려 있다
3. **미검증이라고 쓴 2건**(Supabase 실행 · Swagger UI 직접 호출)은 **억지로 ✔ 로 올리지 않았다.** 돌려본 사람이 갱신한다

### 발표에서 먼저 꺼낼 한계 3가지
- **N:M 0개** — 마스터 테이블이 없는 범위라 연결 테이블만 만들면 빈 테이블이 된다(`erd.md` §3) + `erd_phase2.mmd` 확장 설계 제시
- **Supabase 미실행** — 로컬 SQLite 로 검증했고 DDL·런북은 준비돼 있다
- **커밋이 1인 명의** — 통합 커밋 방침이었고 담당별 산출물은 `04_team/` 에 기록

처리 불가 항목은 숨기지 말고 **"한계"로 먼저 언급**한다.
