# ReplaceFlow Backend (FastAPI)

반도체 설비 부품 교체 승인 프로세스 에이전트 — BE. 계약: `../docs/CONTRACT.md` (상태값·엔드포인트·JSON 필드명 고정).

## 실행

> **Python 3.10 이상 필수.** 모델이 `Mapped[str | None]` (PEP 604)를 쓴다.
> 3.9 이하에서는 SQLAlchemy 가 `MappedAnnotationError` 를 던지며 기동하지 않는다.

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
python -V                       # 3.10 이상 확인
cp .env.example .env            # 기본: SQLite, AI_PROVIDER=MOCK, EGRESS_ALLOWED=false
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Swagger: http://localhost:8000/docs   (FE dev server localhost:5173 CORS 허용)
```

기동 시 테이블 생성 + `docs/CONTRACT.md` 샘플 데이터 자동 시드(비어 있을 때만).

## 테스트

```bash
python -m pytest -q
```

`tests/test_flow.py`: 생성 → `POST agent-runs` 202 → `GET agent-runs` 4회(step 하나씩 DONE) → REVIEW → submit-approval(422→200) → approvals(체크리스트 미완료 409 → 완료 201 APPROVED) + 대시보드·법령 검색·ai-config.

## 구조

```
app/
  main.py                     FastAPI app, CORS, lifespan(create_all + seed), ServiceError → status code
  core/config.py              ★ Security & Config Isolation — 모든 env 값은 여기서만 읽음
  db/session.py               SQLAlchemy 2.x engine/session (SQLite ↔ PostgreSQL은 DATABASE_URL만 변경)
  models/                     ERD 14 테이블 (steps_json/checklist_json/spec/substances = JSON 컬럼)
  schemas/                    Pydantic v2 — CONTRACT JSON 필드명 그대로
  repositories/               DB 접근 (ids.py: WR-YYYYMMDD-NNN / RUN-NNNN / AP-NNNN / DOC-NNNN)
  services/
    orchestrator.py           AgentOrchestrator: run 생성(4 PENDING) · advance() (GET마다 1 step DONE) · BackgroundTasks 변형
    work_request_service.py   생성/목록/상세/submit-approval(422/409)/complete
    approval_service.py       상태머신 + 체크리스트 게이트(409)
    dashboard_service.py      KPI (평균 승인시간 vs As-Is 168h)
    agents/base.py            AgentService 인터페이스 run(context) -> dict
    agents/mock_agents.py     Spec/Legal/SafetyDoc/Vendor Mock (CONTRACT 고정 결과, documents·legal_findings row 생성)
    agents/llm_agents.py      LLM(+RAG) 구현 자리 — NotImplementedError + TODO, 프롬프트는 docs/05_ai_ready/prompts.md
  api/v1/routers/             엔드포인트 (CONTRACT status code 고정)
  seed.py                     샘플 데이터
```

## 설정 (.env)

| 키 | 기본 | 설명 |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./replaceflow.db` | Supabase: `postgresql+psycopg2://...` (`psycopg2-binary` 설치) |
| `AI_PROVIDER` | `MOCK` | `MOCK` / `LOCAL_LLM` / `AX_PLATFORM` / `OPENAI` |
| `EGRESS_ALLOWED` | `false` | 외부 provider(OPENAI/AX_PLATFORM)는 `true` 필요 — 아니면 기동 거부 |
| `BACKGROUND_ADVANCE` | `false` | `true`면 POST 후 BackgroundTasks가 2초 간격으로 step 진행, GET은 읽기 전용 |
| `LOCAL_LLM_URL`, `OPENAI_API_KEY` | | LLM 구현체용 |

## Mock 에이전트 동작 (CONTRACT)

`POST /work-requests/{id}/agent-runs` → 202, steps 4개 `PENDING`, work_request `RUNNING`.
`GET /agent-runs/{runId}` 호출마다 SPEC → LEGAL → SAFETY_DOC → VENDOR 순으로 1개씩 `DONE`.
4개 완료 시 `overall_status=REVIEW`, work_request `REVIEW`. SAFETY_DOC은 `documents` row(WORK_PERMIT/RISK_ASSESSMENT)를, VENDOR는 RFQ row를 실제 생성 → `GET /documents/{docId}`.

승인: `PENDING_APPROVAL`에서만. `APPROVE`는 체크리스트 4항목(`WORK_PERMIT`, `RISK_ASSESSMENT`, `LOTO_GAS_ISOLATION`, `GAS_DETECTOR_CHECK`) 모두 `true`가 아니면 409. `REJECT`→`REJECTED`, `REQUEST_INFO`→`REVIEW`.
