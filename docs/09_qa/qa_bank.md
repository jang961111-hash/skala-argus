# Q&A 뱅크 — 심사 교수·동료 예상 질문과 답변

발표자용. 답은 20초 안에 끝나게, 근거 파일을 같이 말한다.

## A. 기획·페르소나

| 질문 | 답 | 근거 |
|---|---|---|
| 왜 반도체 협력사인가, 하이닉스 본사가 아니라? | 하이닉스는 GaiA·AMOS로 이미 폐쇄망 에이전트를 운영 중. 협력사는 같은 규제(유해가스·중대재해법)를 받지만 AI 조직이 없다. 하이닉스가 2·3차 협력사 스마트팩토리 컨설팅에 1.4조를 배정한 2026-07이 진입 시점. SK AX 채널과도 맞다 | planning_final §3 |
| 페르소나가 둘인데 화면은 두 개뿐? | 같은 상세 화면을 역할 토글로 다르게 보여준다. 엔지니어는 타임라인·승인 요청, 안전관리자는 승인 패널. 화면 수를 늘리는 것보다 한 화면에서 두 역할이 만나는 걸 보여주는 게 이 서비스의 본질(메신저 왕복 대체) | wireframe.html |
| 일주일→하루라는 수치 근거는? | As-Is는 팀원 현업 경험 기반 추정이고, 목표치는 가정이다. 벤치마크로 Siemens Industrial Copilot 파일럿 대응정비 25% 단축, 하이닉스 자율형 팹 결함분석 50% 단축을 인용한다. 발표에서 "가정"이라고 명시한다 | §2 |
| 스마트글라스는 어디 갔나? | 실습교수님 피드백으로 검토했고, 팹 카메라 금지·HoloLens 단종 등 제약을 조사한 뒤 "필수가 아닌 선택 채널"로 내렸다. 같은 API의 `/glass` 라우트로 확장 가능 | E안v2 부록 |

## B. AI-Ready·에이전트

| 질문 | 답 | 근거 |
|---|---|---|
| 에이전틱이라면서 사람이 다 승인하면 자동화가 아니지 않나? | 일주일 중 5일이 정보수집·서류·문의고, 그걸 에이전트가 한다. 승인(판단)만 사람. 산업안전 규제상 승인 주체는 사람이어야 하고, 그게 설계 요건이다 | §4 |
| 에이전트 4개가 병렬인데 의존성은? | A3 안전서류는 A2 법령 결과가 필요하다. 오케스트레이터 정책에 의존 그래프(A1·A2 병렬 → A3 → A4)를 정의했고, Mock은 순차 전이로 단순화했다 | prompts.md §5 |
| Mock인데 AI 확장 지점이 검증된 건가? | 프롬프트 4개와 출력 JSON Schema를 작성했고, 샘플 출력이 스키마를 통과하는 것과 잘못된 값(`required:"MAYBE"`, step 순서 뒤바뀜)이 거부되는 것을 jsonschema로 검증했다. Playground 검증 절차도 문서화 | 05_ai_ready |
| 법령 답변이 틀리면 책임은? | 조문 인용 없는 답은 표시하지 않고, 근거 못 찾으면 `required=UNKNOWN`으로 안전관리자에게 넘긴다. `legal_findings`는 건별 스냅샷이라 나중에 감사 가능. AI는 보조수단 | prompts.md §0 |
| 외부 클라우드 못 쓰면 LLM은 뭘 쓰나? | `ai_configs.provider=LOCAL_LLM`(사내 GPU, OpenAI 호환 엔드포인트) 또는 SK AX A.X 플랫폼. `egress_allowed=false`면 OPENAI 설정 자체가 409로 거부된다. 하이닉스 GaiA가 폐쇄망 선례 | config.py, ai_config router |
| 법령 데이터는 어떻게 넣나? | 법제처 국가법령정보 Open API(공개)로 산안법·화관법·고압가스법 조문을 사내 `law_index`에 적재. 개정 시 재적재, 과거 판단은 `legal_findings`에 보존 | erd.md |

## C. 아키텍처·API

| 질문 | 답 | 근거 |
|---|---|---|
| 왜 202 + 폴링이지 WebSocket/SSE가 아닌가? | 3일 범위에서 폴링이 가장 단순하고 Mock 서버(Postman)와도 호환된다. 실제 LLM은 분 단위라 3초 폴링이면 충분. SSE는 확장 항목 | api_spec.md |
| 409와 422 구분 기준? | "내가 보낸 값을 바꾸면 되는가" — 서류 누락은 값을 채우면 되니 422, 체크리스트 미완료 승인·완료된 요청 재실행은 상태를 바꿔야 하니 409 | api_spec.md |
| Mock을 LLM으로 바꾸면 뭐가 바뀌나? | `services/agents/mock_agents.py` → `llm_agents.py` 구현체 교체와 `ai_configs.provider` 값. 라우터·스키마·FE는 그대로 | architecture.md 확장 표 |
| 비동기를 큐 없이 했는데 Asynchronous Pipeline 맞나? | 엔드포인트 계약(202→폴링→상태 전이)이 비동기다. 현재는 GET마다 step을 전이시키는 Mock, `BACKGROUND_ADVANCE=true`면 BackgroundTasks로 자동 진행. 큐는 확장 | orchestrator.py |

## D. ERD·데이터

| 질문 | 답 | 근거 |
|---|---|---|
| 테이블 14개면 3일에 과하지 않나? | 마스터 6 / 트랜잭션 4 / AI 3 / 설정 1로 나뉘고, 데모가 실제로 쓰는 건 work_requests·agent_runs·documents·approvals 4개. 나머지는 DDL·seed로 존재하며 확장 지점을 보여주는 용도 | erd.md |
| steps_json이 JSON인데 정규화 위반 아닌가? | 에이전트 결과는 스키마가 진화하므로 JSON, 검색·집계가 필요한 것만 승격(overall_status, model_name, legal_findings 테이블). 3NF는 마스터·트랜잭션 테이블에서 지킨다 | erd.md 정규화 절 |
| N:M은 어디? | equipments↔parts는 `equipment_parts`(설치 이력 속성 포함), parts↔parts는 `part_compatibility`(자기참조, 유독가스 허용 여부 속성) | replaceflow.dbml |

## E. 구현·데모·팀

| 질문 | 답 | 근거 |
|---|---|---|
| 데모가 Mock인데 뭘 검증한 건가? | FE→BE→DB 실연동이다. BE는 SQLite에 실제 행을 쓰고 상태머신·체크리스트 게이트가 코드로 동작한다. Mock인 건 에이전트의 "생각" 부분뿐 | test_flow.py |
| 백엔드가 죽으면? | FE `dev:mock` 모드(동일 계약)로 30초 내 전환, 그것도 안 되면 wireframe.html 애니메이션 | e2e_test_checklist 리허설 절 |
| R&R은 어떻게 나눴나, 발표자가 BE인데 | 발표자가 API·에이전트 JSON 설계에 직접 참여해 Q&A 대응. GitHub feature 브랜치로 각자 커밋 확인 가능 | rnr_and_schedule.md |
| 3일 동안 가장 어려웠던 점은? | (각자 준비) 예: 필드명·상태값을 5명이 동일하게 쓰는 것 → CONTRACT.md 한 장으로 해결 | CONTRACT.md |

## F. 우리가 다른 조에 할 질문
- "Mock을 실제 LLM으로 바꿀 때 프론트 코드는 몇 줄 바뀌나요?"
- "AI 결과를 사람이 뒤집은 기록은 어디 남고 다음 응답에 반영되나요?"
- "외부 API를 못 쓰는 고객사라면 어느 설정을 바꾸면 되나요?"
