# Argus 서비스 기획서 (최종본)
## 반도체 설비 부품 교체 "승인 프로세스" 에이전트 — AI-Ready 웹 서비스 설계

| 항목 | 내용 |
|---|---|
| 과정 | SKALA 4기 Full-Stack Engineering · AI 웹 서비스 설계 Mini-project (2026-09-02 ~ 09-04) |
| 팀 | PM 은태현 / Product&UX·FE 문승은 / DevOps&Infra 신서현 / API Architect·BE 정구현 / BE·발표 장병헌 |
| 문서 버전 | **v3.0 (2026-09-03)** — 팀 노션 「API 명세서 v1.0」+「FixGuide 데이터 모델 정의서 v3.0」+「WRA 화면정의서 v2.0」 원문 기준 |
| ⚠️ 명칭 미확정 | ERD 문서 제목은 **FixGuide**, 저장소·본 기획서는 **Argus**, API 명세서는 "부품 교체 요청·승인 시스템". **팀 확인 필요.** 확정 전까지 이 문서는 `Argus`를 유지한다(CONTRACT.md v3.0 상단 경고와 동일) |
| 프레임 | 우리는 SK AX AI 도메인팀 — 유해가스 취급 설비를 가진 반도체 제조사(하이닉스 협력사·후공정)에 B2B AX 솔루션을 제안한다 |
| 관련 산출물 | `docs/02_usecase`(UC 명세·다이어그램) · `docs/03_wireframe`(와이어프레임, `figma_build_guide.md`) · `docs/04_architecture`(아키텍처·상태머신·시퀀스) · `docs/05_ai_ready`(프롬프트·JSON Schema) · `docs/06_erd`(DBML·DDL·seed) · `docs/07_api`(OpenAPI·API 명세) · `postman/`(Mock) · `frontend/` · `backend/` · `docs/08_presentation`(발표) · `docs/09_qa`(E2E·자체점검·Q&A) |

### 변경 이력
| 버전 | 일자 | 내용 |
|---|---|---|
| v0.1 | 09-02 오전 | E안 "협력사 설비 알람→정비 가이드 에이전트" 초안 |
| v0.2 | 09-02 오후 | 실습교수님 피드백 반영 — 스마트글라스·RAG·QR/YOLO, 법령·규격·교체시기·호환 레이어 전수조사 |
| v0.3 | 09-02 오후 | 팀 회의 반영 — 문제를 "교체 승인 프로세스(규격·법령·승인) 일주일"로 재정의, 에이전트 4개+오케스트레이터, 온프레미스 전제, 스마트글라스는 선택 채널 |
| v1.0 | 09-02 저녁 | 최종본. 전 산출물(UC·와이어프레임·아키텍처·ERD·API·Mock·FE/BE 스캐폴딩)과 필드·상태값 정합화(`docs/CONTRACT.md`) |
| v2.0 | 09-03 오후 | 오케스트레이터가 화면정의서에서 **추론**해 작성 — 팀 권위 문서와 불일치해 **폐기**(`CONTRACT_v2.0_superseded.md`) |
| **v3.0** | **09-03** | **팀 노션 「API 명세서 v1.0」+「FixGuide 데이터 모델 정의서 v3.0」+「WRA 화면정의서 v2.0」을 그대로 반영. 에이전트 코드 SPEC/LEGAL/SAFETY_DOC→`A1`/`A2`/`A3`, 상태값 8종→6종(`DRAFT`·`AI_RUNNING`·`AI_DONE`·`PENDING`·`APPROVED`·`REJECTED`), 결과 구조를 에이전트별 고유 스키마에서 통일 구조(`items[]`/`documents[]`)로 단순화, API 15개 확정, 법령·설비·부품 마스터는 전부 Phase 2. 근거: `docs/CONTRACT.md` v3.0(255줄)** |

### 목차
1. 서비스 한 줄 정의 · 2. 문제 정의(As-Is) · 3. SK AX 연결 · 4. 에이전틱 AI 배치 · 5. Actor·Use-Case · 6. 핵심 화면 · 7. AI-Ready 설계 · 8. 아키텍처 · 9. ERD · 10. REST API · 11. 일정·R&R · 12. 한계·확장 · 13. 예상 Q&A · 14. 교수님 확인 사항 · 15. 산출물 목록과 루브릭 매핑

---

## 1. 서비스 한 줄 정의

**"설비 이상이 확인되면, 엔지니어가 작업요청 하나만 올리면 AI 에이전트가 부품 규격·호환 확인, 적용 법령 조사, 안전 서류 초안, 벤더 견적 요청까지 병렬로 처리하고, 안전관리자는 근거가 붙은 승인 패널에서 결재만 하는 — 일주일 걸리던 교체 승인을 하루로 줄이는 에이전트."**

가칭: **Argus** (설비 부품 교체 승인 에이전트)

- 고객사(1호 레퍼런스): SK하이닉스 협력사 또는 후공정 라인 — 특수가스·유해화학물질 취급 설비(가스 캐비닛, 밸브, 배관, 스크러버)를 가진 제조사 1곳
- 페르소나 2명: **설비 엔지니어**(요청자) + **안전관리자**(승인자)
- AI의 역할: 정보를 모으고 서류를 초안하는 **에이전트 팀**. 판단·승인·발주 확정은 사람.

## 2. 문제 — 현업이 말한 그대로

팀원 현업 경험(팹 가스 라인)을 As-Is로 옮기면 이렇다.

| 단계 | 지금 하는 일 | 소요 |
|---|---|---|
| ① 이상 감지 | 모니터에서 가스 유량·압력 이상 → 특정 공정 확인 | 반나절 |
| ② 현장 확인 | 담당자가 직접 가서 진짜 이상인지 확인 → "밸브 고장, 교체 필요" | 반나절 |
| ③ 규격 확인 | 벤더에 전화, 규격이 기존과 동일한지·호환되는지 확인, 견적 요청 | 1~2일 |
| ④ 법령 조사 | 유해물질 취급 설비라 산업안전보건법·화학물질관리법·고압가스법 중 뭐가 걸리는지, 작업허가·위험성평가·MSDS·LOTO가 필요한지 직접 검색 | 1~2일 |
| ⑤ 안전관리자 승인 | 사내 메신저로 자료 보내고 질의응답 반복 → 승인 | 1~2일 |
| ⑥ 교체 | 실제 작업 | 1~2시간 |

**③④⑤가 일주일, ⑥은 두 시간.** 그리고 사내 AI에 물어봐도 "법 관련 데이터가 부실하고 질문을 잘 못 알아들어서" 결국 직접 찾는다. 외부 클라우드 AI는 보안상 못 쓴다.

→ 문제의 본질은 정비 기술이 아니라 **분산된 정보(규격·법령·승인)를 사람이 손으로 모으는 과정**이고, 해결책은 **온프레미스에서 돌아가는, 법령 지식이 미리 들어있는 에이전트**다.

## 3. SK AX 연결 (발표 근거)

| 근거 | 내용 | 출처 |
|---|---|---|
| SK하이닉스 자율형 팹 2030 (2026-03) | 오퍼레이셔널 AI로 숙련 엔지니어 노하우 데이터화, 설비 유지보수 처리시간 50%+ 단축 | https://www.ajunews.com/view/20260318105505267 |
| SK하이닉스 GaiA (2025-08) | 폐쇄망 LLM Chat, 장비 보전 에이전트, 정책·기술 분석 에이전트 — **온프레미스 에이전트 선례** | https://www.m-economynews.com/news/article.html?no=58581 |
| SK하이닉스 협력사 지원 (2026-07) | 5년 1.4조, 2·3차 협력사 스마트팩토리 전환 컨설팅 | https://www.ajunews.com/view/20260702162310993 |
| SK AX AXgenticWire (2026-03) | 멀티에이전트 운영환경, 거버넌스·보안 포함 풀스택 — **우리 에이전트가 얹히는 플랫폼** | https://www.thelec.net/news/articleView.html?idxno=5972 |
| SK AX CEO 안심 패키지 (2025-12) | AI 중대재해 예방 솔루션 — 안전관리자 워크플로우와 접점 | https://www.newswire.co.kr/newsRead.php?no=1025398 |
| SK AX 2026 비전 | "AI를 도입하는 기업에서 **AI가 일하는 기업**으로" | https://www.newspim.com/news/view/20260616001120 |
| 법제처 국가법령정보 Open API | 법령·시행령·시행규칙 전문 공개 API → **온프레미스에 사전 인덱싱 가능** (사내 AI의 "법령 데이터 부실"을 해결하는 근거) | https://open.law.go.kr |
| 화학물질안전원 반도체 제조업종 취급시설 고시 (2022-20) | 가스캐비닛·배관·감지경보 점검 규정 | https://www.law.go.kr/LSW/admRulLsInfoP.do?admRulSeq=2100000216699 |
| 산업안전보건기준에 관한 규칙 | 91조(고장 기계 정비), 92조(정비 시 운전정지·LOTO), 93조(방호장치 해체 금지), 319조(정전 전기작업) | https://www.law.go.kr/lsLinkCommonInfo.do?lspttninfSeq=75618&chrClsCd=010202 |

**White Space**: 시중에 "규격+법령+승인"을 한 번에 처리하는 에이전트는 없다(팀 조사). 있어도 외부 클라우드 기반이라 팹에서 못 쓴다. 온프레미스 + 법령 사전 인덱싱 + 승인 워크플로우 결합이 공백.

## 4. 에이전틱 AI를 어디서 어떻게 보여주는가 (발표의 핵심 장면)

작업요청 1건이 들어오면 **오케스트레이터가 3개 전문 에이전트를 병렬로 실행**하고, 화면에 각 에이전트의 진행 상태가 실시간으로 바뀐다. 결과는 엔지니어가 항목 단위로 검토·편집한 뒤, 안전관리자 승인 화면에 근거가 붙은 결재 요청으로 넘어간다. 이 "AI 검증 진행" → "결과 확인·수정" 화면이 데모의 클라이맥스다.

| 에이전트 | 코드 | 하는 일 | 입력 | 출력 |
|---|---|---|---|---|
| 규격·호환 에이전트 | **`A1`** | 엔지니어가 입력한 `specJson`이 요구 스펙을 충족하는지 판정(예: 압력 등급 3000 psi ≥ 요구 2500 psi). **부품 마스터·호환표는 Phase 2**라 실 재고·대체품 대사는 하지 않는다 | 서버가 구성한 요청 스냅샷(설비·라인·물질·운전조건·제품명·유형·`specJson`·사진 메타) | `items[]` (`{itemId, text, edited}`) |
| 법령 에이전트 | **`A2`** | 취급 물질·설비·운전조건으로 적용 법령 조문 인용, 필요 절차 정리. **법령 마스터 DB는 Phase 2**라 정적으로 내장된 참고 조문(시드)을 근거로 답한다 | 위와 동일 스냅샷 | `items[]` (`{itemId, text, edited}`) |
| 안전서류 에이전트 | **`A3`** | 작업허가서 등 안전서류 초안 생성 | `A2` 결과 + 스냅샷 | `documents[]` (`{docId, type, name, content, edited}`) |
| 오케스트레이터 | — | `agent_runs`/`agent_steps` 생성·상태 관리, `workRequestId`로 스냅샷 구성, 결과 통합 | 작업요청 등록 시 입력 전체 | `AgentRun`(`steps[]`·`allDone`·`pollIntervalMs`) |

핵심 설계: 에이전트는 **정보를 모으고 초안을 쓸 뿐** 승인을 실행하지 않는다. 엔지니어가 결과를 `items[]`/`documents[]` 단위로 편집(`edited=true`, AI 원본과 화면에서 시각적으로 구분)한 뒤, 안전관리자가 승인해야 다음 단계가 열린다 — Human-in-the-loop. 3일 범위에서는 3개 에이전트 모두 Mock이고 오케스트레이션 구조·상태머신·JSON 계약이 실제 산출물.

**A4 벤더 에이전트는 Phase 2다.** 벤더 견적(RFQ)은 벤더 포털·이메일 같은 외부 시스템 연동이 전제인데, 이는 우리 서비스의 온프레미스 전제(`ai_configs.egress_allowed=false` 기본)와 정면으로 충돌한다. 3일이라는 범위에서 이를 Mock으로 흉내 내면(예: 고정된 가짜 RFQ 문구) "이 에이전트가 실제로 무엇을 하는가"라는 질문에 대한 답이 가짜가 되고, 이는 실제 법령·규격 데이터에 기반해 동작해야 할 나머지 3개 에이전트의 근거 품질까지 함께 의심받게 만든다. 그래서 A4를 빼는 쪽이 남은 3개 에이전트의 신뢰도를 지키는 선택이라고 판단했다(상세: `docs/02_usecase/usecase_spec.md` §3.5).

## 5. Actor 및 Use-Case

**v3.0은 12개 UC다(회원가입·로그인·임시저장·사진업로드·결과편집·재제출은 유효, 지식 관리 UC는 대응 API가 15개 안에 없어 삭제). `Role`은 `ENGINEER`·`SAFETY_MANAGER` 2종뿐 — `BUYER`·`ADMIN`은 v3.0 도메인에 없다. 전체 명세는 `docs/02_usecase/usecase_spec.md` 참조 — 여기서는 요약만 남긴다.**

| Actor | 설명 |
|---|---|
| 미인증 방문자 | 회원가입·로그인만 수행 |
| 설비 엔지니어 (`ENGINEER`) | 요청 등록(동적 스펙+사진)·임시저장, AI 결과 확인·편집, 제출, 거절 시 재제출 |
| 안전관리자 (`SAFETY_MANAGER`) | AI 결과(항상 읽기전용 `editable:false`)·설명 검토, 승인/거절(+사유) |
| 모니터링 시스템(외부, 선택) | 이상 알람(Mock 입력) |
| 에이전트 서비스(외부/Mock) | `A1`·`A2`·`A3` (`A4` 벤더는 Phase 2) |

| UC | 이름 | Actor | 흐름 (API #, CONTRACT §4) |
|---|---|---|---|
| UC-01·02 | 회원가입·로그인 | 미인증 방문자 | #1·#2·#3 — 로그인 성공 시 서버가 `redirectPath`로 역할 분기 |
| UC-03~05 | 요청 등록·임시저장·사진업로드 | 엔지니어 | #5·#8·#9·#11 — 등록 즉시 AI 검증 자동 트리거 → `AI_RUNNING` |
| UC-06 | AI 검증(`A1`·`A2`·`A3`) | 시스템 | #12 폴링(`pollIntervalMs:2500`) → `allDone` → `AI_DONE` |
| UC-07·08 | 결과 확인·편집, 제출 | 엔지니어 | #13(전체 치환) · #14 → `PENDING` |
| UC-09 | 승인/거절 | 안전관리자 | #15 — 체크리스트 없이 승인 즉시, 거절은 사유(10자↑) 필수 → `APPROVED`/`REJECTED` |
| UC-10 | 거절 사유 확인 후 재제출 | 엔지니어 | #6·#7·#14 재호출 → `PENDING` 복귀, 직전 `approvals` 이력 보존 |
| UC-11·12 | 대시보드, 내 요청 목록 | 엔지니어/안전관리자 | #4·#6 — 역할별 KPI(엔지니어는 평균 승인시간 없음), `status` 다중 필터 |

## 6. 핵심 화면 9개 (CONTRACT v3.0 §7 화면↔API 매트릭스)

v1.0의 화면 2개(목록/대시보드, 상세=타임라인+승인패널)가 **역할별 GNB·플로우 분리**로 9개 화면이 됐다. 화면 구성 자체는 화면정의서 v2.0 기준으로 v2.0 문서 때와 동일하고, v3.0에서 바뀐 것은 각 화면이 호출하는 API 번호·필드명(camelCase)·상태값(6종)이다.

| Screen ID | 경로 | 역할 | 비고 |
|---|---|---|---|
| `WRA_C_00` | `/login` | 공통 | 성공 시 역할 분기 → E_01 / S_01 |
| `WRA_C_01` | `/signup` | 공통 | 역할 선택 필수(엔지니어/안전관리자) |
| `WRA_E_01` | `/home` | 엔지니어 | KPI 4(작성중·진행중·승인대기·반려) + 최근 요청. **평균 승인시간·진행률 컬럼 없음** |
| `WRA_E_02` | `/requests/new` | 엔지니어 | 제품 유형 5종 동적 스펙 + 사진 업로드 |
| `WRA_E_03` | `/requests/{id}/run` | 엔지니어 | 에이전트 **3종** 카드, 2~3초 폴링 |
| `WRA_E_04` | `/requests/{id}/result` | 엔지니어 | 결과 **편집**(항목 추가/삭제/편집) + 설명 작성 후 제출 — **데모 클라이맥스** |
| `WRA_E_05` | `/my/requests` | 엔지니어 | 상태 탭 필터, 거절 사유 열람·재제출 |
| `WRA_S_01` | `/manage/requests` | 안전관리자 | KPI 4 + 승인 대기 목록 + 거절 사유 TOP5 |
| `WRA_S_02` | `/manage/requests/{id}` | 안전관리자 | AI 결과 **읽기 전용** + 승인/거절+사유 — **데모 클라이맥스** |

**데모 시나리오(핵심 흐름)**: 로그인(엔지니어) → `WRA_E_02`에서 제품 유형 선택(동적 스펙 전환) + 사진 첨부 → 'AI 검증 시작' → `WRA_E_03`에서 3개 카드가 2~3초 간격으로 완료 → `WRA_E_04`에서 결과를 직접 편집(예: 서류 누락 항목 채우기) → 설명 작성 후 제출 → 안전관리자 계정으로 전환 → `WRA_S_01`에서 승인 대기 건 클릭 → `WRA_S_02`에서 AI 결과(읽기전용)·사진 확인 → 승인 → 상태 `APPROVED`.

`WRA_E_04`(결과 편집)가 v1.0 대비 가장 큰 변화다. v1.0은 "서류의 누락 항목만 보완"이었지만 v2.0은 A1/A2/A3 결과 전체를 엔지니어가 항목 단위로 고칠 수 있고, 고친 항목은 `edited=true`로 AI 원본과 화면에서 시각적으로 구분된다 — Human-in-the-loop 원칙을 화면으로 가장 직접 증명하는 지점이다.

체크리스트 4항목 blocking(v1.0 `WRA_S_02` 승인 게이트)은 v2.0에서 **완전히 삭제**되고 승인/거절(사유 필수) 2択으로 단순화됐다. `/glass` 선택 채널은 v2.0 화면정의서에 언급이 없어 이번 범위에서 제외한다.

와이어프레임 상세는 `docs/03_wireframe/wireframe_spec.md`(요소·API 매핑 표), Figma 제작 지시는 `docs/03_wireframe/figma_build_guide.md`(디자인 토큰·컴포넌트·AC 매핑, UX 담당 산출물) 참조.

## 7. AI-Ready 설계 포인트 (v3.0)

| 원칙 | 설계 |
|---|---|
| Interface First | FE는 `GET /agent-runs/{runId}`(API#12) JSON만 안다. `AgentOrchestrator` + **3개**(`A1`/`A2`/`A3`) 에이전트 인터페이스, 지금은 Mock 구현체, 추후 LLM 구현체로 교체해도 FE 변경 0 |
| **사실/추론/행동 3층 분리** | 입력(`work_requests`) · AI 산출(`agent_runs`/`agent_steps`/`agent_results`) · 사람 결정(`approvals`)을 테이블로 분리하고 **위 층이 아래 층을 덮어쓰지 않는다**(팀 ERD 원칙 그대로). `agent_steps`(오케스트레이터가 초 단위 갱신)와 `agent_results`(엔지니어가 편집)를 굳이 나눈 이유도 갱신 주체·주기가 달라 같은 행을 UPDATE 경합시키지 않기 위함 |
| Asynchronous Pipeline | `POST /agent-runs`(API#11, body `{workRequestId}`) → 202. `GET /agent-runs/{runId}`(API#12) → `steps[]`(`WAITING/RUNNING/DONE/FAILED`) + `allDone` + `pollIntervalMs:2500`(서버가 값을 내려줌). step 하나가 실패해도 HTTP는 200 유지, 해당 step만 `FAILED`+`errorMessage` |
| **AI 원본 보존 (신규)** | `agent_results.original_json`에 AI 최초 생성 스냅샷을 보존하고 `payload_json`이 수정본이 된다(CONTRACT는 [제안]으로 적었지만 실측: `backend/app/models/agent.py`에 이미 컬럼으로 구현됨) — "`edited:true`만 있으면 무엇이 바뀌었는지 알 수 없다"는 팀 ERD 근거의 DB 구현. `docs/05_ai_ready/prompts.md`의 가드레일(수정본을 AI 원본과 시각적으로 구분)과 한 세트로 서술 |
| Security & Config Isolation | `ai_configs`[제안]: `agentCode`·`provider`(MOCK/LOCAL_LLM/OPENAI)·`modelName`·`promptVersion`·`temperature`·`maxTokens`·`egressAllowed`(default false)·`isActive`(부분 유니크 `UNIQUE(agentCode) WHERE isActive`). **API 키는 테이블에 없다 — 환경변수로 관리**. `promptVersion`은 `docs/05_ai_ready/prompts.md` 실제 버전(`argus-v0.3`)과 매칭 |
| 인증·역할 분리 | `users.password_hash`(bcrypt), JWT Bearer. 가입 시 역할(`ENGINEER`/`SAFETY_MANAGER`) 선택이 로그인 응답의 `redirectPath`(서버 계산)로 화면을 분기시킨다 |
| Human-in-the-loop 결과 편집 | 엔지니어가 `A1`/`A2`/`A3` 결과를 `PATCH /agent-results/{id}`(API#13, **전체 치환**)로 편집. `items[]`/`documents[]`의 개별 `edited`가 true가 되어 화면에서 AI 원본과 시각적으로 구분됨. `PENDING`/`APPROVED`에서는 409 `RESULT_LOCKED`로 잠김 |
| 동적 스펙 | `productType`(밸브/피팅·튜브/레귤레이터/필터/`ETC`) 별로 `specJson` 필수 키가 다르며, 서버가 불일치 시 400 `SPEC_SCHEMA_MISMATCH`로 검증한다 |

**Phase 2 범위 주의**: 법령·설비·부품 마스터·호환표 테이블이 v3.0 DB 7종에 전혀 없다(CONTRACT §5). `A1`·`A2`는 이 3일 범위에서 마스터 데이터 조인 없이 Mock/정적 참고 데이터로 동작한다 — 상세는 `docs/05_ai_ready/prompts.md`.

전문·JSON Schema는 `docs/05_ai_ready/prompts.md`, `docs/05_ai_ready/schemas/*.schema.json` 참조. (SPEC/LEGAL/SAFETY_DOC·`result_id`·`overall_status` 등 v2.0 필드명은 전부 폐기 — v1.0에 있던 A4 VENDOR 필드도 동일하게 없다)

## 8. 시스템 아키텍처

```
[웹 (Vue 3/Vite)] ◀─REST JSON(camelCase)─▶ ┌───── BE (FastAPI) ─────┐
  C_00/C_01 인증                            │ auth / work-requests    │──▶ [DB PostgreSQL(Supabase)/SQLite]
  E_01~E_05 엔지니어 5화면                    │  / agent-runs / approvals│
  S_01·S_02 안전관리자 2화면                  │ AgentOrchestrator ─┬─ A1(Mock/LLM) │
                                             │                    ├─ A2(Mock/LLM) │
                                             │                    └─ A3(Mock/LLM) │
                                             │ ApprovalService(역할분리, 체크리스트 없음)│
                                             │ Settings(env var): validate_egress()  │
                                             │  — 외부 provider+egressAllowed=false면│
                                             │    기동 자체를 거부(fail-fast)         │
                                             └────────────────────────┘
확장: [Queue] [사내 GPU LLM] [법령·설비·부품 마스터(Phase 2)] [`ai_configs` 테이블(Phase 2 승격 대상)]
```
`/glass` 선택 채널, 법령 인덱스 박스, `VendorAgent`는 v1.0 산출물이며 v3.0 범위에 없다(§4, `docs/02_usecase/usecase_spec.md` §3.5). `ai_configs`는 CONTRACT §10 실측 정정에 따라 미구현이고, 설정 격리는 `backend/app/core/config.py`의 환경변수 계층 + `validate_egress()` fail-fast로 대체 구현돼 있다.

## 9. ERD (8테이블 — CONTRACT §5)

| 테이블 | 주요 컬럼 | 관계 |
|---|---|---|
| `users` | id(uuid) PK, name, email UNIQUE, password_hash(bcrypt), role(`ENGINEER`\|`SAFETY_MANAGER`), created_at | 1:N work_requests, approvals |
| `work_requests` | id PK, **request_no UNIQUE**(`WR-YYYYMMDD-NNN`), requester_id FK, equipment, line, substance, operating_condition(jsonb), product_name, product_type, spec_json(jsonb), symptom, site_memo, engineer_note, status(6종) default DRAFT, created_at/updated_at/submitted_at | 1:N photos·agent_runs(재실행)·approvals(append-only) |
| `work_request_photos` | id PK, work_request_id FK, file_name, storage_key, thumbnail_key, size, uploaded_at | 최대 5장 |
| `agent_runs` | id PK, work_request_id FK, status(RUNNING/DONE/FAILED), started_at/finished_at, **input_snapshot(jsonb) — 구현됨**, ai_config_id FK(미구현) | 1:N agent_steps(고정3)·agent_results(고정3) |
| `agent_steps` | id PK, run_id FK, agent_code(A1/A2/A3), status(WAITING/RUNNING/DONE/FAILED), message, error_message, started_at/finished_at, **UNIQUE(run_id, agent_code)** | |
| `agent_results` | id PK, run_id FK, agent_code, payload_json(jsonb), edited bool, updated_at, **original_json(jsonb) — 구현됨**, **UNIQUE(run_id, agent_code)** | |
| `approvals` | id PK, work_request_id FK, approver_id FK, decision(APPROVE/REJECT), reason, reason_category(varchar30, 자유입력), decided_at | append-only(재제출 후 재결정도 새 행) |
| `ai_configs` **[제안·미구현]** | agent_code, provider(MOCK/LOCAL_LLM/OPENAI), model_name, prompt_version, temperature, max_tokens, egress_allowed default false, is_active | CONTRACT §10: 설정 격리는 현재 env var 계층으로 실구현, 이 테이블은 멀티테넌트 확장 시 승격 대상 |

**N:M 없음(팀 ERD 명시)**: 법령·설비·부품 마스터·호환표가 전부 Phase 2라 v3.0 8테이블은 전부 1:N이다(D-07, 루브릭 리스크는 `erd.md`에서 완화 방안 서술). 사실(`work_requests`)/AI 산출(`agent_runs`·`agent_steps`·`agent_results`)/사람 결정(`approvals`) 3층 분리, append-only 이력이 정규화 포인트다.

## 10. REST API — 15개 (CONTRACT §4)

| # | Method | Path | 화면 |
|---|---|---|---|
| 1 | POST | `/auth/signup` | C_01 |
| 2 | POST | `/auth/login` | C_00 |
| 3 | GET | `/auth/me` | 공통 |
| 4 | GET | `/dashboard/summary?role=` | E_01, S_01 |
| 5 | POST | `/work-requests` | E_02 |
| 6 | GET | `/work-requests?mine=&status=&page=&size=&sort=` | E_01, E_05, S_01 |
| 7 | GET | `/work-requests/{id}` | E_04, E_05, S_02 |
| 8 | PATCH | `/work-requests/{id}` | E_02, E_04 |
| 9 | POST | `/work-requests/{id}/photos` | E_02 |
| 10 | GET | `/work-requests/{id}/photos` | S_02 |
| 11 | POST | `/agent-runs`(최상위, body `{workRequestId}`) | E_02 |
| 12 | GET | `/agent-runs/{runId}` | E_03 |
| 13 | PATCH | `/agent-results/{id}`(전체 치환) | E_04 |
| 14 | PATCH | `/work-requests/{id}/submit-approval` | E_04 |
| 15 | POST | `/approvals`(최상위, body `{workRequestId,...}`) | S_02 |

**v1.0에 있었으나 v3.0엔 없는 것**: `/laws/search`·`/parts`·`/equipments`·`/documents`·`/tenants/{id}/ai-config`·완료 보고 전용 엔드포인트(`.../complete`). 오류 포맷은 `{code, message, fieldErrors?}` 단일 규격(코드 23종, CONTRACT §6) — FastAPI 기본 `{"detail":...}`이 아니다. **승인은 체크리스트 없이 즉시, 거절만 사유(10자 이상) 필수**(400 `REJECT_REASON_REQUIRED`).

## 11. 3일 일정·R&R

| 일차 | 산출물 | 담당 |
|---|---|---|
| 1일차 | v3 확정, UC 7개, 와이어프레임 2장, 아키텍처, 샘플(설비 3·부품 4·법령 조문 6·서류 템플릿 2), 레포 | 은태현(일정·샘플), 문승은(UC·와이어프레임), 정구현(아키텍처·API), 장병헌(에이전트 JSON·프롬프트·상태머신), 신서현(GitHub·환경) |
| 2일차 | ERD, Swagger, Mock 서버(step 전이), FE 화면 2개, BE 요청·run·승인 API, DB 연결, 오후 FE-BE 연동 | 은태현(ERD·DB), 정구현(API·Mock), 장병헌(BE 오케스트레이터·승인 게이트), 문승은(FE 타임라인·승인 패널), 신서현(연동) |
| 3일차 | E2E, 발표 자료, 데모 리허설, 15:00 발표 | 은태현(슬라이드), 장병헌(발표·Q&A), 신서현(데모), 전원 |

## 12. 한계·확장

- 한계: 에이전트 **3개**(A1·A2·A3) 전부 Mock, 법령·설비·부품 마스터·호환표는 DB 테이블 자체가 없음(전부 Phase 2 — 샘플 조문조차 DB에 없고 프롬프트에 정적으로 내장), `ai_configs` 테이블 미구현(env var로 대체), 온프레미스 LLM 미구축
- 확장 1: 법령 마스터 테이블 신설 + 법제처 Open API 적재 + 사내 GPU LLM → A2 실제 RAG
- 확장 2: A1을 부품 마스터·호환표 실연동, A4 벤더 에이전트 추가(외부 연동 전제 해소 후), `ai_configs` 테이블 승격으로 멀티테넌트·프롬프트 버전 관리 고도화
- 확장 3: 모니터링 알람 → 자동 작업요청 생성, 예방정비 주기와 결합해 교체 선제 제안
- 확산: 같은 구조로 조선·에너지·화학 등 "법정 승인이 병목인" 설비 산업 → 도메인 에이전트 팩

## 13. 예상 Q&A

- 에이전틱이라면서 사람이 다 승인하면 뭐가 자동화인가? → 정보수집·서류 초안을 에이전트가 하고, 사람은 판단(승인)만. 체크리스트 게이트는 v2.0에서 폐지됐지만 **승인 자체를 SAFETY_MANAGER 역할로만 제한**하고(403 `FORBIDDEN_ROLE`) 요청 생성은 ENGINEER만 하므로, 역할 분리 자체가 Human-in-the-loop 장치다.
- 외부 클라우드 못 쓰는데 LLM은? → `backend/app/core/config.py`의 `validate_egress()`가 외부 provider + `egressAllowed=false` 조합이면 **기동 자체를 거부**(fail-fast). `ai_configs` 테이블은 Phase 2 승격 대상. 3일 범위는 Mock.
- 법령이 바뀌면? → v3.0은 법령 마스터 테이블이 없다. 지금은 A2 프롬프트에 정적으로 내장된 조문(시드)을 근거로 답하고, 확장 시 법령 마스터+RAG로 교체한다.
- 재제출하면 이전 거절 이력은? → `approvals`는 append-only라 재결정도 새 행을 추가한다. 다만 이번 라이브 E2E는 상태 전이(`REJECTED→PENDING`)만 실측했고 "이력이 실제로 조회 가능한지"는 별도 assert가 추가되는 대로 검증 예정(발표에서 과장하지 않는다).

## 14. 확인이 필요한 사항 (CONTRACT §8 "팀 확인 필요" 10건 중 발표에 영향 있는 것)

1. 사진 업로드가 "요청 생성 이후" 구조라 `WRA_E_02`에서 저장 전 업로드하려면 DRAFT 선생성이 전제된다 — 화면 흐름에 노출할지 팀 확인 필요
2. `approvals` append-only 다건 유지를 그대로 시연할지, 단건 갱신처럼 보이게 UI를 단순화할지
3. `ai_configs` 테이블이 Phase 2인 채로 "설정 격리"를 발표에서 어떻게 프레이밍할지(env var 계층 vs DB 테이블)
4. N:M 관계 부재가 루브릭 감점 요인인지("1:N, N:M" 요구), `erd.md`의 Phase 2 예비 설계로 방어 가능한지


---

## 15. 산출물 목록과 루브릭 매핑 (자체 검증 완료 항목 ✅)

| 루브릭 | 세부 기준 | 산출물 (경로) | 검증 |
|---|---|---|---|
| 서비스 기획 & Architecture (30) | Use-Case 정의·UI 와이어프레임 완성도 | `docs/02_usecase/usecase_spec.md`(UC-01~12), `usecase_diagram.svg`, `user_flow.svg` / `docs/03_wireframe/wireframe_spec.md`, `figma_build_guide.md` | ✅ Mermaid 렌더 확인, 9화면 실연동 캡처 11장(`docs/10_project_record/02_evidence/screenshots/`) |
| | AI 확장 지점 정의·프롬프트/JSON 스키마 타당성 | 본 문서 4·7장 / `docs/05_ai_ready/prompts.md`(A1·A2·A3+오케스트레이터 정책+가드레일, `argus-v0.3`) / `docs/05_ai_ready/schemas/agent_run.schema.json`·`agent_result_items.schema.json`·`agent_result_documents.schema.json`·`approval.schema.json` (VENDOR는 `_phase2/`로 이동) | ✅ jsonschema Draft2020-12 검증 15/15 PASS(`docs/05_ai_ready/prompts.md` §7), `load_prompt()` 파서와 헤딩 포맷 실물 대조 |
| | GitHub 관리·R&R 분담 | `README.md`, `docs/01_planning/rnr_and_schedule.md`, `docs/01_planning/github_guide.md`, `.github/PULL_REQUEST_TEMPLATE.md`, `.gitignore` | ✅ |
| | FE-BE-DB 전체 시스템 구조 다이어그램 | `docs/04_architecture/`(아키텍처·상태머신·시퀀스, A1/A2/A3 기준 갱신) | 다른 트랙 담당 — 본 문서 §8 요약과 정합 확인 필요 |
| 시스템 설계 & Scaffolding (30) | ERD 관계(1:N)·정규화 | `docs/06_erd/`(8테이블, N:M 부재는 Phase 2 예비 설계로 방어) | 다른 트랙 담당 |
| | Mock API RESTful 규격(Method/Path/Status) | `docs/07_api/`(API 15개, camelCase, 단일 오류 포맷) | 다른 트랙 담당 |
| | FE/BE 구조·DB 연동 | `frontend/`, `backend/` — **pytest 30 passed, 라이브 E2E 64 통과/0 실패, FE 빌드 223.58 kB**(`docs/10_project_record/02_evidence/test_results/`) | ✅ 실측 로그 원본 보존 |
| | Mock API 데이터 바인딩 화면 시연 | 9화면 실동작: 등록→AI검증(폴링 2500ms)→결과편집(항목단위)→제출→승인/거절(토글+확정, 체크리스트 없음) | ✅ `scripts/e2e_live_v3.sh` curl 재현 |
| Peer (40) | 기획·UX / 시스템 설계 / AI-Ready 확장성 / 구현·Pitch | `docs/08_presentation/`, `docs/09_qa/`, `docs/10_project_record/`(결정 로그·사고 로그·실측 증거) | ✅ |
