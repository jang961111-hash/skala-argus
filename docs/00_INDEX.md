# ReplaceFlow 산출물 인덱스 (미니프로젝트 가이드·루브릭 기준)

가이드(과정 범위·3일 로드맵·R&R Guide·Pitch 구성·Rubric)에서 요구하는 산출물을 전부 나열하고, 어디에 있는지·검증 상태를 표시한다. ☑ = 자체 검증 완료.

## 1일차 — 서비스 기획 & Architecture 정의
| 가이드 요구 | 산출물 | 위치 | 검증 |
|---|---|---|---|
| AI-Ready 아이디어 선정 | 기획서 최종본(문제·페르소나·SK AX 연결·에이전트 배치) | `docs/01_planning/planning_final.md` | ☑ |
| Teaming · R&R 정의 | R&R 표, 3일 시간표, 리스크 | `docs/01_planning/rnr_and_schedule.md`, `README.md` §팀 | ☑ |
| Actor 중심 Use-Case 정의 | UC-01~07 정식 명세 + Actor 표 | `docs/02_usecase/usecase_spec.md` | ☑ |
| AI 확장 지점 정의 | 에이전트 4개+오케스트레이터, 사람이 남는 곳 | `usecase_spec.md` "AI 확장 지점 정의", `planning_final.md` §4·§7 | ☑ |
| UI/UX 화면 흐름도(Wireframe) | 화면1·2·흐름도·글라스뷰 HTML 목업(데모 애니메이션), Figma 구조 명세 | `docs/03_wireframe/wireframe.html`, `wireframe_spec.md` | ☑ 브라우저 동작 |
| 개발환경 세팅 (FE/BE/DB 프로젝트 생성) | Vue3+Vite / FastAPI / PostgreSQL(SQLite 폴백) | `frontend/`, `backend/` | ☑ 빌드·테스트 |
| 프로젝트 기본 구조 | 폴더 트리, .gitignore, PR 템플릿, 브랜치·커밋 규칙 | `README.md`, `docs/01_planning/github_guide.md`, `.github/` | ☑ |
| FE-BE-DB 전체 시스템 구조 다이어그램 | 아키텍처 SVG + 설명(4원칙 매핑) + 상태머신 + 시퀀스 | `docs/04_architecture/*.svg`, `architecture.md` | ☑ Mermaid 렌더 |

## 2일차 — 시스템 설계 & Scaffolding
| 가이드 요구 | 산출물 | 위치 | 검증 |
|---|---|---|---|
| 데이터 모델링(ERD) 1:N·N:M·정규화 | DBML(dbdiagram), PostgreSQL DDL, 시드, 설계 설명 | `docs/06_erd/` | ☑ PostgreSQL 16 실행·재실행 |
| REST API 명세 (Mock 엔드포인트 포함) | OpenAPI 3.0(Swagger Editor), 사람용 명세, 설계 근거 | `docs/07_api/openapi.yaml`, `api_spec.md` | ☑ Redocly 0 error |
| Postman Mock Server | 컬렉션(52 예시 응답, 폴링 5단계) + 환경 | `postman/` | ☑ JSON 파싱 |
| AI 프롬프트 · 입출력 JSON 규격 | 프롬프트 4종+정책+가드레일+Playground 검증 절차, JSON Schema 6종 | `docs/05_ai_ready/` | ☑ jsonschema 통과·역예제 거부 |
| Full-Stack Scaffolding (FE/BE API 연동, DB 연결) | FE 화면 2개+컴포넌트, Mock 모드 / BE 15 엔드포인트, 상태머신, 오케스트레이터, seed | `frontend/src/`, `backend/app/` | ☑ pytest 8/8, curl E2E |
| 핵심 화면 & 데이터 흐름 End-to-End 검증 | E2E 체크리스트(정상 22·오류 14·비기능 10) + 리허설 절차 | `docs/09_qa/e2e_test_checklist.md` | ☑ 실BE E2E 재현 |

## 3일차 — 설계 검증 & 최종 발표
| 가이드 요구 | 산출물 | 위치 | 검증 |
|---|---|---|---|
| Project Pitch 자료 (6섹션 15분) | 슬라이드 16장 구성안 + 대본 + 시간 배분 | `docs/08_presentation/pitch_outline_and_script.md` | ☑ |
| Live Demo (메인 UI → Mock API → 렌더링) | 90초 데모 시나리오, 실패 대비 2중 백업 | 같은 파일 §데모 | ☑ |
| 회고 및 향후 확장 계획 | 한계·로드맵·R&R별 회고 템플릿 | `docs/09_qa/retrospective_template.md` | ☐ 각자 작성 |
| Q&A · Peer Review (필수 질문 1개) | 예상 질문 25개 답변 + 타 조 질문 3개 | `docs/09_qa/qa_bank.md` | ☑ |
| 루브릭 자체 점검 | 72개 체크 항목 | `docs/09_qa/self_review_rubric.md` | ☐ 제출 전 체크 |

## 공통
| 항목 | 위치 |
|---|---|
| 필드명·상태값·API·샘플 데이터 단일 계약 | `docs/CONTRACT.md` (모든 산출물이 이걸 따름) |
| 배경 리서치 (SK AX 사례, 스마트글라스·규격·법령 전수조사) | Claude 프로젝트 `claude/skax_ax_background_2026-09-02.md`, `claude/E안v2_전수조사_리서치부록.md` |

## 자체 검증 기록 (2026-09-02)
- BE: `pytest` 8 passed · uvicorn 기동 후 curl로 생성→202→폴링 4회→REVIEW→422/200→409/201→APPROVED 재현
- FE: `npm run build` 성공(182KB) · 승인 요청 시 서류 누락값 입력 로직 추가(BE 422 계약 정합)
- 계약 정합화 수정 3건: `agent_progress`를 `{done,total}`로 통일(BE·OpenAPI·FE), `submit-approval` body를 `missing_info`로 통일(OpenAPI·Postman·api_spec), 프롬프트 로더가 `prompts.md` 섹션 제목 형식과 맞도록 수정
- OpenAPI: Redocly lint valid · JSON Schema: 6종 통과 · SQL: sqlglot·pglast 파싱 + PostgreSQL 16 실행
- 남은 수동 항목: Figma 실제 제작(스펙 기반), GitHub 레포 생성·커밋, Supabase 프로젝트 생성 후 DDL·seed 실행, 회고 각자 작성
