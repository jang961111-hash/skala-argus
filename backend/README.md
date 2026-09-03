# ReplaceFlow Backend (FastAPI)

부품 교체 요청·승인 시스템 (REQ-F-0001) — BE.
계약: `../docs/CONTRACT.md` **v3.0** (Enum·엔드포인트·필드명·에러 코드 고정). 계약과 다르면 계약이 맞다.

## 실행

> **Python 3.10 이상 필수.** 모델이 `Mapped[str | None]` (PEP 604)를 쓴다.
> 3.9 이하에서는 SQLAlchemy 가 `MappedAnnotationError` 를 던지며 기동하지 않는다.

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
cp .env.example .env            # SECRET_KEY 를 반드시 바꿀 것
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8810
# Swagger: http://localhost:8810/docs   (FE dev server localhost:5173 CORS 허용)
```

기동 시 테이블 생성 + 데모 시드(비어 있을 때만). 시드 계정 2개 모두 비밀번호는 `Passw0rd!` 다.

| 이메일 | 역할 | 로그인 후 이동 |
|---|---|---|
| `engineer@replaceflow.test` | `ENGINEER` | `/home` |
| `safety@replaceflow.test` | `SAFETY_MANAGER` | `/manage/requests` |

시드는 6개 상태(`DRAFT`·`AI_RUNNING`·`AI_DONE`·`PENDING`·`APPROVED`·`REJECTED`)를 각 1건씩 만든다.

## 테스트

```bash
python -m pytest -q
```

- `tests/test_auth.py` — signup 201/400(`VALIDATION_FAILED`·`PASSWORD_MISMATCH`)/409, login 200/401,
  만료·위조 토큰 구분, 미인증 401, `password_hash` 미노출, **오류가 항상 `{code,message,fieldErrors?}` 인지**
- `tests/test_flow.py` — DRAFT → PATCH → `POST /agent-runs` → 폴링 3회 → `AI_DONE` → 결과 전체치환 편집
  → submit-approval(422) → 승인/거절(400·403·409) → 재제출 → 승인, 권한 분리, 목록 페이징·정렬·다중 status,
  사진(400·409·413·EXIF 제거·썸네일), 스펙 스키마, `request_no` 채번

## 구조

```
app/
  main.py                     FastAPI app, CORS, lifespan, **단일 에러 포맷 핸들러 4종**
  core/config.py              ★ Security & Config Isolation — 모든 env 값(SECRET_KEY 포함)은 여기서만 읽음
  core/enums.py               도메인 Enum (CONTRACT §2) — 모델과 스키마가 공유
  core/errors.py              ErrorCode 18종 + AppError + 코드↔status 매핑 (CONTRACT §6)
  core/security.py            bcrypt 해시 + HS256 JWT (만료/위조를 각각의 코드로 구분)
  db/session.py               SQLAlchemy 2.x engine/session (SQLite ↔ PostgreSQL 은 DATABASE_URL 만 변경)
  db/types.py                 UUID PK · jsonb · PostgreSQL enum 의 이식용 타입
  models/                     **테이블 7개** — users, work_requests, work_request_photos,
                              agent_runs, agent_steps, agent_results, approvals
  schemas/base.py             CamelModel(alias_generator) + KST 오프셋 직렬화
  schemas/                    Pydantic v2 — 응답은 전부 camelCase
  repositories/               DB 접근. request_no.py 는 채번 + UNIQUE 충돌 재시도
  api/deps.py                 get_current_user / require_engineer / require_safety_manager
  api/v1/routers/             엔드포인트 15개
  services/
    auth_service.py           signup(409) / login(401) / redirectPath 결정
    work_request_service.py   생성(draft)·목록(권한 스코프)·상세·부분수정·제출 검증 4종
    agent_service.py          run 생성 · step 진행 · **결과 전체치환 편집**
    approval_service.py       승인/거절 — 사유 10자 검증, append-only 이력
    dashboard_service.py      역할별 KPI (토큰 역할 불일치 403)
    photo_service.py          EXIF 제거 + 320px 썸네일, 형식·용량·개수 검증
    agents/base.py            ★ AgentService 인터페이스 run(context) -> payload
    agents/mock_agents.py     A1 규격·호환 / A2 법령·조문 / A3 안전서류 Mock
    agents/llm_agents.py      LLM(+RAG) 구현 자리 — NotImplementedError + TODO
    agents/__init__.py        ★ get_agent() 팩토리 — Mock ↔ LLM 교체 지점
  seed.py                     데모 시드
```

## 설정 (.env)

| 키 | 기본 | 설명 |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./replaceflow.db` | Supabase: `postgresql+psycopg2://...` (`psycopg2-binary` 설치) |
| `SECRET_KEY` | (개발용 기본값) | JWT 서명 키. **운영 배포 전 반드시 교체** — 기본값이면 기동 시 경고 |
| `TOKEN_TTL_HOURS` | `72` | 액세스 토큰 유효시간 |
| `AI_PROVIDER` | `MOCK` | `MOCK` / `LOCAL_LLM` / `AX_PLATFORM` / `OPENAI` |
| `EGRESS_ALLOWED` | `false` | 외부 provider(OPENAI/AX_PLATFORM)는 `true` 필요 — 아니면 기동 거부 |
| `BACKGROUND_ADVANCE` | `false` | `true` 면 POST 후 BackgroundTasks 가 step 을 진행시키고 GET 은 읽기 전용 |
| `UPLOADS_DIR` | `uploads` | 사진 저장 경로 (`backend/` 기준, `.gitignore` 대상) |
| `MAX_UPLOAD_BYTES` · `MAX_PHOTOS_PER_REQUEST` · `THUMBNAIL_PX` | `10485760` · `5` · `320` | 사진 제약 |
| `POLL_INTERVAL_MS` | `2500` | 폴링 응답에 실어 보내는 권장 주기 |
| `LOCAL_LLM_URL`, `OPENAI_API_KEY` | | LLM 구현체용 |

## 계약에서 놓치기 쉬운 지점

**경로** — `POST /agent-runs` 와 `POST /approvals` 는 **최상위 경로**이고 body 에 `workRequestId` 를 담는다.
`/work-requests/{id}/agent-runs` 형태가 아니다. `/complete` 엔드포인트는 없다(`DONE` 상태가 없다).

**에러** — 모든 4xx·5xx 가 `{code, message, fieldErrors?}` 다. FastAPI 기본 `{"detail": ...}` 는 나가지 않는다.
Pydantic 검증 실패는 **400 `VALIDATION_FAILED`** 로 내려간다 — 계약의 유일한 422 는 `SUBMIT_REQUIRED_FIELD_MISSING` 이다.

**ID** — 대리키는 UUID v4, 화면에 보이는 번호는 `requestNo`(`WR-YYYYMMDD-NNN`, 서버 채번, UNIQUE)로 분리돼 있다.

**Mock 에이전트** — `POST /agent-runs` → 202, step 3개가 전부 `WAITING`.
`GET /agent-runs/{runId}` 호출마다 A1 → A2 → A3 순으로 하나씩 `DONE`.
3개 완료 시 `allDone:true`, run 은 `DONE`, work_request 는 `AI_DONE` 으로 전환된다.
step 이 실패하면 **HTTP 는 200 을 유지**하고 해당 step 만 `FAILED` + `errorMessage` 다.
**GET 이 상태를 바꾸는 것은 Mock 단계의 의도된 설계이며 `BACKGROUND_ADVANCE=true` 로 끌 수 있다.**

**결과 편집** — `PATCH /agent-results/{id}` 는 부분 수정이 아니라 **전체 치환**이다.
배열에 없는 기존 `itemId`/`docId` 는 삭제되고, id 없이 온 항목은 신규 추가로 보고 서버가 채번한다.
항목별 `edited` 는 클라이언트 값을 믿지 않고 **AI 원본(`agent_results.original_json`)과 대조해 서버가 판정**한다.

**제출 검증 4가지** — ①A1·A2·A3 결과 전부 존재 ②`engineerNote` 비어 있지 않음 ③A2 적용 법령 1건 이상
④상태가 `AI_DONE` 또는 `REJECTED`. 하나라도 어긋나면 422 `SUBMIT_REQUIRED_FIELD_MISSING` 이고
어떤 항목이 걸렸는지는 `fieldErrors` 에 실린다.

**권한** — `ENGINEER` 는 본인 요청만, `SAFETY_MANAGER` 는 `PENDING` 이상만 본다(위반 403).
안전관리자가 상세를 조회하면 `agentRun.results[].editable` 은 언제나 `false` 다.

## FE 정합 (`frontend/src/constants/domain.js` 와 맞춘 지점)

- **`nextAction`** 값은 `CONTINUE` · `RUN` · `RESULT` · `DETAIL` 이다(FE `NEXT_ACTION` 과 동일 어휘).
- **엔티티 자신의 id 는 `id` 와 한정명 두 키로 모두 나간다** — `id`+`workRequestId`, `id`+`runId`,
  `id`+`agentResultId`, `id`+`approvalId`, `id`+`photoId`, `id`+`userId`.
  계약 §1 은 한정명을 예시로 들고 FE 는 `id` 를 쓰기 때문에 둘 다 낸다. 한쪽으로 확정되면 지우면 된다.
- **`draft` 는 쿼리스트링(`?draft=true`)과 body(`{"draft": true}`) 둘 다 받는다.**
- **상세 응답에 `photos` 가 포함된다**(FE `toDetail` 이 `wr.photos` 를 읽는다).
- 사진 응답에 `originalUrl` · `thumbnailUrl` 이 있고 `/uploads` 정적 마운트가 서빙한다.
  계약의 API 15개에 이미지를 내려받을 경로가 없어 정적 마운트로 메운 것이다 — 팀 확인이 필요하다.
  Vite dev proxy 에 `/uploads` 도 추가해야 화면에서 뜬다.
- 남은 차이 하나: **안전관리자 목록 범위.** 계약 §1 은 "PENDING 이상"이라 BE 는 `PENDING`·`APPROVED`·`REJECTED`
  만 보여준다. FE Mock 은 `DRAFT` 만 제외해 `AI_RUNNING`·`AI_DONE` 도 보인다 — 실서버에서는 403 이 난다.

`tests/test_flow.py::test_fe_contract_alignment` 가 위 항목을 고정한다.

## Phase 2 (이번 범위 아님)

A1 부품 마스터·호환표 연동, **A4 벤더 에이전트**, 법령 인덱스(RAG), `ai_configs` 테이블,
SSE/WebSocket 폴링 대체. 설비·라인·물질은 지금은 `work_requests` 의 varchar 컬럼이다.
