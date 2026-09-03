# 프로젝트 기록 (A to Z)

> **목적**: 나중에 서버를 띄워 확인할 때 "왜 이렇게 됐는지"를 바로 알 수 있게 한다.
> 회고·피드백·점검의 단일 진입점이다. 코드가 답하지 못하는 것(의사결정·번복·실측 증거)만 여기 둔다.
>
> **최신화 규칙은 `RECORD_KEEPING.md` 에 있다. 팀원 전원 적용.**

최종 갱신: 2026-09-03 16:37 · 갱신자: PM 은태현

## 지금 상태 한 줄

**프로젝트명 `Argus` 확정. 계약 v3.0 구현 완료 — `pytest 30 passed` · 라이브 E2E `72/0` · FE 9화면 실연동 캡처 완료 · `develop`+`feature/*` 9개 브랜치 `--no-ff` 병합 후 push 완료.**
남은 건 **발표 준비**(슬라이드·회고·리허설 3회)와 **Supabase 실행(미검증)** · Stitch 진행분. 커밋은 **1인 명의**(통합 커밋 방침).

## 폴더 구조

| 경로 | 무엇이 있나 | 언제 보나 |
|---|---|---|
| `01_timeline/decision_log.md` | 의사결정과 근거, 번복 이력 | "왜 이렇게 정했지?" |
| `01_timeline/incident_log.md` | 사고와 복구 | "왜 한 번 갈아엎었지?" |
| `02_evidence/test_results/` | pytest·E2E·빌드 **원본 로그** | "진짜 통과했나?" |
| `02_evidence/screenshots/` | 화면 캡처 (v1.0 구버전 + v3.0 현행) | "화면이 실제로 이렇게 나오나?" |
| `02_evidence/inventory/` | 파일 목록·디렉터리 구조·git log | "무엇이 얼마나 있나?" |
| `03_contract_history/` | 계약 v1.0→v2.0→v3.0 변천 | "이 필드는 언제 왜 바뀌었나?" |
| `04_team/` | R&R과 담당별 산출물 | "누가 뭘 했나?" |
| `05_retrospective/` | 회고 | 발표 5번 섹션 |

## 실측 증거 (이 숫자만 발표에 쓴다) — `20260903_1637` 직접 실행

| 항목 | 값 | 원본 |
|---|---|---|
| 백엔드 테스트 | **30 passed** | `02_evidence/test_results/pytest_20260903_1637.log` |
| 라이브 E2E (실 uvicorn) | **72 통과 / 0 실패** | `..._/e2e_live_v3_20260903_1637.log` |
| 프론트 빌드 | 성공 · **223.88 kB** (gzip **81.98 kB**) | `..._/fe_build_20260903_1637.log` |
| 화면 | 9종 · argus_ 캡처 9장 | `02_evidence/screenshots/` |
| API | 15개 (OpenAPI 12 paths / 15 operations) | `docs/07_api/openapi.yaml` |
| ERD | 8테이블 · 1:N 8개 · **N:M 0개(Phase 2)** | `docs/06_erd/` |
| 에러 코드 | 23종 — E2E 가 경로 커버 | `docs/CONTRACT.md` §6 |
| Git | 33커밋 · `develop`+`feature/*` 9개 · `--no-ff` 병합 10건+ | `git log --merges` |

### 미검증 (억지로 통과 표시하지 않음)
| 항목 | 상태 |
|---|---|
| Supabase 실제 DDL 실행 | **미검증** — 로컬 SQLite 로 검증, 런북 준비됨 |
| `WRA_C_01` 회원가입 캡처 | **미확보** — 9화면 중 8화면만 커버(S_02 가 2장) |
| 회고 §3·§4 | **미작성** |

> ⚠️ **무효 수치(지우지 않고 표시)**: v1.0 `pytest 8/8`·`E2E 35/35`, v3.0 중간 `E2E 64/0`. 틀린 게 아니라 **검증 대상이 늘어난 것**이다(사진 업로드 §14 추가로 64→72).

## 재현 방법

```bash
# 백엔드 (Python 3.10+ 필수 — macOS 기본 python3 은 3.9라 실패한다)
cd backend && python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q                 # 기대: 30 passed

# 라이브 E2E (서버 자동 기동·종료, 포트 8820, 격리 DB)
bash scripts/e2e_live_v3.sh                   # 기대: 통과 64 / 실패 0

# 화면 (BE 8000 + FE 5173)
cd backend && .venv/bin/python -m uvicorn app.main:app --port 8000 &
cd frontend && npm install && npm run dev -- --port 5173
# 로그인: engineer@argus.test / safety@argus.test · 비밀번호 Passw0rd!
```
