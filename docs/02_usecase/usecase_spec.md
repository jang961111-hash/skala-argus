# Argus Use-Case 명세서

문서 버전: **v3.0 (2026-09-03)** · 기준 문서: `docs/CONTRACT.md` v3.0(팀 「API 명세서 v1.0」+「데이터 모델 정의서 v3.0」+「WRA 화면정의서 v2.0」 원문 이관), `docs/03_wireframe/figma_build_guide.md`(AC 번호 출처, UX 담당)
상태값·필드명(camelCase)·API 번호는 CONTRACT.md v3.0의 표기를 그대로 쓴다. **ID는 UUID v4**이며 예시의 `WR-...` 표기는 `requestNo`(사람이 읽는 표시용 채번)이지 PK가 아니다.

### v2.0 → v3.0 변경 요약 (팀 권위 문서로 교체)

v2.0(`docs/CONTRACT_v2.0_superseded.md`)은 오케스트레이터가 화면정의서에서 **추론**해 작성한 것이었고, 팀 노션의 실제 API 명세서·데이터 모델 정의서와 불일치해 폐기됐다. v3.0은 그 팀 문서를 그대로 옮긴 것이며, 이번 개정의 실질 변화는 다음과 같다.

1. **에이전트 코드 `SPEC`/`LEGAL`/`SAFETY_DOC` → `A1`/`A2`/`A3`**
2. **상태값 8종 → 6종**: `DRAFT`·`AI_RUNNING`·`AI_DONE`·`PENDING`·`APPROVED`·`REJECTED` (`REQUESTED`·`RUNNING`·`REVIEW`·`PENDING_APPROVAL` 표기 소멸)
3. **결과 구조가 에이전트별 고유 스키마 → 통일 구조**로 단순화: A1·A2는 `{items:[{itemId,text,edited}]}`, A3는 `{documents:[{docId,type,name,content,edited}]}`. `PATCH /agent-results/{id}`는 **전체 치환(PUT-like)** — 배열에 없는 기존 `itemId`는 삭제, `itemId` 없이 오면 신규 추가
4. **API 15개로 확정**(번호 1~15, CONTRACT §4). REST 경로가 리소스 중첩이 아니라 **평평한 구조**로 바뀐 곳이 있다 — 특히 `POST /agent-runs`, `POST /approvals`는 최상위 경로이고 body에 `workRequestId`를 담는다(`/work-requests/{id}/agent-runs`가 아니다)
5. **법령 마스터·설비 마스터·호환표·부품 마스터는 전부 Phase 2** — v2.0에서 가정했던 `law_index`/`equipments`/`parts`/`part_compatibility` 테이블이 v3.0 DB(7테이블+제안1)에 **없다**. `work_requests.equipment`/`line`/`substance`는 자유 텍스트 컬럼이다. A1·A2는 이 3일 범위에서 마스터 데이터 조인 없이 동작한다(§3.2)
6. **체크리스트 게이트는 v2.0부터 이미 폐지**됐고 v3.0에서도 유지 — 승인은 사유 없이 즉시, 거절만 사유(10자 이상) 필수
7. **재제출은 append-only** — `REJECTED`에서 동일 제출 API(#14) 재호출 시 `PENDING`으로 복귀하며 **직전 `approvals` 행은 삭제되지 않고 보존**된다(CONTRACT §5 설계원칙 3)
8. **Actor에서 `BUYER`·`ADMIN` 제거** — v3.0 `Role` enum은 `ENGINEER`·`SAFETY_MANAGER` 2종뿐이다. 지식 관리(구 UC-13, `ADMIN` 대상)는 대응 API 자체가 15개 안에 없어 **UC 목록에서 삭제**한다(`ai_configs`는 API로 노출되지 않는 내부 설정 테이블)

---

## 1. Actor 정의표

| Actor ID | Actor | 유형 | Role | 설명 | 주요 UC |
|---|---|---|---|---|---|
| ACT-00 | 미인증 방문자 | 사람 | — | 회원가입·로그인만 수행. 그 외 전 API 401 | UC-01, UC-02 |
| ACT-01 | 설비 엔지니어 | 사람 (Primary) | `ENGINEER` | 본인 요청만 조회·수정(403 위반 시). 요청 등록·임시저장·사진 업로드, AI 결과 확인·편집, 제출, 거절 시 재제출 | UC-03~08, UC-10, UC-12 |
| ACT-02 | 안전관리자 | 사람 (Primary) | `SAFETY_MANAGER` | `PENDING` 이상 전체 조회, AI 결과는 항상 읽기 전용(`editable:false`), 승인/거절 결정 | UC-09, UC-11 |
| ACT-03 | 모니터링 시스템 | 외부 시스템 (Mock, 선택) | — | 이상 알람. UC-03 진입의 선택적 트리거(CONTRACT에 명시 없음, PoC 연출용 유지) | UC-03(트리거) |
| ACT-04 | 에이전트 서비스 | 시스템 (Mock/LLM) | — | `A1`(규격·호환) / `A2`(법령·조문) / `A3`(안전서류) 3종. `A4` 벤더는 Phase 2 | UC-06 |

**v3.0에서 제거된 Actor**: 구매 담당(`BUYER`), 관리자(`ADMIN`), 법령 인덱스(외부 데이터) — `Role` enum과 DB 테이블 목록에 대응 항목이 없다.

---

## 2. Use-Case 명세

각 UC 표의 "API"는 CONTRACT §4의 번호(1~15)를 그대로 인용한다. "AC"는 `docs/03_wireframe/figma_build_guide.md` §6의 원문 번호다.

### UC-01 회원가입

| 항목 | 내용 |
|---|---|
| 주 Actor | 미인증 방문자 |
| 화면 | `WRA_C_01` (`/signup`) |
| API | **#1** `POST /auth/signup` |
| 입력 | `name`(2~20자) · `email`(유니크) · `password`(8자 이상, 영문+숫자+특수문자) · `passwordConfirm` · `role`(`ENGINEER`\|`SAFETY_MANAGER`) |
| 사후조건 | `users` 레코드 생성(`password_hash`는 bcrypt) |
| 오류 | 400 `VALIDATION_FAILED` · 400 `PASSWORD_MISMATCH` · 409 `EMAIL_ALREADY_EXISTS` |
| AC | 1-1~1-5 |

**기본 흐름**: 가입 폼 입력 → 유효성 통과 → `POST /auth/signup` → 201 → `WRA_C_00` 이동.
**예외**: 필수 누락/역할 미선택 → `VALIDATION_FAILED`. 비밀번호 불일치 → `PASSWORD_MISMATCH`. 중복 이메일 → `EMAIL_ALREADY_EXISTS`(409).

**구현 확인됨**: `WRA_C_01`은 `frontend/src/views/auth/SignupView.vue`로 실재하고, 라이브 E2E가 signup 201·409(`EMAIL_ALREADY_EXISTS`)·400(`PASSWORD_MISMATCH`)을 실측했다. 09-03 캡처 세트에 이 화면 스크린샷이 빠진 것은 미구현이 아니라 **로그인 상태에서 `/signup` 접근 시 리다이렉트돼 캡처를 못 뜬 것**(재캡처 예정)이다.

---

### UC-02 로그인 (역할 분기)

| 항목 | 내용 |
|---|---|
| 주 Actor | 미인증 방문자 |
| 화면 | `WRA_C_00` (`/login`) |
| API | **#2** `POST /auth/login`, **#3** `GET /auth/me`(새로고침·직접 URL 진입 시 역할별 GNB 렌더링용) |
| 사후조건 | JWT `accessToken` 발급. 이후 전 API(`/auth/*` 제외) `Authorization: Bearer` 필수 |
| 오류 | 401 `INVALID_CREDENTIALS`(로그인) / 401 `TOKEN_EXPIRED`·`TOKEN_INVALID`(me) |
| AC | 0-1~0-4 |

**기본 흐름**: 이메일·비밀번호 입력 → `POST /auth/login` → 200 `{accessToken, role, redirectPath}`. **`redirectPath`는 서버가 계산해 내려준다**(`ENGINEER`→`/home`, `SAFETY_MANAGER`→`/manage/requests`) — 프론트는 role로 직접 분기하지 않고 이 값을 그대로 따른다.
**예외**: 자격 증명 불일치 → 401. 미가입자는 "회원가입" 링크로 UC-01.

---

### UC-03 작업요청 등록

| 항목 | 내용 |
|---|---|
| 주 Actor | 설비 엔지니어 |
| 부 Actor | 모니터링 시스템(선택 트리거) |
| 화면 | `WRA_E_02` (`/requests/new`) |
| API | **#5** `POST /work-requests`(`draft=false`), **#11** `POST /agent-runs`(body `{workRequestId}`만) |
| 사전조건 | 로그인된 `ENGINEER` |
| 사후조건 | `work_requests.status = DRAFT`에서 시작해 `draft=false`로 생성 시 서버가 `AI_RUNNING`으로 전이시키는 흐름(§3 상태 전이 참조), `agent_runs` 신규 행 생성 |
| AC | 3-1, 3-2, 3-3, 3-5 |

`equipment`·`line`·`substance`·`operatingCondition{temperature,pressure}`·`productName`·`productType`·`specJson`은 **`draft=false`일 때만 필수**. `productType`이 `specJson` 필수 키를 정한다(CONTRACT §2 표: `VALVE`/`REGULATOR`→`pressureRating`, `FITTING_TUBE`→`connectionStandard`+`material`, `FILTER`→`substanceType`, `ETC`→`freeSpec`). 서버가 유형별 스키마를 검증하며 불일치 시 **400 `SPEC_SCHEMA_MISMATCH`**.

**기본 흐름**
1. `WRA_E_01`에서 "신규 교체 요청" → `WRA_E_02`.
2. 엔지니어가 위 필드를 입력한다. `productType` 선택에 따라 `specJson` 입력 폼이 동적으로 바뀐다(AC 3-2).
3. `symptom`·`siteMemo`는 선택.
4. (선택) 사진 첨부 — UC-05.
5. "AI 검증 시작" → `POST /work-requests`(`draft:false`) → 201. 이어서 `POST /agent-runs`(body `{workRequestId}`) → **202**. `WRA_E_03`으로 이동.

**대안/예외**
- 2a. 필수값 누락 또는 `specJson`이 `productType` 필수 키와 불일치 → 400 `SPEC_SCHEMA_MISMATCH`(등록 차단).
- 5a. 이미 진행 중인 run이 있는 상태에서 재요청 → 409 `RUN_ALREADY_IN_PROGRESS`.
- 5b. 필수값 누락된 채 agent-runs 시도 → 400 `WORK_REQUEST_INCOMPLETE`.

---

### UC-04 요청 임시저장 (DRAFT)

| 항목 | 내용 |
|---|---|
| 주 Actor | 설비 엔지니어 |
| 화면 | `WRA_E_02`(저장) → `WRA_E_05`(목록 노출, UC-12) → `WRA_E_02`(이어쓰기) |
| API | **#5** `POST /work-requests`(`draft=true`), **#8** `PATCH /work-requests/{id}`(이어쓰기 중 수정), **#7** `GET /work-requests/{id}`(재조회) |
| 사후조건 | `status = DRAFT`. 업무 컬럼은 DB NOT NULL이 아니므로(§5) 부분 입력만으로 저장 가능 — **필수값 검증은 서비스 계층에서 `draft=false`일 때만 수행**하므로 `draft=true`면 전부 선택값 |
| AC | 3-6, 6-5 |

**기본 흐름**: "임시 저장" → `POST /work-requests`(`draft:true`) → 201, `status=DRAFT`. 나중에 `WRA_E_05`에서 "이어서" → `GET /work-requests/{id}` → `WRA_E_02` 재진입, 저장값 복원 → `PATCH /work-requests/{id}`로 계속 수정 가능(UC-03 흐름으로 합류).

> **팀 확인 필요 (CONTRACT §8-7 원문)**: "사진 업로드는 요청 생성 이후 구조 — E_02에서 저장 전 업로드하려면 DRAFT 선생성 전제." 즉 `WRA_E_02`에서 사진을 첨부하려면 **먼저 `draft:true`로 `work_requests` 행을 만들어 `workRequestId`를 확보해야** `POST /work-requests/{id}/photos`(UC-05)를 호출할 수 있다. 이는 폼 입력 도중 최초 사진 첨부 시점에 임시 DRAFT 생성이 암묵적으로 선행되어야 함을 뜻하며, **CONTRACT에도 팀이 아직 확정하지 않은 사항으로 명시돼 있다.** 이 문서는 그 제약을 그대로 기록만 하고 임의로 확정하지 않는다.

---

### UC-05 사진 업로드

| 항목 | 내용 |
|---|---|
| 주 Actor | 설비 엔지니어(업로드) · 안전관리자(열람) |
| 화면 | `WRA_E_02`(업로드) · `WRA_S_02`(열람) |
| API | **#9** `POST /work-requests/{id}/photos`(`multipart/form-data`, 파트명 **`files`(배열)**), **#10** `GET /work-requests/{id}/photos` |
| 제약 | jpg/png/webp · 파일당 10MB · **요청당 최대 5장** · **서버가 EXIF 제거 + 320px 썸네일 생성** |
| 오류 | 400 `UNSUPPORTED_FILE_TYPE` · 413 `FILE_TOO_LARGE` · 409 `PHOTO_LIMIT_EXCEEDED` |
| AC | 3-4(업로드), 8-5(안전관리자 열람) |

**기본 흐름**: 파일 선택(여러 장 가능) → `POST /work-requests/{id}/photos`(`files[]`) → 201, 서버가 EXIF 제거·썸네일 생성 후 저장 → 썸네일 표시. `WRA_S_02`에서 안전관리자가 썸네일 클릭 → 원본 열람(`GET .../photos`).
**예외**: 지원하지 않는 형식 → 400. 10MB 초과 → 413. 5장 초과 → 409. (UC-04의 "팀 확인 필요" 메모 참조 — DRAFT 선생성 전제)

---

### UC-06 AI 검증 (에이전트 실행, A1·A2·A3)

| 항목 | 내용 |
|---|---|
| 주 Actor | 시스템(오케스트레이터) |
| 부 Actor | 엔지니어(UC-03에서 트리거), 에이전트 서비스 `A1`/`A2`/`A3` |
| 화면 | `WRA_E_03` (`/requests/{id}/run`) |
| API | **#12** `GET /agent-runs/{runId}`(폴링), **#7** `GET /work-requests/{id}`(결과 확인 이동 전 재조회) |
| AC | 4-1~4-4 |
| AI 확장 지점 | **있음 — 핵심.** `AgentOrchestrator` + 3개 에이전트. **서버가 `workRequestId`로 전체 스냅샷을 구성**(설비·라인·물질·운전조건·제품명·유형·스펙·사진 메타)해 각 에이전트에 전달(CONTRACT §4-11) |

**기본 흐름**
1. `WRA_E_03` 진입. `agent_steps` 3개(`A1`,`A2`,`A3`)가 `WAITING`으로 표시된다.
2. `GET /agent-runs/{runId}` 폴링. 간격은 스펙상 "2~3초"이지만 **정확한 값은 서버가 `pollIntervalMs`로 내려주며(실측 2500ms), 프론트는 이 값을 그대로 쓴다** — 하드코딩하지 않는다. `steps[].status`(`WAITING→RUNNING→DONE`)로 카드 갱신.
3. 3개 모두 `DONE`이면 응답의 `allDone:true`. 프론트는 폴링을 멈추고 "결과 확인" 버튼을 활성화한다. **서버는 이 시점에 `work_requests.status`를 `AI_DONE`으로 전환한다.**
4. "결과 확인" → `GET /work-requests/{id}` → `WRA_E_04`(UC-07).

**대안/예외**
- 특정 step 실패 → **해당 step만 `status:"FAILED"` + `errorMessage`, HTTP는 200 유지**(전체 실패로 취급하지 않는다 — CONTRACT §4-12). 나머지 step은 계속 진행될 수 있다.
- `{runId}` 없음 → 404 `AGENT_RUN_NOT_FOUND`.
- 이미 진행 중인 run이 있는 상태에서 재실행 시도(UC-03 단계) → 409 `RUN_ALREADY_IN_PROGRESS`.

---

### UC-07 AI 결과 확인·편집

| 항목 | 내용 |
|---|---|
| 주 Actor | 설비 엔지니어 |
| 화면 | `WRA_E_04` (`/requests/{id}/result`) |
| API | **#7** `GET /work-requests/{id}`(`agentRun.results[]` 포함), **#13** `PATCH /agent-results/{id}` |
| 사전조건 | `status = AI_DONE` (또는 `REJECTED` 재진입) |
| 오류 | 409 `RESULT_LOCKED`(락 상태에서 수정 시도) · 403 `FORBIDDEN_NOT_OWNER` |
| AC | 5-1, 5-2 |

편집 단위는 **카드(A1/A2/A3) 통째가 아니라 항목(`items[]`의 각 원소, A3는 `documents[]`의 각 문서) 단위**다 — 화면에서 항목 하나하나를 따로 추가·삭제·편집할 수 있다. 다만 그 결과를 서버에 반영하는 API 호출 방식은 `PATCH /agent-results/{id}` **전체 치환(PUT-like)** 1회다: A1·A2는 `{items:[{itemId,text,edited}]}`, A3는 `{documents:[{docId,type,name,content,edited}]}`를 배열 통째로 보낸다 — 배열에 없는 기존 `itemId`/`docId`는 삭제되고, id 없이 `text`/`content`만 오면 신규 추가로 처리된다. 즉 "편집 단위는 항목별"이지만 "저장 호출은 배열 전체 1회"라는 뜻이며, 둘을 혼동하지 않는다.

**기본 흐름**
1. `WRA_E_04` 진입 → `GET /work-requests/{id}` → `agentRun.results[]`(A1·A2 항목형, A3 문서형) 표시. `editable:true`(엔지니어 시점, `AI_DONE`/`REJECTED`일 때).
2. 항목 추가/삭제/편집 후 저장 → `PATCH /agent-results/{id}`에 **변경된 배열 전체**를 보낸다 → 200, 서버가 각 항목/행의 `edited`를 갱신.
3. 화면은 `edited:true`인 항목을 AI 원본과 시각적으로 구분해 표시한다(§3.1 가드레일).

**예외**: `PENDING`/`APPROVED` 상태에서 수정 시도 → 409 `RESULT_LOCKED`(CONTRACT §3 "PENDING·APPROVED 수정 시도" 규칙).

---

### UC-08 제출 (승인 요청)

| 항목 | 내용 |
|---|---|
| 주 Actor | 설비 엔지니어 |
| 화면 | `WRA_E_04` |
| API | **#8** `PATCH /work-requests/{id}`(`engineerNote` 저장), **#14** `PATCH /work-requests/{id}/submit-approval` |
| 사후조건 | `status = PENDING`. `WRA_S_01`에 노출 |
| 오류 | **422 `SUBMIT_REQUIRED_FIELD_MISSING`** |
| AC | 5-3, 5-4, 5-5 |

서버 검증 4가지(CONTRACT §4-14): ① A1·A2·A3 결과 전부 존재 ② `engineerNote` 비어 있지 않음 ③ **A2 적용 법령(항목) 1건 이상** ④ 상태가 `AI_DONE` 또는 `REJECTED`. 하나라도 실패하면 422.

**기본 흐름**: `engineerNote` 작성(#8) → "제출" → `PATCH .../submit-approval`(#14) → 200 → `status=PENDING`.
**예외**: 4조건 중 하나라도 미충족 → 422, 안내 후 차단.

---

### UC-09 승인 / 거절

| 항목 | 내용 |
|---|---|
| 주 Actor | 안전관리자 |
| 화면 | `WRA_S_02` (`/manage/requests/{id}`) |
| API | **#7** `GET /work-requests/{id}`(`agentRun.results[].editable`는 **항상 `false`**), **#10** `GET /work-requests/{id}/photos`, **#15** `POST /approvals`(body `{workRequestId, decision, reason?, reasonCategory?}`) |
| 사전조건 | `status = PENDING` |
| 오류 | 403 `FORBIDDEN_ROLE`(SAFETY_MANAGER 아님) · 409 `NOT_PENDING` · 409 `ALREADY_DECIDED` · 400 `REJECT_REASON_REQUIRED`(REJECT인데 `reason` 없음/10자 미만) |
| AC | 8-1~8-5 |

`POST /approvals`는 **최상위 경로**이고 body에 `workRequestId`를 담는다(`/work-requests/{id}/approvals`가 아니다). **체크리스트 blocking 없음(CONTRACT §4-15, v2.0부터 이미 폐지, v3.0에서도 유지)** — 승인은 사유 없이 즉시 처리되고, 거절만 사유(10자 이상, 미만이면 400 `REJECT_REASON_REQUIRED`)가 필수다. **Human-in-the-loop은 체크리스트가 아니라 역할 분리로 지켜진다**: 승인/거절 자체를 `SAFETY_MANAGER`만 수행할 수 있고(403 `FORBIDDEN_ROLE`), 요청은 애초에 `ENGINEER`만 생성하므로 요청자가 스스로를 승인하는 경우는 역할 구조상 발생하지 않는다(실측: `backend/app/services/approval_service.py`에 별도의 "자가승인 차단" 검사는 없다 — 필요가 없기 때문).

**화면 인터랙션(`WRA_S_02`, 실연동 캡처 기준)**: 승인/거절은 **토글로 결정을 먼저 선택하고, 별도의 "결정 확정" 버튼으로 한 번 더 확정하는 2단계** 구조다(오조작 방지). 거절을 선택하면 그 시점부터 사유 textarea가 노출되고, 확정 시점에 사유 길이를 검증한다.

**기본 흐름**
1. `WRA_S_01`에서 `PENDING` 건 클릭 → `WRA_S_02`. `GET /work-requests/{id}`로 요청 정보·AI 결과(읽기 전용)·`engineerNote`·사진 확인.
2. 토글에서 "승인" 선택 → "결정 확정" 클릭 → `POST /approvals {workRequestId, decision:"APPROVE"}` → 201 → `status=APPROVED`.

**대안/예외**
- 토글에서 "거절" 선택 → 사유 textarea 노출 → "결정 확정" 클릭 시 `reason` 10자 미만이면 400 `REJECT_REASON_REQUIRED`(클라이언트에서도 선차단).
- 사유 입력 후 확정 → `POST /approvals {decision:"REJECT", reason, reasonCategory?}` → 201 → `status=REJECTED`. `reasonCategory`는 CONTRACT §8-6에 "고정 5종 enum vs 자유 입력" 미확정으로 명시돼 있어, 자유 문자열로 취급한다(§5 DB `reason_category varchar(30)`가 enum 컬럼이 아닌 점을 근거로 삼되, 최종 확정은 팀 판단 대기).
- 이미 결정된 요청 재결정 → 409 `ALREADY_DECIDED`. `PENDING`이 아닌 요청 → 409 `NOT_PENDING`.

---

### UC-10 거절 사유 확인 후 재제출

| 항목 | 내용 |
|---|---|
| 주 Actor | 설비 엔지니어 |
| 화면 | `WRA_E_05`(사유 확인) → `WRA_E_04`(재편집, UC-07) |
| API | **#6** `GET /work-requests?status=REJECTED`, **#7** `GET /work-requests/{id}`(최신 `approval` 포함), **#14** `PATCH .../submit-approval`(재호출) |
| 사후조건 | `status: REJECTED → PENDING`. **직전 `approvals` 행은 삭제되지 않고 그대로 보존**(append-only, CONTRACT §5 설계원칙 3) — 이력 화면에서 과거 거절 사유도 조회 가능해야 함(구현 세부는 Phase 밖) |
| AC | 6-3, 6-4 |

**기본 흐름**: `WRA_E_05`에서 `REJECTED` 건의 사유(`GET /work-requests/{id}`의 `approval.reason`) 확인 → `WRA_E_04` 재진입(UC-07로 A1/A2/A3 결과·`engineerNote` 재편집) → 동일한 **#14** `submit-approval` 재호출 → `status: REJECTED → PENDING` 복귀.

---

### UC-11 대시보드 조회

| 항목 | 내용 |
|---|---|
| 주 Actor | 설비 엔지니어(`WRA_E_01`) / 안전관리자(`WRA_S_01`) |
| API | **#4** `GET /dashboard/summary?role=engineer\|safety`, **#6** `GET /work-requests?mine=&status=&page=&size=&sort=` |
| 오류 | `role` 필수, **토큰 역할과 불일치 시 403** |
| AC | 2-1, 2-2, 2-4(엔지니어) / 7-1~7-5(안전관리자) |

- 엔지니어(`role=engineer`): 작성중·진행중(AI)·승인대기·반려보완 4개 KPI. **평균 승인 소요시간 없음.** `GET /work-requests?mine=true`로 최근 요청 조회, 각 항목의 **`nextAction`(서버가 계산: `DRAFT`→이어서/`AI_RUNNING`→진행/`AI_DONE`→결과/그 외→상세)**으로 행 클릭 시 이동 화면을 결정한다(CONTRACT §4-6, 프론트가 상태를 직접 분기하지 않는다).
- 안전관리자(`role=safety`): 승인대기·오늘처리·이번달승인·이번달거절 4개 KPI + `rejectReasonsTop`(TOP5). `GET /work-requests?status=PENDING`으로 목록.
- 목록 응답은 `content[]` + `page{}`(0-base 페이지네이션). 빈 목록도 200 + `content:[]`.

---

### UC-12 내 요청 목록 (상태 필터)

| 항목 | 내용 |
|---|---|
| 주 Actor | 설비 엔지니어 |
| 화면 | `WRA_E_05` (`/my/requests`) |
| API | **#6** `GET /work-requests?mine=true&status=&page=&size=&sort=`, **#7**, **#14**(재제출은 UC-10) |
| AC | 6-1, 6-2, 6-5 |

`status`는 **콤마로 다중 지정 가능**(예: `REJECTED,DRAFT`). 상태 탭 선택 → 재조회. `DRAFT` 건은 `nextAction`이 "이어서"를 가리켜 `WRA_E_02`(UC-04)로, `REJECTED` 건은 UC-10으로 이어진다.

---

## 3. AI 확장 지점 정의

### 3.1 원칙

에이전트는 정보를 모으고 초안을 쓸 뿐, 판단·승인은 사람이 한다(Human-in-the-loop). 산업안전 규제상 승인 주체는 사람이어야 하며 이는 설계 요건이다.

**AI 원본 보존 원칙(팀 ERD 근거 인용)**: `agent_results` 테이블은 `payload_json`(현재값)과 별도로 **`original_json`**(CONTRACT는 [제안]으로 표시했지만 실측: `backend/app/models/agent.py`에 이미 컬럼으로 구현됨) — AI가 처음 생성한 원본 스냅샷 — 을 둔다. ERD 문서의 근거 그대로 인용하면: *"`original_json` 없이 `edited:true`만 있으면 무엇이 바뀌었는지 알 수 없다."* 이는 `docs/05_ai_ready/prompts.md` §0에서 정의한 가드레일("엔지니어가 편집한 결과는 AI 원본과 화면에서 시각적으로 구분한다")의 **DB 레벨 구현**이다 — 화면의 `edited:true` 배지는 UI 표현이고, `original_json`은 그 배지가 가리키는 "무엇이 바뀌었는가"를 실제로 diff 가능하게 만드는 근거 데이터다. 이 둘을 한 세트로 본다.

**`agent_steps`(진행)와 `agent_results`(결과)가 분리된 이유(팀 ERD 근거 인용)**: *"갱신 주체와 주기가 다르다. `agent_steps`는 오케스트레이터가 초 단위로(폴링), `agent_results`는 엔지니어가 편집한다(UC-07). 한 테이블이면 폴링 UPDATE와 편집 UPDATE가 같은 행을 경합한다."* 이는 CONTRACT §5의 "사실/추론/행동 분리" 원칙(입력 `work_requests` · AI 산출 `agent_runs`/`agent_steps`/`agent_results` · 사람 결정 `approvals`을 테이블로 분리하고 위 층이 아래 층을 덮어쓰지 않는다)의 구체적 적용 사례이며, 데이터베이스 설계와 AI 파이프라인 설계가 같은 원칙(쓰기 경합 회피, 이력 보존)을 공유한다는 근거로 발표에서 인용할 가치가 있다.

### 3.2 확장 지점 (AI가 들어가는 곳)

| # | 확장 지점 | 위치 | 관련 UC | PoC 구현 | 확장 구현 |
|---|---|---|---|---|---|
| X-0 | **AgentOrchestrator** | `agent_runs`/`agent_steps` 생성·관리, **서버가 `workRequestId`로 전체 스냅샷 구성**(CONTRACT §4-11, 실측: `AgentOrchestrator.build_snapshot()`) | UC-06 | 3-step 순차 Mock 전이, `pollIntervalMs:2500`, `agent_runs.input_snapshot`에 스냅샷 영속화(CONTRACT [제안] 표기와 달리 이미 구현됨) | Queue 기반 실 병렬 실행 |
| X-1 | **A1 규격·호환** | 입력: 스냅샷의 `specJson` / 출력: `items[]`(적합성 판정 텍스트) | UC-06, UC-07 | Mock. **부품 마스터·호환표 DB가 Phase 2**라 실제 재고·대체품 대사는 하지 않고, 입력 스펙 적합성 판정만 수행 | 부품 마스터 연동 후 `alternatives[]` 구조화 |
| X-2 | **A2 법령·조문** | 입력: 스냅샷의 설비·물질·운전조건 / 출력: `items[]`(조문 인용 텍스트) | UC-06, UC-07 | Mock. **법령 마스터(`law_index`) DB가 Phase 2**라 RAG 조회가 아니라 프롬프트에 정적으로 내장된 참고 조문(시드)을 근거로 답한다 | 법제처 Open API 적재 + RAG |
| X-3 | **A3 안전서류** | 입력: A2 결과 + 스냅샷 / 출력: `documents[]`(초안 본문) | UC-06, UC-07 | Mock 초안 | LLM 초안 생성, 재생성 |
| X-4 | ~~A4 벤더~~ | **Phase 2** | — | — | — |
| X-C | **AI 설정 격리** | `ai_configs`[제안](`agent_code`, `provider` MOCK/LOCAL_LLM/OPENAI, `model_name`, `prompt_version`, `temperature`, `max_tokens`, `egress_allowed` default false, `is_active`, **부분 유니크 `UNIQUE(agent_code) WHERE is_active`**). **API 키는 테이블에 두지 않고 환경변수로 관리** | 전체 | `provider=MOCK` 고정 | `LOCAL_LLM`/`OPENAI` 교체, `prompt_version`이 `docs/05_ai_ready/prompts/<agent>/<version>.txt` 파일 버전과 매칭(§3.3) |

### 3.3 `prompt_version` ↔ 프롬프트 파일 버전 매칭

`ai_configs.prompt_version`은 실제 프롬프트 파일 버전과 매칭되어야 한다는 것이 팀 데이터 모델 정의서에 명시돼 있다. 이 저장소에서는 `docs/05_ai_ready/prompts.md`에 원문을 두고 현재 버전은 **`argus-v0.3`**(A1/A2/A3 3종 통일 구조 기준)이다. 다만 **`ai_configs`가 미구현(CONTRACT §10)이라 이 매칭은 아직 설계 의도일 뿐 실제로 DB에 기록되지 않는다** — 실측(`backend/app/models/`, `services/agent_service.py`)에 `prompt_version` 필드 자체가 없다. `ai_configs`가 승격되면 `agent_runs.ai_config_id`[제안]가 실행 당시 값을 고정해 재현성을 보존하게 된다.

### 3.4 사람이 유지하는 곳

| 행위 | Actor | UC | 시스템 보장 장치 |
|---|---|---|---|
| 요청 등록·임시저장·사진 첨부 | 엔지니어 | UC-03~05 | `draft=false` 시에만 필수값 검증(서비스 계층), `specJson` 유형 불일치 400 |
| AI 결과 전체를 항목/문서 단위로 편집 | 엔지니어 | UC-07 | `PATCH /agent-results/{id}`(전체 치환)만 허용, `PENDING`/`APPROVED`에서는 409 `RESULT_LOCKED` |
| 제출 결정(설명 첨부, A2 근거 1건 이상 강제) | 엔지니어 | UC-08 | 422 `SUBMIT_REQUIRED_FIELD_MISSING`(4조건) |
| AI 결과 근거 확인(항상 읽기 전용), 승인/거절(사유) 결정 | 안전관리자 | UC-09 | `agentRun.results[].editable`는 SAFETY_MANAGER 조회 시 항상 `false`. REJECT는 `reason` 10자 이상 없으면 400 |
| 거절 사유 확인 후 재제출 판단 | 엔지니어 | UC-10 | 직전 `approvals` append-only 보존으로 이력 추적 가능 |

### 3.5 Phase 2 — v3.0 범위 외

CONTRACT §8-10 원문 그대로: **A1 부품 마스터·호환표 연동, A4 벤더 에이전트**가 Phase 2다. 여기에 CONTRACT §5의 "⚠️ N:M은 이번 범위에 없다(ERD 문서 명시). 법령 마스터·설비 마스터·호환표는 Phase 2"를 더하면, v2.0에서 가정했던 `equipments`/`parts`/`part_compatibility`/`law_index` 4개 테이블이 v3.0 DB(7테이블+제안1)에 전부 빠져 있다는 뜻이다.

A4를 뺀 이유는 v2.0과 동일하게 유효하다: 벤더 견적(RFQ)은 외부 시스템 연동이 필요해 온프레미스 전제(`ai_configs.egress_allowed=false` 기본)와 충돌하고, 3일 범위에서 Mock으로 흉내 내면 A1·A2·A3의 근거 품질까지 의심받는다.

**루브릭 리스크**: CONTRACT §5는 "루브릭이 '1:N, N:M 관계'를 요구하므로 감점 위험이 있다. 팀 판단 필요 사항으로 보고됨"이라고 명시한다. 이 UC 문서가 다루는 범위 밖의 결정이므로 여기서는 사실만 기록하고, ERD·발표 트랙의 판단을 따른다.

---

## 4. 삭제된 UC — 지식 관리 (v2.0 UC-13)

v2.0에서 `ADMIN`이 법령 인덱스·AI 설정을 관리하던 UC는 v3.0에서 **완전히 삭제**한다. `ai_configs`가 DB에는 [제안]으로 존재하지만(실측: `backend/app/models/`에 대응 모델 없음 — 코드로도 미구현 확인) API 15개 어디에도 이를 조회·수정하는 엔드포인트가 없고, `Role` enum에도 `ADMIN`이 없다. 대응 UC를 억지로 남기면 존재하지 않는 API를 가리키게 되므로, CONTRACT과 모순되지 않도록 이 UC 자체를 없앤다.

---

## 5. UC ↔ 라이브 E2E 실측 대조 (`scripts/e2e_live_v3.sh`, 64 PASS / 0 FAIL)

기준 로그: `docs/10_project_record/02_evidence/test_results/e2e_live_v3_20260903_1537.log`. E2E는 13개 섹션으로 구성되며, 아래는 각 섹션이 검증한 항목을 UC 번호에 매핑하고 **양방향 gap**(UC에는 있는데 E2E가 안 덮는 것 / E2E가 검증하는데 UC 본문에 없던 것)을 기록한다.

| E2E 섹션 | 검증 항목(요약) | 대응 UC | 비고 |
|---|---|---|---|
| 1. 인증 | signup 성공/중복이메일/비번불일치, login 성공/role/redirectPath/실패, auth/me 토큰有無 | UC-01, UC-02 | 일치 |
| 2. DRAFT 생성·이어쓰기 | draft 생성/상태/`requestNo` 형식/`id` UUID, 미완성 draft로 agent-runs 시도 400, PATCH 이어쓰기 | UC-04(주), UC-03(예외) | `requestNo`/`id` 형식 검증은 실측에만 있고 UC-04 본문엔 형식 언급 없음 — **gap①**(경미, CONTRACT §1·§5에 이미 정의) |
| 3. 정식 생성 검증 | 필수값 누락 400 `VALIDATION_FAILED`, `specJson` 불일치 400 `SPEC_SCHEMA_MISMATCH` | UC-03 | `SPEC_SCHEMA_MISMATCH`는 이미 명시. `VALIDATION_FAILED`(단순 필수 누락)는 UC-03 예외흐름에 없었음 — **gap②**(경미) |
| 4. 에이전트 실행·폴링 | 202/RUNNING/409 중복실행/폴링 누적 DONE/`pollIntervalMs`/`allDone`/`AI_DONE` 전환 | UC-06 | 일치, 세부까지 정확히 대응 |
| 5. 결과 편집 — 전체 치환 | PATCH 200/`edited:true`/삭제+신규 반영/`itemId` 없는 신규 채번 | UC-07 | 일치 |
| 6. 제출 | `engineerNote` 없이 422, 채운 뒤 200, `PENDING` 전환 | UC-08 | 일치 |
| 7. 권한 | 엔지니어가 승인 시도 403 `FORBIDDEN_ROLE`, **타인 요청 조회 403 `FORBIDDEN_NOT_OWNER`** | UC-09(전자) | **후자(`FORBIDDEN_NOT_OWNER`)는 어느 UC 본문에도 오류 코드로 명시돼 있지 않았다 — gap③.** CONTRACT §1 "ENGINEER는 본인 요청만 조회·수정, 위반 시 403"은 있었지만 UC-07/UC-12에 구체적 오류 코드로 옮기지 않았다 |
| 8. 승인/거절 | 사유 없음/9자 400, 정상 거절 201/`REJECTED`, **재제출 200/`PENDING`**, 정상 승인 201/`APPROVED`, 중복 승인 409 | UC-09, **UC-10** | 상태 전이(`REJECTED→PENDING`)는 실측 일치. **단, "직전 approval 이력 보존"은 테스트 이름에만 있고 실제로 approval 개수·과거 행 존재를 assert하는 코드는 없다(`scripts/e2e_live_v3.sh` 254~257행 확인) — UC-10의 "이력 보존" 사후조건은 CONTRACT §5 설계원칙(append-only)에서 끌어온 것이지 이 E2E가 실측한 사실이 아니다. 과장하지 않도록 구분해 둔다.** |
| 9. 불변 상태 | `APPROVED`에서 work-requests PATCH 409 `IMMUTABLE_STATUS`, agent-results PATCH 409 `RESULT_LOCKED` | UC-07(후자, 이미 명시), UC-08 | **`IMMUTABLE_STATUS`(work-requests PATCH 자체의 잠금)는 UC-08 본문에 오류 코드로 없었다 — gap④** |
| 10. 대시보드 | role=engineer/safety 200, 평균승인시간 없음, `rejectReasonsTop` 존재, role 불일치 403 | UC-11 | 일치 |
| 11. 목록 | `mine=true`, `status` 콤마 다중, `page.number` 0-base, `nextAction` 존재 | UC-12 | 일치 |
| 12. 404 | 없는 workRequest/run | UC-03, UC-06(대안흐름에 이미 명시) | 일치 |
| 13. 오류 포맷 | 단일 `{code,message}` 포맷, `detail` 키 부재 | 전 UC 공통(CONTRACT §1.1·§6) | UC 단위가 아니라 계약 레벨 검증 — 대응 UC 없음이 정상 |

**UC에는 있는데 E2E가 전혀 안 덮는 것**: **UC-05(사진 업로드)**. `scripts/e2e_live_v3.sh`에 `photos`/`files` 관련 호출이 한 줄도 없다 — API#9·#10이 이번 E2E 실행 64건에 포함되지 않았다. 9화면 스크린샷(`02_evidence/screenshots/v3.0_WRA_E_02_요청등록_동적스펙.jpg`)에 업로드 UI가 있는지는 별개로, **API 레벨 실측은 없다.**

**요약**: UC-05를 제외한 나머지 11개 UC(UC-01~04, 06~12)는 E2E 실측과 정합한다. gap ①~④ 중 ③(`FORBIDDEN_NOT_OWNER`)·④(`IMMUTABLE_STATUS`)는 이번 절 작성으로 위 UC 표에 이미 반영했다(UC-07·UC-09 관련 항목 원문에 오류 코드 자체는 있었으나, "타인 조회"·"work-requests 자체 잠금" 케이스로 명시되지는 않았던 것 — 재작성하지 않고 이 표로 보완한다). UC-10의 "이력 보존" 문구는 CONTRACT 설계원칙에 근거하되 이번 E2E가 실측한 것은 아니라는 점을 분명히 남긴다.
