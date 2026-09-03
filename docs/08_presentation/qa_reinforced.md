# Q&A 보강 — 답이 약했던 5문항 (발표자 장병헌)

`docs/09_qa/qa_bank.md`의 25문항을 검토해 **지금 답하면 무너지는 5개**를 골라 다시 썼다. 발표 당일 이 5개는 아래 답을 쓴다(qa_bank의 해당 행보다 우선). 각 답은 20~30초 안에 끝나게 썼고, **파일 경로와 실측 결과를 근거로 붙였다.**

> **⚠️ `docs/CONTRACT.md` v3.0(최종 확정) 기준 유효성**
> - **Q1(GET이 상태를 바꾼다)·Q2(AI가 없는데 AI 프로젝트인가)·Q3(Spring Boot 대신 FastAPI)** — 논지 그대로 유효. 다만 Q4에서 인용하던 항목 내역은 아래대로 바뀐다.
> - **Q4(Mock인데 뭘 검증했나)** — **본문을 확정 수치로 갱신 완료.** (이하 이력) 이전 v1.0 항목 내역은 무효였다: 에이전트가 3종이라 "폴링 4회"는 3회가 되고, "체크리스트 미완 409"는 게이트 폐지로 사라졌고, 상태값·에러 포맷·ID 규칙이 전부 바뀌었다. **코드 프리즈 후 `bash scripts/e2e_live.sh`를 다시 돌려 통과 건수와 항목을 새로 채운다.**
>   v3.0에서 실측 대상이 되는 가드는 이것들이다 — `403 FORBIDDEN_ROLE`(엔지니어의 승인 시도) · `403 FORBIDDEN_NOT_OWNER`(남의 요청 조회) · `422 SUBMIT_REQUIRED_FIELD_MISSING`(결과 3종·설명·**A2 법령 1건**) · `400 REJECT_REASON_REQUIRED`(거절 사유 10자) · `400 SPEC_SCHEMA_MISMATCH`(유형별 스펙 키) · `409 RUN_ALREADY_IN_PROGRESS` / `IMMUTABLE_STATUS` / `RESULT_LOCKED` / `ALREADY_DECIDED` · `413 FILE_TOO_LARGE` · 404 2종.
> - **Q5(수치 근거)** — v3.0 기준으로 본문을 다시 썼다. 논지가 더 강해졌다: 평균 승인 소요시간 KPI를 **화면뿐 아니라 API에서도 제거**했으므로 "측정 못 하는 숫자는 아예 지웠다"고 말할 수 있다.
> - 다섯 번째 문항이 필요하면 **"어제 설계를 오늘 왜 뒤집었나"** 또는 **"N:M이 하나도 없는데"** 를 쓴다 → `v2_framing_notes.md` §1·§4.
> - ✅ **최종 수치(`..._1637.log`)**: pytest **30 passed** · E2E **72/0** · 빌드 **223.88 kB**(gzip **81.98**). 발표자 대조 완료.
> - **서비스명 `Argus` 확정.** 옛 이름 언급 금지(구버전 캡처 파일명만 예외).
> - ⚠️ **Supabase 미검증 · Figma 0건 · 캡처 8종(C_01 없음) · 커밋 1인 명의.** 넷 다 발표에서 사실대로 말한다.

원칙: 약점은 먼저 인정하고, 그 다음에 그 약점을 어디에 가둬놨는지 보여준다. 방어하지 말고 설계를 보여준다.

---

## Q1. "GET 요청이 서버 상태를 바꾸는데, REST 규격 위반 아닌가요?"

**한 줄:** 위반 맞습니다. 의도한 Mock 동작이고, 환경변수 하나로 규격에 맞는 경로가 이미 들어 있습니다.

**답변:**
"정확한 지적이고, 인정하고 시작하겠습니다. HTTP 규격상 GET은 safe method여야 하는데, 지금 기본 설정에서 `GET /agent-runs/{run_id}`는 `AgentOrchestrator.advance()`를 호출해서 다음 step 하나를 완료시킵니다. 명백히 safe하지 않습니다.

왜 이렇게 뒀냐면, 3일 범위에서 큐와 워커를 붙이지 않고도 '폴링하면 타임라인이 살아 움직이는' 걸 보여줘야 했고, 폴링 N번이면 정확히 N개가 완료된다는 결정론적 동작이 데모와 테스트 양쪽에 유리했기 때문입니다. e2e도 그 성질에 기대서 폴링 4회를 검증합니다.

중요한 건 **이 동작을 코드 전체에 퍼뜨리지 않고 플래그 하나에 가둬놨다**는 점입니다. `backend/app/core/config.py`의 `BACKGROUND_ADVANCE`를 `true`로 켜면, `backend/app/api/v1/routers/agent_runs.py`의 분기가 바뀌어서 **GET은 리포지토리에서 읽기만 하고, 진행은 FastAPI BackgroundTasks가 2초 간격으로 담당합니다**(`orchestrator.advance_all_in_background`). 즉 규격에 맞는 경로는 이미 구현돼 있고, 기본값만 데모 쪽으로 잡아둔 겁니다.

덧붙이면 `advance()`는 실행이 REVIEW나 FAILED가 된 뒤에는 아무것도 바꾸지 않고 그대로 돌려줍니다. 멱등입니다. 이것도 e2e에 'REVIEW 후 재조회 멱등' 항목으로 들어 있습니다.

실서비스로 가면 BackgroundTasks도 부족하고 Celery나 Redis 큐로 가야 합니다. 거기까지가 확장 계획입니다."

**근거:** `backend/app/services/orchestrator.py` (`advance`, `advance_all_in_background`) · `backend/app/api/v1/routers/agent_runs.py:24` · `backend/app/core/config.py:36,58` · `backend/.env.example:11` · `backend/README.md:59`

**꼬리질문 대비** — "그럼 왜 기본값을 true로 안 했나?" → "BackgroundTasks는 진행 속도가 시간 기반이라 테스트가 sleep에 의존하게 됩니다. `backend/tests/conftest.py`에서 명시적으로 false로 고정해 테스트를 결정론적으로 유지했습니다."

---

## Q2. "AI가 하나도 안 들어갔는데 AI 프로젝트라고 할 수 있나요?"

**한 줄:** 이번 과정 범위가 기획~스캐폴딩이고 AI는 Mock이 요구사항입니다. 대신 AI가 들어갈 구멍을 인터페이스·설정·데이터 세 곳에 전부 뚫어놨습니다.

**답변:**
"네, 지금 LLM 호출은 한 줄도 없습니다. 그게 이번 과정의 요구사항이기도 합니다 — 범위가 기획부터 스캐폴딩까지고, AI 부분은 Mock으로 두고 '확장 가능하게 설계했는가'를 보는 자리로 이해했습니다.

그래서 저희가 증명하려는 건 'AI를 붙였다'가 아니라 **'AI를 붙일 때 무엇을 안 고쳐도 되는가'**입니다. 세 군데를 보시면 됩니다.

첫째, 인터페이스입니다. `backend/app/services/agents/base.py`에 추상 클래스 `AgentService`가 있고 `run(context)` 하나만 있습니다. `mock_agents.py`와 `llm_agents.py`가 **같은 인터페이스를 구현하고**, `get_agent(agent_type, provider)`가 골라줍니다. 오케스트레이터는 구현체를 모릅니다. `AgentContext`에 `prior_results`가 있어서 A3 안전서류가 A2 법령 결과를 받아 쓰는 의존도 인터페이스 안에서 해결됩니다.

둘째, 프롬프트가 코드에 없습니다. `llm_agents.py`의 `load_prompt()`가 `docs/05_ai_ready/prompts.md`에서 해당 에이전트 섹션을 읽어옵니다. 프롬프트를 고치는 데 배포가 필요 없습니다.

셋째, 데이터입니다. `agent_runs`에 `model_name`과 `prompt_version`을 실행마다 저장합니다. 모델을 바꾸면 어떤 판단이 어떤 모델·어떤 프롬프트 버전에서 나왔는지 나중에 추적됩니다. 규제 산업에서는 이게 있어야 감사가 됩니다.

정리하면, AI가 안 들어간 게 아니라 **AI가 꽂힐 소켓을 만들고 지금은 Mock을 꽂아둔 상태**입니다. 소켓이 진짜인지는 `llm_agents.py`가 이미 같은 인터페이스로 자리 잡고 있는 걸로 확인하실 수 있습니다."

**근거:** `backend/app/services/agents/base.py` · `mock_agents.py` · `llm_agents.py` (`load_prompt`, `validate_egress`) · `backend/app/services/agents/__init__.py` (`get_agent`) · `agent_runs.model_name` / `prompt_version`

**꼬리질문 대비** — "llm_agents.py는 껍데기 아닌가?" → "네, `_client()`는 TODO입니다. 다만 프롬프트 로딩과 egress 검증은 실제로 동작합니다. 껍데기라는 지적은 맞고, 3일 범위에서 저희가 증명한 건 '경계선을 어디에 그었는가'까지입니다."

---

## Q3. "Spring Boot로 하기로 해놓고 왜 FastAPI인가요?"

**한 줄:** 강의안 Tool Guide가 Java/Spring Boot, Python/FastAPI, Node/Express를 모두 허용 스택으로 제시했습니다. 그 안에서 고른 겁니다.

**답변:**
"강의안 Tool Guide에 백엔드 허용 스택이 Java/Spring Boot, Python/FastAPI, Node/Express 셋으로 제시돼 있어서 그 안에서 선택했습니다. 규정을 벗어난 건 아닙니다.

FastAPI를 고른 이유는 이 프로젝트의 목적이 **AI 확장 지점 설계**라서입니다. 프롬프트, JSON Schema, 그리고 나중에 붙일 LLM 클라이언트와 RAG 파이프라인이 전부 Python 생태계에 있습니다. 백엔드를 Java로 짜면 AI 부분만 별도 Python 서비스로 갈라져서, 3일 안에 '한 코드베이스에서 Mock을 LLM으로 갈아끼운다'는 걸 보여주기 어려웠습니다.

두 번째 이유는 명세와 구현이 갈라지지 않는다는 점입니다. Pydantic 스키마가 그대로 OpenAPI 3.0 문서가 되기 때문에, API 명세가 코드와 어긋날 수가 없습니다. `/openapi.json`이 200으로 응답하는 것까지 오늘 확인했습니다.

그리고 **아키텍처 자체는 언어 중립적으로 잡았습니다.** 라우터 → 서비스 → 리포지토리 → 모델 4계층인데, Spring의 Controller → Service → Repository → Entity와 1:1로 대응합니다. `AgentService`가 인터페이스고 Mock/LLM이 구현체인 것도 Spring의 인터페이스 주입과 같은 구조입니다. 스택을 Spring으로 옮겨야 한다면 파일이 옮겨가지 설계가 바뀌지는 않습니다."

**근거:** 강의안 Tool Guide · `backend/app/api/v1/routers/` → `services/` → `repositories/` → `models/` 폴더 구조 · e2e "OpenAPI 스키마 200"

---

## Q4. "데모가 전부 Mock인데, 결국 뭘 검증한 건가요?"

**한 줄:** Mock인 건 에이전트의 '판단' 하나뿐이고, 그걸 둘러싼 계약·상태 전이·권한 게이트는 실제 HTTP로 실측합니다.

**답변:**
"Mock인 건 에이전트가 '무엇을 답하는가'뿐입니다. 그 답을 둘러싼 나머지는 전부 실제로 돕니다.

검증은 `bash scripts/e2e_live.sh`로 합니다. 이건 pytest와 다릅니다. **pytest는 TestClient라 네트워크를 안 타지만, 이 스크립트는 실제 uvicorn을 포트에 띄우고 curl로 HTTP를 때립니다. 데모와 같은 조건입니다.** **72건 전부 통과, 실패 0건입니다.** 백엔드 테스트도 30개 전부 통과했습니다.

검증 대상은 크게 넷입니다.
- **권한 분리** — 엔지니어가 승인을 시도하면 `403 FORBIDDEN_ROLE`, 남의 요청을 조회하면 `403 FORBIDDEN_NOT_OWNER`. **'권한이 없다'와 '지금 상태에서는 안 된다'를 코드로 갈랐습니다.**
- **제출 게이트** — 결과 3종이 다 있고, 엔지니어 설명이 있고, **A2 적용 법령이 최소 1건**이어야 제출이 통과합니다. 아니면 `422 SUBMIT_REQUIRED_FIELD_MISSING`. **법령 근거 없이는 승인 대기로 갈 수조차 없습니다.**
- **입력·상태 가드** — 유형별 스펙 키가 안 맞으면 `400 SPEC_SCHEMA_MISMATCH`, 거절 사유가 없으면 `400 REJECT_REASON_REQUIRED`, 진행 중 재실행은 `409 RUN_ALREADY_IN_PROGRESS`, 결정된 건 재결정은 `409 ALREADY_DECIDED`, 제출 후 수정은 `409 IMMUTABLE_STATUS`·`RESULT_LOCKED`.
- **비동기 계약** — `POST /agent-runs`가 202, 폴링하면 A1→A2→A3가 순서대로 DONE, 셋 다 끝나면 서버가 `AI_DONE`으로 전환. **step 하나가 실패해도 HTTP는 200을 유지하고 그 step만 `FAILED`가 됩니다.**

즉 저희가 검증한 건 '**AI가 뭐라고 답하든, 근거와 사람의 결정 없이는 상태가 앞으로 못 간다**'는 겁니다. AI를 진짜로 붙였을 때 위험한 게 바로 이 게이트인데, 그건 Mock이 아닙니다."

**근거:** `scripts/e2e_live.sh` (재현: `bash scripts/e2e_live.sh`, 종료코드가 실패 건수) · `backend/tests/` · CONTRACT §3·§6

**한 가지 더 말할 것**: "이 E2E는 각 항목이 **계약서 조항 번호에 매핑**돼 있습니다. 로그를 열면 '1. 인증, 계약 §4 #1~#3' 식으로 찍힙니다. **계약이 지켜졌는지를 검증한 거지 코드가 안 죽는지를 본 게 아닙니다.**"

**⭐ 이어서 말할 것 (사고 I-09)**: "그리고 저희는 **이 72건이 실제로 비교를 하고 있는지**도 확인했습니다. 검사 10곳이 인자를 잘못 받아 **실패 경로에서 조용히 통과**할 수 있는 상태였고, 전부 고쳤습니다. **통과 개수는 검사가 비교하고 있다는 증거가 아닙니다.**"

**⚠️ 정직성**: 여기에 **Supabase는 포함되지 않는다.** 물으면 "스키마는 PostgreSQL DDL로 썼고 실행 검증은 못 했습니다"라고 말한다.

---

## Q5. "일주일을 하루로 — 이 숫자의 근거가 뭔가요?"

**한 줄:** 측정치가 아닙니다. 현업 경험 기반 가정이고, 그래서 관련 KPI를 화면과 API에서 아예 지웠습니다.

**답변:**
"측정치가 아니라는 것부터 말씀드리겠습니다. **'일주일'은 저희 팀원의 현업 경험에서 나온 추정이고, '하루'는 목표 가정입니다.** 파일럿을 돌려서 잰 값이 아닙니다.

그리고 여기에 저희가 한 판단이 하나 있습니다. **어제 버전에는 대시보드에 '평균 승인 소요시간'과 'As-Is 대비 몇 % 단축' KPI가 있었습니다. 데모 첫 대사가 그 숫자였습니다.** 그런데 그 값은 시드 데이터 한 건으로 계산된, 표본 1짜리 숫자였습니다.

**아직 측정할 수 없는 숫자를 대시보드에 띄워두는 건, 저희가 문제로 지목했던 '근거 없이 답하는 사내 AI'와 같은 일이라고 봤습니다. 그래서 오늘 지웠습니다. 화면에서만 숨긴 게 아니라 API 응답에서도 없앴습니다.**

지금 엔지니어 대시보드에 남은 KPI는 작성 중·진행 중·승인 대기·반려 넷이고, 전부 **행을 세면 나오는 값**입니다. 안전관리자 쪽은 승인 대기·오늘 처리·이번 달 승인·이번 달 거절, 그리고 거절 사유 TOP5입니다. **추정이 섞이지 않는 값만 남겼습니다.**

단축 효과의 실제 숫자는 고객사에서 몇 달 돌려야 나옵니다. 그때 `approvals` 테이블에 `decided_at`이 쌓여 있으니 계산은 언제든 붙일 수 있습니다. **다만 데이터가 쌓이기 전에 그 숫자를 화면에 먼저 띄우지는 않겠다는 게 저희 결정입니다.**"

**근거:** CONTRACT §4-4(엔지니어 대시보드에 평균 승인 소요시간 없음) · §5 `approvals.decided_at`

**꼬리질문** — "그럼 이 서비스의 효과는 어떻게 증명하나?" → "지금은 증명하지 않습니다. 저희가 증명한 건 **효과를 측정할 수 있는 데이터 구조가 들어가 있다는 것**까지입니다. `approvals`가 append-only라 재제출·재결정까지 전부 시각과 함께 남습니다."

---

## 별건 — qa_bank.md에 사실과 다른 답이 하나 있다 (담당자 수정 필요)

`docs/09_qa/qa_bank.md` E섹션 "R&R은 어떻게 나눴나" 행의 근거가 **"GitHub feature 브랜치로 각자 커밋 확인 가능"**으로 적혀 있는데, 오늘 레포 실측 결과와 다르다.

```
$ git branch -a          →  main 하나뿐 (원격도 origin/main)
$ git shortlog -sn --all →  11  jang961111-hash   (기여자 1명)
```

루브릭 1-3에 "5명 전원 커밋 존재, 편중 없음(`git shortlog -sn`)"과 "PR 5건 이상"이 명시돼 있어서, 채점자가 GitHub Insights를 열면 바로 드러난다. **발표에서 "역할별 feature 브랜치로 각자 커밋이 남게 했다"고 말하면 안 된다** — 대본에서는 해당 문장을 삭제하고 커밋 11건·파일 126개로 바꿔놨다.

- 이 문서는 `docs/08_presentation/` 소유라 `qa_bank.md`를 직접 고치지 않았다. **PM·DevOps 담당이 판단할 사항이다.**
- 선택지는 둘이다. (a) 발표 전까지 각자 계정으로 커밋·PR을 실제로 남긴다. (b) 남기지 못하면 회고 섹션에서 "GitHub 협업 규칙을 문서화했으나 3일 일정상 단일 브랜치로 작업했다"고 **먼저 인정한다.** 어느 쪽이든 사실과 다른 주장을 하는 것보다 낫다.
