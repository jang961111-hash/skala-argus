# 프로젝트 기록 (A to Z)

> **목적**: 나중에 서버를 띄워 확인할 때 "왜 이렇게 됐는지"를 바로 알 수 있게 한다.
> 회고·피드백·점검의 단일 진입점이다. 코드가 답하지 못하는 것(의사결정·번복·실측 증거)만 여기 둔다.
>
> **최신화 규칙은 `RECORD_KEEPING.md` 에 있다. 팀원 전원 적용.**

최종 갱신: 2026-09-03 15:31 · 갱신자: 오케스트레이터

## 지금 상태 한 줄

계약 v3.0(팀 API 명세서 v1.0 + 데이터 모델 v3.0 기준) 구현 완료. **pytest 30 · 라이브 E2E 64/64 · FE 9화면 실연동 확인.** 미커밋.

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

## 실측 증거 (이 숫자만 발표에 쓴다)

| 항목 | 값 | 원본 |
|---|---|---|
| 백엔드 단위·통합 테스트 | **30 passed** | `02_evidence/test_results/pytest_*.log` |
| 라이브 E2E (실 uvicorn 상대) | **64 통과 / 0 실패** | `02_evidence/test_results/e2e_live_v3_*.log` |
| 프론트 빌드 | 성공 · 223.58 kB (gzip 81.73 kB) | `02_evidence/test_results/fe_build_*.log` |
| 화면 | 9종 (공통2·엔지니어5·안전관리자2) | `02_evidence/screenshots/` |
| API | 15개 (OpenAPI 12 paths / 15 operations) | `docs/07_api/openapi.yaml` |
| ERD | 8테이블 · 1:N 8개 · **N:M 0개(Phase 2)** | `docs/06_erd/` |
| 에러 코드 | 23종 전부 커버 | `docs/CONTRACT.md` §6 |

> ⚠️ **v1.0 시절 수치(pytest 8/8, E2E 35/35)는 무효다.** 검증 대상이 바뀌었다.

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
