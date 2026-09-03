# Argus 산출물 인덱스 (v3.0 최종 사양)

**기준 계약: `docs/CONTRACT.md` v3.0 (255줄).** 팀 노션 「API 명세서 v1.0 (REQ-F-0001)」 + 「FixGuide 데이터 모델 정의서 v3.0」 + 「WRA 화면정의서 v2.0」 원문 이관본.

표기: **☑** 검증 완료 · **⏳** 구현 중 · **🔄** 갱신 중 · **☐** 미착수 · **✖** 미충족
⚠️ **경로와 판정만 적는다.** 여러 트랙이 동시에 파일을 고치는 중이라 내용을 복사해 두면 몇 분 뒤 틀린다.

> ✅ **명칭 확정: `Argus`** — 코드·문서·화면·**GitHub 레포(`skala-argus`)·로컬 경로(`~/projects/argus`)**까지 통일 완료.
> `ReplaceFlow`·`FixGuide` 는 폐기. 아래에 남은 `FixGuide` 표기는 **팀 노션 원본 문서의 제목**이라 이력으로 보존한다.

---

## 계약 · 범위
| 항목 | 위치 | 상태 |
|---|---|---|
| **공통 계약서 v3.0** (쓰기 = 오케스트레이터 전용) | `docs/CONTRACT.md` | ☑ 255줄 |
| v1.0 보존 | `docs/CONTRACT_v1.0_archived.md` | ☑ |
| v2.0 폐기본 (추론본, 팀 문서와 불일치) | `docs/CONTRACT_v2.0_superseded.md` | ☑ |
| 범위 결정 기록 (A/B/C 산정) | `docs/09_qa/scope_decision_v2.md` | ☑ 이력 |

## 1일차 — 기획 & Architecture
| 가이드 요구 | 산출물 | 위치 | 상태 |
|---|---|---|---|
| AI-Ready 아이디어 선정 | 기획서 (문제·페르소나·SK AX 연결) | `docs/01_planning/planning_final.md` | 🔄 v3.0 반영 중 |
| Teaming · R&R | R&R 표, 3일 일정, 리스크 | `docs/01_planning/rnr_and_schedule.md`, `README.md` §7 | ☑ |
| Actor · Use-Case | UC 명세 + Actor 표 | `docs/02_usecase/` | 🔄 Role 2종·상태 6종으로 교체 중 |
| AI 확장 지점 | 에이전트 **A1·A2·A3** (A4 벤더 Phase 2) | `CONTRACT.md` §2, `docs/05_ai_ready/` | 🔄 |
| UI/UX 화면 흐름도 | **화면 9종** · Figma 제작 가이드 | `docs/03_wireframe/figma_build_guide.md` (319줄) | ✖ **Figma 산출물 0건** — Figma/Stitch 결정 중 |
| 화면 ↔ API 매핑 | 9화면 × API 번호 매트릭스 | `CONTRACT.md` §7 | ☑ |
| 개발환경 세팅 | Vue3+Vite / FastAPI / PostgreSQL(SQLite 폴백) | `frontend/`, `backend/` | ☑ |
| 프로젝트 기본 구조 | 폴더 트리, `.gitignore`, PR 템플릿 | `README.md`, `docs/01_planning/github_guide.md`, `.github/` | ☑ 문서 / ✖ **브랜치·PR 실적용 없음** |
| FE-BE-DB 다이어그램 | 아키텍처 + 상태머신 + 시퀀스 | `docs/04_architecture/` | ⏳ v3.0 재작성 |

## 2일차 — 시스템 설계 & Scaffolding
| 가이드 요구 | 산출물 | 위치 | 상태 |
|---|---|---|---|
| 데이터 모델링(ERD) | DBML · DDL · 시드 · 설명 · **ER 다이어그램** | `docs/06_erd/` (`argus.dbml`, `schema_postgres.sql`, `seed_data.sql`, `erd.md`, `erd.mmd`, `erd.svg`) | ☑ **8테이블**(7+`ai_configs` 제안) · sqlglot·dbml2sql 통과 |
| ├ 1:N 관계 | 8개 | `erd.md` §3 | ☑ |
| ├ **N:M 관계** | **0개** | `erd.md` §3, `erd_phase2.mmd` | ✖ **범위 내 없음 — 정직 표기.** Phase 2 예비 설계로 대응 |
| └ 정규화 | 사실/추론/행동 3층 · 대리키+업무키 UNIQUE · append-only | `CONTRACT.md` §5 | ☑ |
| REST API 명세 | OpenAPI 3.0 | `docs/07_api/openapi.yaml` | ☑ **12 paths / 15 operations** |
| ├ 에러 규격 | **23종** 단일 포맷 `{code,message,fieldErrors}` | `CONTRACT.md` §1.1·§6 | ☑ 명세 / ⏳ 구현 |
| Postman Mock | 컬렉션 + 환경 | `postman/` | ☑ **요청 16개 / 예시 67개** |
| AI 프롬프트 · JSON 규격 | 프롬프트 + 결과 스키마 | `docs/05_ai_ready/`, `CONTRACT.md` §4-13 | 🔄 A4 절 제거 중 |
| Full-Stack Scaffolding | FE **9화면**(auth·engineer·safety 폴더 분리) / BE 7모델 | `frontend/src/views/` (vue 10), `backend/app/` | ⏳ BE `services/` 구현 중 |
| End-to-End 검증 | v3.0 라이브 검증 · CI | `scripts/e2e_live_v3.sh` (작성 중), `.github/workflows/ci.yml` | ⏳ |
| DB 적용 절차 | Supabase 런북 | `docs/09_qa/supabase_runbook.md` | ☐ DDL 실행 대기 |

## 3일차 — 검증 & 발표
| 가이드 요구 | 산출물 | 위치 | 상태 |
|---|---|---|---|
| Project Pitch (6섹션 15분) | 구성안 + 대본 | `docs/08_presentation/pitch_outline_and_script.md`, `qa_reinforced.md` | 🔄 v3.0 대본 · 슬라이드 실물 미제작 |
| Live Demo | 시나리오 + 백업 | 같은 파일 | 🔄 **클라이맥스 재설계** (체크리스트 409 폐지) |
| 회고 · 향후 확장 | 한계 · 로드맵 · R&R별 | `docs/09_qa/retrospective_template.md` | ☐ §3·§4 공란 |
| Q&A · Peer Review | 예상 질문 + 보강 | `docs/09_qa/qa_bank.md`, `docs/08_presentation/qa_reinforced.md` | ☑ |
| 루브릭 자체 점검 | **73항목 실측 기입** | `docs/09_qa/self_review_rubric.md` | ☑ 2차 기입 · ⚠ **✖ 6건** |
| Day2 진척 보드 | 30태스크 판정 + 잔여 일정 | `docs/09_qa/progress_board.md` | ☑ |

## 검증 · 운영 산출물
| 항목 | 위치 | 상태 |
|---|---|---|
| DevOps 검증 리포트 | `docs/09_qa/devops_report.md` | ☑ |
| Postman ↔ 실 BE 대조 | `docs/09_qa/postman_verification.md` | ☑ (v1.0 기준) |
| E2E 체크리스트 | `docs/09_qa/e2e_test_checklist.md` | 🔄 v3.0 갱신 |
| 라이브 E2E (v1.0 증빙 보존) | `scripts/e2e_live.sh` | ☑ **v1.0 전용** |
| 라이브 E2E v3.0 | `scripts/e2e_live_v3.sh` | ⏳ 작성 중 |
| CI | `.github/workflows/ci.yml` | ⏳ |
| Figma 제작 가이드 (9화면 3등급) | `docs/03_wireframe/figma_build_guide.md` | ☑ 319줄 |
| Supabase 런북 | `docs/09_qa/supabase_runbook.md` | ☑ |

---

## 확정 실측치 — **직접 실행 검증** (`collect_evidence.sh`, 20260903_1659)

레포: **https://github.com/jang961111-hash/skala-argus** · 로컬 `~/projects/argus` · 원본 로그 `docs/10_project_record/02_evidence/test_results/`

| 항목 | 값 | 원본 |
|---|---|---|
| `pytest -q` | **30 passed** | `pytest_20260903_1659.log` |
| `scripts/e2e_live_v3.sh` | **72 통과 / 0 실패** | `e2e_live_v3_20260903_1659.log` |
| `npm run build` | 성공 · **223.88 kB** (gzip **81.98 kB**) | `fe_build_20260903_1659.log` |
| 화면 | 9종 · 캡처 **11장**(argus 9 + v1.0 대조 2) | `02_evidence/screenshots/` |
| ERD | **8테이블** · 1:N **8개** · **N:M 0개(Phase 2)** | `docs/06_erd/` |
| API | **15개** (OpenAPI 12 paths / 15 operations) · 에러코드 **23종** | `docs/07_api/openapi.yaml` |
| Postman | 요청 **16개** / 예시 **67개** | `postman/` |
| Git | **커밋 37** · **브랜치 12**(`main`+`develop`+`feature/*` **10**) · 추적 파일 **171** · **미커밋 0** | `git log --merges` |

### ⛔ 무효가 된 실측치 (지우지 않고 표시 — `RECORD_KEEPING.md` §2-3)
| 항목 | 값 | 사유 |
|---|---|---|
| `pytest` 8/8 | ✖ 무효 | v1.0 기준. **현행 30 passed** |
| `e2e_live.sh` 35/35 | ✖ 무효 | v1.0 기준(체크리스트 409 등 폐지 로직 포함). **현행 64/0**. 스크립트는 v1.0 증빙으로 보존 |
| Postman 21요청/78예시 | ✖ 무효 | v3.0 은 **16/67** |
| 정규화 지적 3건 | — | **범위 축소로 소멸.** "고쳤다"가 아니라 "대상 테이블이 Phase 2 로 빠졌다"가 사실 |

### 미검증 (억지로 통과 표시하지 않음 — `RECORD_KEEPING.md` §2-4)
| 항목 | 상태 |
|---|---|
| Supabase 실제 DDL 실행 | **미검증.** 로컬 SQLite 로 검증했고 런북(`06_erd/supabase_apply.md`)은 준비됨 |
| Swagger UI 전 엔드포인트 직접 호출 | **미검증.** BE 구현은 완료 |
| `WRA_C_01` 회원가입 화면 캡처 | **미확보.** v3.0 캡처 9장 중 S_02 가 2장이라 9화면 중 8화면만 커버 |

## 기록 체계 (상시 지침)
`docs/10_project_record/` — 갱신 규칙은 `RECORD_KEEPING.md`, 진입점은 `README.md`.
PM 책임: `README.md` 상태 한 줄 + 실측 표(하루 1회 이상) · `01_timeline/decision_log.md`(결정·번복 즉시) · 루브릭 반영.
노션 사본: https://app.notion.com/p/3d0a7f29102a812cbafee720e548f73c (로컬이 원본, 노션이 사본)

## 남은 수동 항목 (사람이 직접)
**Stitch 제작(진행 중)** · **Supabase DDL 실행(미검증)** · 발표 슬라이드 조판 · 회고 §3·§4 작성 · 리허설 3회 · 타 조 질의 1개 확정
*(명칭 통일·커밋·푸시는 완료 — 미커밋 0)*

---
*스캔 시점: 2026-09-03 저녁. 6개 트랙 동시 작업 중 — 판정이 아니라 경로를 신뢰하라.*
