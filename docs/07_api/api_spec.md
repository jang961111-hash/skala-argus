# ReplaceFlow REST API 명세 (발표용)

- Base URL: `http://localhost:8000/api/v1` (Mock: Postman Mock Server, 컬렉션 `postman/ReplaceFlow.postman_collection.json`)
- 형식: JSON (UTF-8), 시각은 ISO-8601 + 오프셋(`+09:00`)
- 인증: `Authorization: Bearer <JWT>` — 클레임 `role` (ENGINEER / SAFETY_MANAGER / BUYER / ADMIN). PoC 는 Mock 토큰.
- 기계 판독 명세: [`openapi.yaml`](./openapi.yaml) (OpenAPI 3.0.3, `redocly lint` 통과)
- 오류 응답은 전 엔드포인트 공통 `Error` 스키마: `{ "code": "…", "message": "…", "details": {…} }`

## 1. 엔드포인트 요약

| # | Method | Path | 설명 | 요청 | 응답(성공) | 상태코드 | 주 사용자 |
|---|---|---|---|---|---|---|---|
| 1 | GET | `/work-requests` | 작업요청 목록 (화면1 테이블) | query `status`, `page`, `size` | `{ items: [WorkRequestSummary], total, page, size }` | 200 · 401 · 422 | 전체 |
| 2 | POST | `/work-requests` | 작업요청 생성 (UC-01) | `WorkRequestCreate` `{equipment_id, part_id, symptom, site_check_note, requested_by}` | `WorkRequest` (status=`REQUESTED`) + `Location` | **201** · 401 · 422 | 엔지니어 |
| 3 | GET | `/work-requests/{id}` | 상세 = 요청 + `latest_run` + `approvals` (화면2 초기 로딩) | path `id` | `WorkRequestDetail` | 200 · 401 · 404 | 전체 |
| 4 | POST | `/work-requests/{id}/agent-runs` | **에이전트 실행 시작 (비동기)** (UC-02) | path `id`, body 없음 | `{ run_id, overall_status: "RUNNING" }` + `Location`, `Retry-After: 3` | **202** · 401 · 404 · **409**(이미 APPROVED/DONE) | 엔지니어/시스템 |
| 5 | GET | `/agent-runs/{runId}` | **실행 상태·결과 (폴링)** | path `runId` | `AgentRun` (steps 4개 상태·결과) | 200 · 401 · 404 | FE 타임라인 |
| 6 | PATCH | `/work-requests/{id}/submit-approval` | 승인 요청 제출 REVIEW → PENDING_APPROVAL (UC-03) | `{ missing_info: {누락항목명: 값}| `WorkRequest` (status=`PENDING_APPROVAL`) | 200 · 401 · 404 · **409**(run 미완료) · **422**(누락 정보) | 엔지니어 |
| 7 | POST | `/work-requests/{id}/approvals` | 승인/반려/보완요청 (UC-04) | `ApprovalCreate` `{approver_id, decision, checklist{4}, comment}` | `Approval` | **201** · 401 · 404 · **409**(체크리스트 미완료 APPROVE) · 422 | 안전관리자 |
| 8 | GET | `/documents/{docId}` | 서류 초안 (작업허가서·위험성평가·LOTO·RFQ) | path `docId` | `Document` `{doc_id, type, body(md), missing[], version}` | 200 · 401 · 404 | 전체 |
| 9 | GET | `/parts/{partId}/compatibility` | 부품 호환표 | path `partId` | `{ part: Part, alternatives: [{part_no, grade, diff, allowed_for_toxic_gas}] }` | 200 · 401 · 404 | 엔지니어/구매 |
| 10 | GET | `/laws/search` | 법령 인덱스 검색 (사내 사전 적재) | query `q`, `equipmentType`, `substance` | `{ items: [LawArticle], total }` | 200 · 401 · 422 | 안전관리자/에이전트 |
| 11 | GET | `/dashboard/summary` | KPI (UC-06) | — | `DashboardSummary` | 200 · 401 | 관리자 |
| 12 | GET | `/tenants/{id}/ai-config` | 에이전트별 AI 설정 조회 | path `id` | `[AiConfig]` | 200 · 401 · 404 | 관리자 |
| 13 | PUT | `/tenants/{id}/ai-config` | AI 설정 전체 교체(멱등) | `[AiConfig]` | `[AiConfig]` | 200 · 401 · 404 · 422 | 관리자 |
| 14 | GET | `/equipments` | 설비 목록 | — | `[Equipment]` | 200 · 401 | 전체 |
| 15 | GET | `/parts` | 부품 목록 | — | `[Part]` | 200 · 401 | 전체 |

## 2. 상태 머신과 API 의 대응

```
REQUESTED ──(4) POST agent-runs 202──▶ RUNNING ──(5) 폴링 4/4 DONE──▶ REVIEW ──(6) PATCH submit-approval 200──▶ PENDING_APPROVAL
                                                                                  ▲                                   │
                                                                                  │ REQUEST_INFO                       │ (7) POST approvals 201
                                                                                  └───────────────────────────────────┼──▶ APPROVED ──(UC-05 작업 완료)──▶ DONE
                                                                                                                      └──▶ REJECTED
```
| 전이 | API | 실패 조건 |
|---|---|---|
| REQUESTED → RUNNING | #4 | APPROVED/DONE 이면 409 `INVALID_STATE` |
| RUNNING → REVIEW | #5 (서버 내부; Mock 은 폴링 4회) | step FAILED → `overall_status=FAILED`, 요청은 REQUESTED 로 복귀 |
| REVIEW → PENDING_APPROVAL | #6 | run 미완료 409 `RUN_NOT_COMPLETED` / 서류 missing 잔존 422 `MISSING_INFORMATION` |
| PENDING_APPROVAL → APPROVED/REJECTED/REVIEW | #7 | APPROVE 인데 checklist 4항목 중 false → 409 `CHECKLIST_INCOMPLETE` |

## 3. 대표 요청/응답

**#4 실행 시작 → #5 폴링**
```http
POST /api/v1/work-requests/WR-20260902-011/agent-runs
→ 202 Accepted
Location: /api/v1/agent-runs/RUN-0042
Retry-After: 3
{ "run_id": "RUN-0042", "overall_status": "RUNNING" }

GET /api/v1/agent-runs/RUN-0042        (3초 간격, RUNNING 인 동안 반복)
→ 200 { "run_id": "RUN-0042", "overall_status": "RUNNING",
        "steps": [ {"agent":"SPEC","status":"DONE","result":{…}}, {"agent":"LEGAL","status":"PENDING","result":null}, … ] }
…
→ 200 { "overall_status": "REVIEW", "steps": [4개 모두 DONE], "summary": "OEM 동일 규격 밸브 교체. …", "approval_required_by": "SAFETY_MANAGER" }
```

**#7 승인 (체크리스트 게이트)**
```http
POST /api/v1/work-requests/WR-20260902-011/approvals
{ "approver_id": "U-002", "decision": "APPROVE",
  "checklist": { "WORK_PERMIT": true, "RISK_ASSESSMENT": true, "LOTO_GAS_ISOLATION": false, "GAS_DETECTOR_CHECK": true },
  "comment": "…" }
→ 409 Conflict
{ "code": "CHECKLIST_INCOMPLETE", "message": "필수 체크리스트 4항목을 모두 확인해야 승인할 수 있습니다.", "details": { "unchecked": ["LOTO_GAS_ISOLATION"] } }
```
전체 예시 JSON 은 `openapi.yaml` 의 `components/examples` 와 Postman 저장 예시(52건)에 있다.

## 4. RESTful 설계 근거

### 4.1 리소스 명명
- **명사·복수형·kebab-case**: `/work-requests`, `/agent-runs`, `/approvals`, `/documents`, `/parts`, `/equipments`, `/laws`, `/tenants`. 동사는 HTTP 메서드가 담당한다.
- **소유 관계는 중첩 경로**: `agent-runs` 와 `approvals` 는 특정 작업요청에 종속되어 *생성*되므로 `POST /work-requests/{id}/agent-runs`, `POST /work-requests/{id}/approvals`. 반면 run 은 생성 후 독립적으로 조회·추적되므로 `GET /agent-runs/{runId}` 는 최상위에 둔다(폴링 URL 이 짧고, 나중에 run 목록/재실행 API 를 붙이기 쉬움).
- **컨트롤러 리소스 1개만 예외**: `PATCH /work-requests/{id}/submit-approval`. "승인 요청 제출"은 상태 전이 + 누락 정보 보완이 한 트랜잭션이라 `PATCH /work-requests/{id} {status: PENDING_APPROVAL}` 로 두면 클라이언트가 상태머신 규칙을 알아야 한다. 의도를 이름에 드러내는 컨트롤러 엔드포인트(REST API Design Rulebook 의 controller resource)를 채택하고, 부분 갱신 의미이므로 PATCH 를 쓴다.
- **검색은 하위 리소스 + 쿼리**: `GET /laws/search?q=&equipmentType=&substance=`. 필터가 3개 이상이고 향후 RAG 유사도 검색으로 확장될 여지가 있어 별도 경로로 분리.
- **설정은 테넌트 하위 단일 리소스**: `GET/PUT /tenants/{id}/ai-config`. 에이전트 4개 설정을 한 배열로 다루고 PUT 으로 통째로 교체(멱등) — 부분 갱신 이력이 필요 없는 관리 화면에 적합.
- **식별자는 사람이 읽는 접두어 ID**: `WR-20260902-011`, `RUN-0042`, `DOC-0101`, `AP-0007`. 감사 로그·메신저 대화에서 그대로 인용 가능(현업 요구: "메신저 왕복 대체").

### 4.2 상태코드 — 왜 202 인가
- `POST /work-requests/{id}/agent-runs` 는 4개 에이전트를 돌리는 **장기 작업**(실서비스 수십 초~분). 요청을 *접수*했을 뿐 완료된 것이 아니므로 `201 Created`(완성된 리소스) 나 `200 OK`(동기 완료) 는 의미가 틀리다. **`202 Accepted`** 가 "처리는 시작됐고 결과는 나중에" 라는 HTTP 표준 의미.
- 202 응답에 **`Location` 헤더로 상태 조회 URL**(`/agent-runs/RUN-0042`) 과 **`Retry-After: 3`** 을 실어 클라이언트가 폴링 주소·주기를 하드코딩하지 않게 한다 (RFC 7231 §6.3.3 권고 패턴).
- 그 외: 생성은 **201** + `Location` (`/work-requests`, `/approvals`), 조회·갱신은 **200**, 존재하지 않는 ID 는 **404**.

### 4.3 409 vs 422 구분 기준
| 코드 | 의미 | ReplaceFlow 적용 | 클라이언트 대응 |
|---|---|---|---|
| **422 Unprocessable Entity** | 요청 문법은 맞지만 **내용이 불충분/부적합** — 요청 본문을 고치면 해결 | `submit-approval` 시 서류 `missing` 잔존(작업자 이름 미입력), 본문 필드 검증 실패 | `details.missing` 을 폼에 표시하고 **같은 요청을 보완해 재시도** |
| **409 Conflict** | 요청 자체는 유효하지만 **리소스의 현재 상태와 충돌** — 본문을 고쳐도 안 되고 상태가 바뀌어야 함 | (a) APPROVED/DONE 에 에이전트 재실행, (b) run 미완료 상태에서 승인 요청, (c) 체크리스트 미완료 상태에서 APPROVE | 상태 새로고침 / 선행 단계(폴링 완료, 체크리스트 체크) 유도. **재시도 금지** |

한 줄 기준: *"내가 보낸 값을 바꾸면 되는가?"* → 예: 422, 아니오(리소스 상태가 바뀌어야 함): 409.
체크리스트 미완료 APPROVE 를 422 가 아닌 409 로 둔 이유: 체크리스트는 본문에 들어오지만 **승인 가능 조건(게이트)** 을 의미하며, 안전상 "값을 고쳐 재전송"이 아니라 "실제로 확인 후 체크"라는 사람의 행위가 선행돼야 하므로 상태 충돌로 해석한다(Human-in-the-loop 강조).

### 4.4 폴링 설계 (Asynchronous Pipeline)
- **패턴**: Request-Acknowledge-Poll. 202 → `GET /agent-runs/{runId}` 반복 → `overall_status ∈ {REVIEW, FAILED}` 면 중단.
- **주기 3초**: 데모 90초 시나리오(에이전트 4개가 2~3초 간격 완료)와 사람이 "살아 움직인다"고 느끼는 갱신 빈도의 절충. `Retry-After` 로 서버가 조정 가능.
- **부분 결과 노출**: 응답에 항상 steps 4개가 고정 순서(SPEC→LEGAL→SAFETY_DOC→VENDOR)로 들어 있고, 완료된 step 은 `result` 를 즉시 포함 → FE 타임라인 카드가 하나씩 채워진다. 미완료 step 은 `result:null` 이라 FE 분기가 단순하다.
- **멱등·안전**: GET 이므로 몇 번 호출해도 부작용 없음(실서버). Mock 만 "호출마다 step 1개 DONE" 으로 상태를 진행시키는데, 이는 Mock 이 시간 경과를 흉내 내는 방식이며 계약(CONTRACT)에 명시했다.
- **종료 조건과 실패**: `overall_status=FAILED` 면 실패한 step 의 `error` 를 보여주고 #4 재실행 버튼 활성화(요청은 REQUESTED 로 복귀).
- **왜 WebSocket/SSE 가 아닌가**: 3일 PoC 범위, 온프레미스 방화벽·프록시 환경에서 가장 단순하고 확실한 방식. 확장 시 `GET /agent-runs/{runId}` 는 그대로 두고 SSE(`/agent-runs/{runId}/events`)를 *추가*하면 되므로 계약이 깨지지 않는다.
- **Postman 검증**: 컬렉션의 `GET /agent-runs/{runId}` 에 0/4 → 4/4 저장 예시 5개. Mock Server 에서 `x-mock-response-name: 200 폴링 2/4 완료 (RUNNING)` 헤더로 특정 상태를 강제하고, Collection Runner(delay 3000ms)에서 `postman.setNextRequest` 로 RUNNING 동안 자기 자신을 재호출한다.

### 4.5 기타 규약
- **페이지네이션**: `page`(1부터)·`size`(기본 20, 최대 100) + 응답 `total`. 목록이 작아 커서 방식은 과함.
- **오류 형식 단일화**: `Error{code, message, details}` — `code` 는 FE 분기용 상수(`NOT_FOUND`, `INVALID_STATE`, `RUN_NOT_COMPLETED`, `MISSING_INFORMATION`, `CHECKLIST_INCOMPLETE`, `VALIDATION_ERROR`, `UNAUTHORIZED`), `message` 는 한국어 표시 문구.
- **버전**: 경로 접두 `/api/v1`. 스키마 변경(major)은 `/v2` 로 분리, 프롬프트 버전(`prompt_version`)은 응답 필드로 노출해 판단 재현성 확보.
- **읽기 전용 마스터**(`/equipments`, `/parts`, `/laws/search`)는 GET 만 제공 — 지식 관리(UC-07)는 PoC 범위 밖, 시드 데이터로 대체.

## 5. 산출물 위치
| 파일 | 용도 |
|---|---|
| `docs/07_api/openapi.yaml` | 기계 판독 명세 (Swagger UI / Redoc / FastAPI 스텁 생성) |
| `docs/07_api/redocly.yaml` | lint 설정 |
| `postman/ReplaceFlow.postman_collection.json` | 요청 15개 + 저장 예시 52개 (Mock Server 용), 데모 시나리오 폴더 |
| `postman/ReplaceFlow.postman_environment.json` | `baseUrl` 등 환경 변수 |
| `docs/05_ai_ready/schemas/*.schema.json` | AgentRun / 에이전트별 결과 / Approval JSON Schema 2020-12 |
