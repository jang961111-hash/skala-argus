# 인수인계 — 다음 세션이 여기서 이어받는다

> **이 파일 하나만 읽으면 작업을 이어갈 수 있어야 한다.**
> 대화 맥락이 끊겨도(컨텍스트 압축·세션 교체) 여기서 재개한다.
> 최종 갱신 2026-09-03 17:10

---

## 0. 30초 요약

**Argus** — 반도체 설비 부품 교체 승인 에이전트. SKALA 4기 Full-Stack Engineering 미니프로젝트(광주 2반 5조).
**발표 2026-09-04(금) 15:00. 산출물 제출 마감 14:30(하드 마감, 이후 수정 불가).**

구현·문서·검증·커밋 **전부 완료**. 남은 건 **사람 손이 필요한 것들**뿐이다.

```
pytest 30 passed · 라이브 E2E 72/72 · FE 빌드 223.88 kB
커밋 38 · 브랜치 12 · 파일 172
```

---

## 1. 좌표

| 항목 | 값 |
|---|---|
| 로컬 | `~/projects/argus` |
| GitHub | https://github.com/jang961111-hash/skala-argus (public) |
| 계약(단일 진실 원천) | `docs/CONTRACT.md` **v3.0** |
| 기록·회고 | `docs/10_project_record/` |
| 최신화 규칙 | `docs/10_project_record/RECORD_KEEPING.md` |
| 발표 당일 절차 | `docs/09_qa/demo_runbook.md` |
| 노션(총감독 확인용) | https://app.notion.com/p/3d0a7f29102a812cbafee720e548f73c |
| 발표 덱(16장) | https://claude.ai/code/artifact/3e87efca-2f9c-4338-806b-07891c2093fa |
| Stitch 프롬프트 패키지 | https://claude.ai/code/artifact/dca86dbb-252a-4a21-950d-aad64d4a446f |

**데모 계정** `engineer@argus.test` / `safety@argus.test` · 비밀번호 `Passw0rd!`

---

## 2. 이것부터 읽어라 (순서대로)

1. `docs/CONTRACT.md` — 계약 v3.0. **팀 노션 원본을 옮긴 것이며, 원본과 다르면 원본이 맞다**
2. `docs/10_project_record/01_timeline/decision_log.md` — 결정 11건과 번복 이유
3. `docs/10_project_record/01_timeline/incident_log.md` — 사고 9건. **같은 실수를 반복하지 않으려면 필수**
4. `docs/09_qa/self_review_rubric.md` — 루브릭 73항목 현재 판정

---

## 3. 남은 일 — 전부 사람 손

| 담당 | 항목 | 상태 |
|---|---|---|
| 장병헌 | **Stitch 와이어프레임** — 프롬프트 9개 준비됨 | 🔄 진행 중 |
| 장병헌 | **Supabase** 생성 + `docs/06_erd/schema_postgres.sql` 실행 | ⏳ `supabase_apply.md` 절차대로 |
| 은태현 | 발표 슬라이드 — **덱 16장 초안 있음**, 검토·보완 | 🔄 |
| 전원 | 회고 §3·§4 — **5인 초안 있음**, 본인이 고칠 것 | ⏳ |
| 전원 | 리허설 3회 (9/4 13:00 / 14:00 / 14:40) | ⏳ |
| 전원 | 타 조 질의 1개 — **후보 A 추천 확정** | ⏳ 제출만 |

---

## 4. 아직 열려 있는 판단

- **N:M 0개** — 루브릭 30점이 "1:N, N:M"을 요구하는데 v3.0 범위엔 없다.
  대응은 `docs/06_erd/erd.md`의 1:N 8개 표 + "왜 없는가" + `erd_phase2.svg`(Phase 2 연결 테이블 3종).
  **실제로 하나 넣을지는 미결.** 넣으면 시드·E2E·문서가 연쇄로 바뀐다
- **PR 0건 / 이슈 0건** — 브랜치는 이미 병합돼 지금 PR을 열면 빈 diff다. 방식 조정이 필요

---

## 5. 밟으면 아픈 함정 (실제로 다 밟았다)

| 함정 | 증상 | 대응 |
|---|---|---|
| **Python 3.9** | 백엔드가 기동조차 안 됨 (`MappedAnnotationError`) | `python3.11 -m venv .venv`. macOS 기본 `python3`은 3.9다 |
| **bash 3.2** | E2E가 `unbound variable`로 죽음 | 빈 배열은 `${arr[@]+"${arr[@]}"}` |
| **포트 잔재** | E2E가 이전 서버에 붙어 대량 실패 | 스크립트에 포트 해제 대기 있음. 그래도 이상하면 `lsof -ti:8820 \| xargs kill -9` |
| **`.env` 불일치** | "리셋했는데 데이터가 그대로" | `grep DATABASE_URL backend/.env` — `argus.db`여야 한다 |
| **와일드카드 삭제 금지** | 남의 DB를 날림 (사고 I-08) | 파일명을 명시한다 |
| **증거 로그 편집 금지** | 캡처된 증거를 고치면 증거가 아니다 | 지우고 재수집(`collect_evidence.sh`) |

---

## 6. 재현

```bash
cd ~/projects/argus/backend
python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q          # 기대: 30 passed

cd .. && bash scripts/e2e_live_v3.sh   # 기대: 72 통과 / 0 실패
bash scripts/collect_evidence.sh       # 증거 일괄 재수집

# 화면 (BE 8000 + FE 5173)
cd backend && .venv/bin/python -m uvicorn app.main:app --port 8000 &
cd frontend && npm install && npm run dev -- --port 5173
```

---

## 7. 일하는 방식 (이 팀이 합의한 것)

- **계약이 먼저.** `CONTRACT.md`를 고치는 건 오케스트레이터만. 트랙은 변경을 **요청**한다
- **파일 소유권 비중첩.** 담당이 아닌 경로는 읽기만 하고, 어긋난 걸 발견하면 **고치지 말고 보고**한다
- **숫자는 실측만.** 돌려본 명령의 출력을 원본 로그로 남기고 그 숫자만 인용한다
- **모르면 "미검증"이라고 쓴다.** 억지로 통과 표시하는 것보다 100배 낫다 — 실제로 이 습관이 사고 I-09를 잡았다
- **번복은 덮어쓰지 않고 추가**한다. 왜 바뀌었는지가 회고의 재료다
- 커밋은 팀장 계정 통합. **커밋 본문에 담당 역할·이름 + 계약 조항 번호**를 넣는다

---

## 8. 발표에서 말하면 안 되는 것

- ❌ "각자 계정으로 커밋했다" → `git shortlog -sn`이 1인이다
- ❌ "DB 연동 완료" → Supabase는 **미검증**이다
- ❌ 근거 없는 성능 수치 → 대시보드의 84% 단축은 **시드 데이터 기준 시연값**이다
- ❌ 에이전트 4종 / 체크리스트 409 / 화면 2개 → 전부 v1.0 시절 이야기다
