# 발표 당일 데모 런북

담당: DevOps & Infra 신서현 · 작성 2026-09-03 (Day 2) · 발표 2026-09-04 15:00
리허설: 내일 13:00 · 14:00 · 14:40 — **이 문서가 그 리허설의 대본이다.**

> `docs/09_qa/devops_report.md` 는 개발자용(예행·재현 절차). 이 문서는 **발표 직전, 긴장한 상태에서 한 줄씩 그대로 치는 용도**다. 판단하지 말고 순서대로 친다.

---

## 0. 시작 전 1회 확인 (발표 30분 전)

```bash
cd ~/projects/argus
git status --porcelain --branch          # main 이고 clean 인지만 본다 — 여기서 뭘 고치지 않는다
bash --version | head -1                  # 3.2 면 §5 함정 참고
python3 --version                         # 3.9 면 §5 함정 참고
```

실제 로컬 `.env` 확인 — **DB 파일명이 노트북마다 다를 수 있다** (이 세션 실측에서 `backend/.env` 가 표준값 `argus.db` 대신 BE 담당이 개발 중 쓰던 `be_v3_dev.db` 로 남아있는 걸 발견해서 팀장이 표준값으로 정리했다):
```bash
grep DATABASE_URL backend/.env
```
`sqlite:///./argus.db` 로 나오는지 확인한다. 다르게 나오면 §3을 그대로 치지 말고 §2 안내대로 먼저 알린다 — 와일드카드로 임의 삭제하지 않는다.

---

## 1. 기동 순서 — BE(8000) → FE(5173)

**측정 방법 고지**: 8000·5173 포트는 다른 팀원 프로세스가 상시 점유 중이라 이 세션에서는 대체 포트(8832/5183/5184)로 동일 코드 경로를 실측했다. 기동 지연은 포트 번호와 무관(같은 바이너리·같은 시드 로직)하므로 아래 수치는 실제 8000/5173에도 그대로 적용된다.

### ① 백엔드 먼저
```bash
cd ~/projects/argus/backend
source .venv/bin/activate               # 안 되어 있으면: python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
**대기**: 로그에 `Application startup complete` 뜨면 준비된 것. 실측 **약 0.8초** (헬스 엔드포인트가 401 아닌 000 이 아니게 되는 시점 기준 — 401은 정상, "토큰 없음"일 뿐 서버는 응답 중이란 뜻).

확인 명령 (새 터미널):
```bash
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8000/api/v1/dashboard/summary?role=engineer
# 401 이 나오면 OK (서버는 살아있고 인증만 요구하는 것). 000/커넥션거부면 아직 안 뜬 것 — 2~3초 더 기다린다
```

### ② 프론트엔드
```bash
cd ~/projects/argus/frontend
npm run dev
```
**대기**: 터미널에 `VITE vX.X.X ready in NNN ms` 뜨면 준비된 것. 실측 **255~310ms** (vite 자체 기준. npm 래퍼 포함 실측 체감 1초 이내).

확인: 브라우저로 `http://localhost:5173` 열어서 로그인 화면이 뜨는지 눈으로 본다.

**총 소요**: BE 기동 시작부터 FE 로그인 화면까지 **넉넉잡아 5초** 안에 끝난다. 5초 넘게 아무것도 안 뜨면 §5 사고 대응으로 간다.

---

## 2. 데모 계정

| 역할 | 이메일 | 비밀번호 | 로그인 후 이동 |
|---|---|---|---|
| 엔지니어 | `engineer@argus.test` | `Passw0rd!` | `/home` |
| 안전관리자 | `safety@argus.test` | `Passw0rd!` | `/manage/requests` |

이 세션에서 실제 로그인 API(`POST /auth/login`)로 두 계정 다 실측 확인 완료(200, accessToken 발급).

**`.env`의 `DATABASE_URL`이 `argus.db`가 아니면 §3의 리셋 명령이 안 먹는다.** 먼저 확인:
```bash
cat backend/.env | grep DATABASE_URL
```
`sqlite:///./argus.db` 가 아니면 리셋 전에 팀장(또는 BE 담당)에게 알리고 파일명을 맞춰라 — 와일드카드로 임의 삭제하지 않는다(§3 참고).

---

## 3. 시연 전 리셋 (두 번째 데모를 위해)

**명령**:
```bash
# BE 서버를 Ctrl+C 로 먼저 내린다 (파일이 열려 있는 상태로 지우면 다음 기동 때 꼬일 수 있다)
rm -f backend/argus.db
uvicorn app.main:app --reload --port 8000    # backend/ 안에서, venv 활성화 상태로
```
와일드카드(`*.db`)를 안 쓴다 — `docs/10_project_record/RECORD_KEEPING.md` 금지 항목(사고 I-08, 공유 DB를 와일드카드로 날린 전례)에 따라 삭제 명령엔 파일명을 명시한다. `.env`는 표준값(`argus.db`)으로 정리되어 있다(팀장 조치 완료, 재기동 후 6상태 6건 재시드 확인됨).

**실제로 해보고 확인한 것**: 새 DB 파일로 기동하면 `seed_if_empty()` 가 자동으로 시드를 채운다 — **작업요청 6건, 상태 6종류 각 1건**(`DRAFT`·`AI_RUNNING`·`AI_DONE`·`PENDING`·`APPROVED`·`REJECTED`)씩 정확히 재생성되는 것을 이 세션에서 sqlite3로 직접 카운트해 확인했다. 사용자도 엔지니어·안전관리자 2명 그대로 재생성된다. **재시드는 기동 시 자동이라 별도 명령이 필요 없다** — DB 파일만 지우면 된다.

리셋 자체는 사실상 즉시(1초 미만) + 위 §1의 BE 재기동 시간(~1초)만큼만 걸린다.

---

## 4. 실패 시 3단 폴백

시연 중 BE/FE 연동이 막히면 아래 순서로 전환한다. **순서를 지킨다 — 갑자기 3번(캡처)으로 건너뛰지 말고 1→2→3 순서로 시도하되, 리허설 때 정한 시간 제한을 넘기면 다음 단계로 넘어간다.**

### ① FE 단독 Mock (권장 1차 폴백)
```bash
cd frontend
npm run dev:mock            # 또는: VITE_USE_MOCK=true npm run dev
```
BE 없이 `src/mock/data.js` 인메모리 데이터로 화면이 그대로 동작한다(계약 형태 동일). **실측 전환 시간: 1초 미만** (vite 재기동 300ms 수준 + 브라우저 새로고침). 이미 떠 있는 FE를 Ctrl+C 하고 위 명령으로 다시 띄우면 된다.

### ② Postman Mock
`postman/Argus.postman_collection.json` + `postman/Argus.postman_environment.json`(환경명 `Argus Local (v3.0)`) 을 Postman 에서 열어 API 단위로 시연한다. FE 화면 대신 "이 요청을 서버가 이렇게 처리한다"를 API 레벨로 보여주는 최후 수단 — **Postman 이 이미 열려 있고 컬렉션이 임포트된 상태를 발표 전에 미리 만들어 둘 것** (당일 임포트하면 수십 초 걸린다. 사전 준비하면 전환 즉시).

### ③ 캡처 9장
`docs/10_project_record/02_evidence/screenshots/argus_WRA_*.jpg` — 로그인(C_00)부터 엔지니어 5화면(E_01~E_05)·안전관리자 2화면(S_01~S_02) 까지 이미 실연동 상태로 캡처되어 있다(오늘 날짜, `v1.0_*` 접두는 구버전이니 쓰지 말 것). 슬라이드나 Preview 앱으로 순서대로 넘기면서 설명. **전환 시간: 폴더 열기 수 초** — 발표 노트북에 미리 슬라이드로 박아두면 0초.

**폴백 전환 총정리**: ①까지는 1초 내 복구 가능한 수준이라 사실상 실패로 안 느껴지게 넘어갈 수 있다. ②·③은 "지금부터는 Mock/캡처로 보여드리겠습니다" 라고 말로 전환을 알리는 게 낫다(속도보다 진행 매끄러움).

---

## 5. 흔한 사고 복구 (한 줄)

| 사고 | 복구 명령 |
|---|---|
| 포트 8000 점유 | `lsof -ti:8000 \| xargs kill -9` |
| 포트 5173 점유 | `lsof -ti:5173 \| xargs kill -9` |
| Python 3.9 함정 (macOS 기본 `python3`) | `python3 --version` 으로 먼저 확인 — 3.9면 `backend/.venv` 를 반드시 3.10+ 로 다시 만들어야 함(당일 새로 만들 시간 없으니 사전에 끝내둘 것) |
| bash 3.2 함정 (macOS 기본 `/bin/bash`) | `scripts/e2e_live_v3.sh` 같은 데모 스크립트를 쓸 계획이면 `bash --version` 먼저 확인 — 3.2면 빈 배열 unbound 에러 가능성(발표 스크립트 자체는 이 문제 없음, 데모 중 E2E 스크립트를 직접 돌릴 계획이 아니면 무시 가능) |
| npm 캐시 없음 (새/초기화된 노트북) | `cd frontend && rm -rf node_modules && npm ci` (오프라인이면 다른 팀원 `node_modules` 를 tar 로 복사) |
| `.env` 파일 없음 | `cd backend && cp .env.example .env` |
| DB 꼬임(위 §3 리셋으로도 해결 안 될 때) | `rm -f backend/argus.db && rm -rf backend/uploads` 후 재기동 (와일드카드 금지 — 위 §3 참고) |

---

## 6. 금지 사항 (발표 중)

- ❌ **`git` 명령 치지 말 것** — `git status` 확인도 발표 시작 전(§0)까지만. 발표 중 커밋·체크아웃·머지는 절대 금지(화면 공유 중 충돌 나면 복구 시간이 없다)
- ❌ **브랜치 바꾸지 말 것** — `main` 에 이미 최종본이 머지되어 있다. `git checkout` 자체를 안 친다
- ❌ CI(GitHub Actions) 페이지를 열어서 실시간으로 보여주려 하지 말 것 — 네트워크 의존적이고 느리다. CI 결과는 `docs/09_qa/devops_report.md` 캡처나 숫자로 말로 전달
- ❌ `npm install` / `pip install` 을 발표 중에 새로 돌리지 말 것 — 네트워크 문제 시 그대로 멈춘다. 필요한 건 발표 전에 다 깔아둔다(§0)
- ❌ 리셋(§3) 중간에 서버를 Ctrl+C 안 하고 DB 파일부터 지우지 말 것 — 파일 핸들이 열린 채로 지우면 다음 기동 때 SQLite 락 에러가 날 수 있다. 반드시 "서버 종료 → 파일 삭제 → 재기동" 순서

---

## 요약

- BE 기동 ~0.8초, FE 기동 ~0.3초(vite 자체 기준) — 총 5초 안에 로그인 화면까지 실측
- 데모 계정 2개(engineer/safety, `Passw0rd!`) 실제 로그인 API로 확인 완료
- 리셋은 `rm -f backend/argus.db` 후 재기동 1회(와일드카드 금지, RECORD_KEEPING 사고 I-08 대응), 6상태 6건 자동 재시드를 이 세션에서 sqlite3 직접 카운트로 확인
- 3단 폴백: FE Mock(<1초) → Postman Mock(사전 준비 시 즉시) → 캡처 9장(`docs/10_project_record/02_evidence/screenshots/argus_WRA_*.jpg`, 오늘 실연동 캡처)
- 로컬 `.env` 의 `DATABASE_URL` 이 팀원마다 다를 수 있음을 실측으로 발견(`argus.db` 아닌 `be_v3_dev.db`) — 팀장이 표준값으로 정리 완료, 런북엔 리셋 전 확인 절차(§2)로 대응
- git 명령·브랜치 전환·CI 페이지·재설치는 발표 중 전부 금지
