# ReplaceFlow 서비스 기획서 (최종본)
## 반도체 설비 부품 교체 "승인 프로세스" 에이전트 — AI-Ready 웹 서비스 설계

| 항목 | 내용 |
|---|---|
| 과정 | SKALA 4기 Full-Stack Engineering · AI 웹 서비스 설계 Mini-project (2026-09-02 ~ 09-04) |
| 팀 | PM·DBA 은태현 / Product&UX·FE 문승은 / DevOps&Infra 신서현 / API Architect·BE 정구현 / BE·발표 장병헌 |
| 문서 버전 | v1.0 최종 (2026-09-02) |
| 프레임 | 우리는 SK AX AI 도메인팀 — 유해가스 취급 설비를 가진 반도체 제조사(하이닉스 협력사·후공정)에 B2B AX 솔루션을 제안한다 |
| 관련 산출물 | `docs/02_usecase`(UC 명세·다이어그램) · `docs/03_wireframe`(와이어프레임) · `docs/04_architecture`(아키텍처·상태머신·시퀀스) · `docs/05_ai_ready`(프롬프트·JSON Schema) · `docs/06_erd`(DBML·DDL·seed) · `docs/07_api`(OpenAPI·API 명세) · `postman/`(Mock) · `frontend/` · `backend/` · `docs/08_presentation`(발표) · `docs/09_qa`(E2E·자체점검·Q&A) |

### 변경 이력
| 버전 | 일자 | 내용 |
|---|---|---|
| v0.1 | 09-02 오전 | E안 "협력사 설비 알람→정비 가이드 에이전트" 초안 |
| v0.2 | 09-02 오후 | 실습교수님 피드백 반영 — 스마트글라스·RAG·QR/YOLO, 법령·규격·교체시기·호환 레이어 전수조사 |
| v0.3 | 09-02 오후 | 팀 회의 반영 — 문제를 "교체 승인 프로세스(규격·법령·승인) 일주일"로 재정의, 에이전트 4개+오케스트레이터, 온프레미스 전제, 스마트글라스는 선택 채널 |
| **v1.0** | 09-02 저녁 | 최종본. 전 산출물(UC·와이어프레임·아키텍처·ERD·API·Mock·FE/BE 스캐폴딩)과 필드·상태값 정합화(`docs/CONTRACT.md`) |

### 목차
1. 서비스 한 줄 정의 · 2. 문제 정의(As-Is) · 3. SK AX 연결 · 4. 에이전틱 AI 배치 · 5. Actor·Use-Case · 6. 핵심 화면 · 7. AI-Ready 설계 · 8. 아키텍처 · 9. ERD · 10. REST API · 11. 일정·R&R · 12. 한계·확장 · 13. 예상 Q&A · 14. 교수님 확인 사항 · 15. 산출물 목록과 루브릭 매핑

---

## 1. 서비스 한 줄 정의

**"설비 이상이 확인되면, 엔지니어가 작업요청 하나만 올리면 AI 에이전트가 부품 규격·호환 확인, 적용 법령 조사, 안전 서류 초안, 벤더 견적 요청까지 병렬로 처리하고, 안전관리자는 근거가 붙은 승인 패널에서 결재만 하는 — 일주일 걸리던 교체 승인을 하루로 줄이는 에이전트."**

가칭: **ReplaceFlow** (설비 부품 교체 승인 에이전트)

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

작업요청 1건이 들어오면 **오케스트레이터가 4개 전문 에이전트를 병렬로 실행**하고, 화면에 각 에이전트의 진행 상태가 실시간으로 바뀐다. 끝나면 안전관리자 승인 패널에 근거가 붙은 결재 요청이 뜬다. 이 "에이전트 실행 타임라인" 화면이 데모의 클라이맥스다.

| 에이전트 | 하는 일 | 입력 | 출력 |
|---|---|---|---|
| **A1. 규격·호환 에이전트** | 기존 부품 규격과 후보 부품 비교, 호환 여부·등급(OEM/호환/리퍼비시) 판정 | 설비 BOM, 부품번호, 벤더 카탈로그(사내 DB) | `spec_match`, `alternatives[]`, 차이점 |
| **A2. 법령 에이전트** | 취급 물질·설비 유형으로 적용 법령 조문 검색, 필요 절차 목록화 | 물질(MSDS), 설비 유형, 작업 종류 → 법령 RAG(법제처 API 사전 인덱스) | `applicable_laws[]`, `required_procedures[]` (작업허가·위험성평가·LOTO·가스 차단 등) |
| **A3. 안전서류 에이전트** | 작업허가서·위험성평가표·LOTO 체크리스트 초안 생성 | A2 결과 + 작업 내용 | `documents[]` (초안 본문·누락 항목) |
| **A4. 벤더 에이전트** | 견적요청(RFQ) 초안, 납기·재고 확인 메시지 작성 | A1 결과, 구매 이력 | `rfq_draft`, `lead_time_est` |
| **오케스트레이터** | 4개 실행·상태 관리, 결과 통합, 승인 패널 생성 | 작업요청 | `agent_run` (steps 상태·통합 요약·승인 필요 항목) |

핵심 설계: 에이전트는 **정보를 모으고 초안을 쓸 뿐** 승인·발주를 실행하지 않는다. 안전관리자가 승인해야 다음 단계(발주·작업)가 열린다 — Human-in-the-loop. 3일 범위에서는 4개 에이전트 모두 Mock(고정 JSON, 단계별 상태 전이)이고 오케스트레이션 구조·상태머신·JSON 계약이 실제 산출물.

## 5. Actor 및 Use-Case

| Actor | 설명 |
|---|---|
| 설비 엔지니어 | 작업요청 생성, 에이전트 결과 확인·보완, 작업 완료 보고 |
| 안전관리자 | 승인 패널에서 법령·서류 검토, 승인/반려/보완요청 |
| 구매 담당(선택) | RFQ 초안 확인 후 발주 |
| 모니터링 시스템(외부) | 이상 알람(Mock 입력) |
| 에이전트 서비스(외부/Mock) | A1~A4 |

| UC | 이름 | Actor | 흐름 |
|---|---|---|---|
| UC-01 | 작업요청 생성 | 엔지니어 | 설비·부품·증상·현장 확인 결과 입력 → `REQUESTED` |
| UC-02 | 에이전트 실행 | 시스템 | 오케스트레이터가 A1~A4 병렬 실행 → `RUNNING` → 각 step `DONE` → `REVIEW` |
| UC-03 | 결과 검토·보완 | 엔지니어 | 에이전트 결과 확인, 누락 정보 입력, 승인 요청 → `PENDING_APPROVAL` |
| UC-04 | 승인 | 안전관리자 | 법령·서류 근거 확인, 체크리스트 완료 후 승인/반려 → `APPROVED`/`REJECTED` |
| UC-05 | 발주·작업 | 엔지니어/구매 | RFQ 발송(초안 그대로 또는 수정), 작업 수행, 완료 보고 → `DONE` |
| UC-06 | 대시보드 | 관리자 | 요청 수, 평균 승인 소요시간(As-Is 7일 대비), 반려 사유 TOP |
| UC-07 | 지식 관리 | 관리자 | 법령 인덱스 갱신, BOM·호환표, 서류 템플릿 |

## 6. 핵심 화면 2개

**화면 1. 작업요청 목록 / 대시보드** — KPI(진행 중, 승인 대기, 평균 승인 소요시간, 이번 달 완료), 요청 테이블(설비 / 부품 / 상태 / 에이전트 진행률 / 승인자), 반려 사유 TOP5

**화면 2. 작업요청 상세 = 에이전트 타임라인 + 승인 패널 (데모 핵심)**
- 상단: 요청 정보(설비, 부품, 증상, 현장 확인 메모)
- 중앙: **에이전트 타임라인** — A1 규격·호환 / A2 법령 / A3 안전서류 / A4 벤더 4개 카드, 각각 `대기 → 실행 중 → 완료` 상태와 결과 요약, 클릭하면 상세(조문 인용, 호환표, 서류 초안)
- 우측: **승인 패널** — 적용 법령 목록(조문 링크), 필수 절차 체크리스트(작업허가·위험성평가·LOTO·가스차단 — 미체크 시 승인 버튼 비활성), 서류 초안 열람, 승인/반려/보완요청 + 코멘트(엔지니어에게 바로 전달 — "메신저 왕복" 대체)
- 데모 시나리오(90초): 요청 생성 → 에이전트 4개가 2~3초 간격으로 완료 → 승인 패널 활성화 → 안전관리자 계정으로 전환 → 체크리스트 4개 체크 → 승인 → 상태 `APPROVED`, 대시보드 평균 승인시간 갱신
- (선택 채널) 같은 화면의 `/glass` 라우트로 현장에서 결과 확인 — 필수 아님

## 7. AI-Ready 설계 포인트

| 원칙 | 설계 |
|---|---|
| Interface First | FE는 `GET /agent-runs/{id}` JSON만 안다. `AgentOrchestrator` + 4개 `AgentService` 인터페이스, 지금은 Mock 구현체, 추후 LLM 구현체로 교체 |
| Structured Data | `agent_runs.steps_json`에 에이전트별 상태·결과, 검색용 컬럼(`overall_status`, `model_name`, `prompt_version`). 법령 결과는 `legal_findings` 테이블로 정규화(조문 단위 추적) |
| Asynchronous Pipeline | `POST /work-requests/{id}/agent-runs` → 202 + `run_id`. `GET /agent-runs/{id}` → steps별 `PENDING/RUNNING/DONE/FAILED`. 3초 폴링. Mock은 호출마다 다음 step을 완료시켜 타임라인이 "살아 움직이게" |
| Security & Config Isolation | **온프레미스 전제**: `ai_configs.provider`에 `LOCAL_LLM`(사내 GPU) / `AX_PLATFORM` / `OPENAI` 선택, 외부 전송 여부 `egress_allowed=false` 기본. 법령 인덱스는 사내에 사전 적재. 프롬프트 버전·에이전트별 모델 분리 |

### 프롬프트 설계 예 (A2 법령 에이전트)
```
[System]
당신은 반도체 제조 사업장의 안전보건 담당자입니다. 주어진 설비·물질·작업 내용에 대해
적용되는 법령 조문과 작업 전 필요한 절차를 찾아 목록화합니다.
- 반드시 제공된 법령 발췌(법제처 인덱스)에서만 인용하고, 조문 번호와 원문을 함께 제시하세요.
- 절차는 '작업 전 / 작업 중 / 작업 후'로 구분하고, 필수 여부와 근거 조문을 붙이세요.
- 근거를 못 찾은 항목은 required=UNKNOWN으로 두고 안전관리자 확인 요청 문구를 넣으세요.
- 출력은 JSON만.
[User]
설비: {equipment}  물질: {substances}  작업: {work_type}  법령 발췌: {law_excerpts}
```

### 에이전트 실행 JSON (`GET /agent-runs/{id}`)
```json
{
  "run_id": "RUN-0042", "work_request_id": "WR-20260902-011", "overall_status": "REVIEW",
  "steps": [
    { "agent": "SPEC", "status": "DONE", "result": { "spec_match": true, "current_part": "VLV-SS316-1/4-NC", "alternatives": [ { "part_no": "VLV-SS316-1/4-NC-EQ", "grade": "EQUIVALENT", "diff": "시트 재질 PCTFE→PTFE", "allowed_for_toxic_gas": false } ] } },
    { "agent": "LEGAL", "status": "DONE", "result": { "applicable_laws": [ { "law": "산업안전보건기준에 관한 규칙", "article": "제92조", "title": "정비등의 작업 시의 운전정지 등", "quote": "…운전을 정지하고 … 잠금장치 및 표지판을…" }, { "law": "화학물질관리법", "article": "제24조", "title": "취급시설의 설치·관리 기준" }, { "law": "고압가스 안전관리법 시행규칙", "article": "별표", "title": "특정고압가스 사용시설 기준" } ], "required_procedures": [ { "name": "작업허가서(가스 배관 작업)", "phase": "BEFORE", "required": true }, { "name": "위험성평가", "phase": "BEFORE", "required": true }, { "name": "LOTO·가스 차단·퍼지 확인", "phase": "BEFORE", "required": true }, { "name": "가스 감지기 정상 확인", "phase": "AFTER", "required": true } ] } },
    { "agent": "SAFETY_DOC", "status": "DONE", "result": { "documents": [ { "type": "WORK_PERMIT", "draft_uri": "/docs/WR-011-permit.md", "missing": ["작업자 2명 이름"] }, { "type": "RISK_ASSESSMENT", "draft_uri": "/docs/WR-011-ra.md", "missing": [] } ] } },
    { "agent": "VENDOR", "status": "DONE", "result": { "rfq_draft": "…VLV-SS316-1/4-NC 2EA 견적 및 납기 요청…", "lead_time_est_days": 3, "last_purchase": "2026-02-14" } }
  ],
  "summary": "OEM 동일 규격 밸브 교체. 유독가스 라인이라 호환품 불가. 작업허가·위험성평가·LOTO 필수. 서류 초안 2건 생성, 작업자 명단만 보완 필요.",
  "approval_required_by": "SAFETY_MANAGER",
  "model_name": "mock-v1", "prompt_version": "replaceflow-v0.1",
  "created_at": "2026-09-02T15:10:02+09:00", "completed_at": "2026-09-02T15:11:30+09:00"
}
```

## 8. 시스템 아키텍처

```
[모니터링(외부, Mock)] ─알람─▶ ┌────────── BE (Spring Boot / FastAPI) ──────────┐
[웹 (Vue/Vite)] ◀─REST JSON─▶ │ WorkRequest API                                 │──▶ [DB PostgreSQL]
  화면1 목록/대시보드          │ AgentOrchestrator ─┬─ SpecAgent   (Mock/LLM)   │
  화면2 타임라인+승인 패널      │                    ├─ LegalAgent  (Mock/LLM+RAG)│──▶ [법령 인덱스(사내, 법제처 API 사전 적재)]
  (/glass 선택 채널)           │                    ├─ SafetyDocAgent           │──▶ [서류 템플릿]
                               │                    └─ VendorAgent              │──▶ [BOM·구매이력]
                               │ ApprovalService (상태머신, 체크리스트 게이트)     │
                               │ ai_configs: provider=LOCAL_LLM, egress=false    │
                               └────────────────────────────────────────────────┘
확장: [Queue] [사내 GPU LLM] [Vector DB] [ERP/구매 연동] [사내 메신저 알림]
```

## 9. ERD

| 테이블 | 주요 컬럼 | 관계 |
|---|---|---|
| `tenants` | id, name, plan | 1:N 이하 전부 |
| `users` | id, tenant_id, name, role(ENGINEER/SAFETY_MANAGER/BUYER/ADMIN) | |
| `equipments` | id, tenant_id, name, type(GAS_CABINET/VALVE/PIPING/SCRUBBER…), line, substances(JSON) | 1:N work_requests, equipment_parts |
| `parts` | id, tenant_id, part_no, name, spec(JSON), grade, toxic_gas_allowed(bool), stock | 1:N part_compatibility |
| `equipment_parts` | equipment_id, part_id, installed_at, last_replaced_at | |
| `part_compatibility` | part_id, alt_part_id, diff, allowed_for_toxic_gas | |
| `work_requests` | id, equipment_id, part_id, symptom, site_check_note, requested_by, status(REQUESTED/RUNNING/REVIEW/PENDING_APPROVAL/APPROVED/REJECTED/DONE), created_at | 1:N agent_runs, approvals |
| `agent_runs` | id, work_request_id, overall_status, steps_json, summary, model_name, prompt_version, created_at, completed_at | 1:N legal_findings, documents |
| `legal_findings` | id, agent_run_id, law, article, title, quote, procedure_name, phase, required | |
| `documents` | id, agent_run_id, type(WORK_PERMIT/RISK_ASSESSMENT/LOTO_CHECKLIST/RFQ), body, missing_json, version | |
| `approvals` | id, work_request_id, approver_id, decision(APPROVE/REJECT/REQUEST_INFO), checklist_json, comment, decided_at | |
| `law_index` | id, law, article, text, effective_date, source_uri (법제처 사전 적재) | |
| `ai_configs` | tenant_id, agent_type, provider(LOCAL_LLM/AX_PLATFORM/OPENAI), model_name, prompt_version, egress_allowed | |
| `audit_logs` | user_id, entity, entity_id, action, before_json, after_json, created_at | |

정규화 포인트: 요청(사실) / 에이전트 산출(agent_runs·legal_findings·documents) / 사람의 결정(approvals) 3층 분리. 법령은 `law_index`(원문)와 `legal_findings`(이 건에 적용된 조문) 분리로 법 개정 시 과거 판단 보존.

## 10. REST API

| Method | Path | 설명 | 응답 |
|---|---|---|---|
| GET/POST | `/api/v1/work-requests` | 목록 / 생성 | 200 / 201 |
| GET | `/api/v1/work-requests/{id}` | 상세(+최신 run, approvals) | 200/404 |
| POST | `/api/v1/work-requests/{id}/agent-runs` | **에이전트 실행(비동기)** | **202** `{run_id, overall_status:"RUNNING"}` |
| GET | `/api/v1/agent-runs/{runId}` | steps 상태·결과(폴링) | 200 |
| PATCH | `/api/v1/work-requests/{id}/submit-approval` | 승인 요청(누락 항목 있으면 422) | 200/422 |
| POST | `/api/v1/work-requests/{id}/approvals` | 승인/반려/보완요청(필수 체크리스트 미완료 시 409) | 201/409 |
| GET | `/api/v1/documents/{docId}` | 서류 초안 | 200 |
| GET | `/api/v1/parts/{partId}/compatibility` | 호환표 | 200 |
| GET | `/api/v1/laws/search?q=&equipmentType=&substance=` | 법령 인덱스 검색 | 200 |
| GET | `/api/v1/dashboard/summary` | KPI·평균 승인 소요시간 | 200 |
| GET/PUT | `/api/v1/tenants/{id}/ai-config` | 에이전트별 모델·egress 설정 | 200 |

Mock: `POST …/agent-runs` 후 `GET` 호출마다 step 하나씩 `DONE`으로 전이(4회 호출 = 약 12초) → `REVIEW`. 오류: 404, 409(체크리스트 미완료 승인), 422(누락 정보).

## 11. 3일 일정·R&R

| 일차 | 산출물 | 담당 |
|---|---|---|
| 1일차 | v3 확정, UC 7개, 와이어프레임 2장, 아키텍처, 샘플(설비 3·부품 4·법령 조문 6·서류 템플릿 2), 레포 | 은태현(일정·샘플), 문승은(UC·와이어프레임), 정구현(아키텍처·API), 장병헌(에이전트 JSON·프롬프트·상태머신), 신서현(GitHub·환경) |
| 2일차 | ERD, Swagger, Mock 서버(step 전이), FE 화면 2개, BE 요청·run·승인 API, DB 연결, 오후 FE-BE 연동 | 은태현(ERD·DB), 정구현(API·Mock), 장병헌(BE 오케스트레이터·승인 게이트), 문승은(FE 타임라인·승인 패널), 신서현(연동) |
| 3일차 | E2E, 발표 자료, 데모 리허설, 15:00 발표 | 은태현(슬라이드), 장병헌(발표·Q&A), 신서현(데모), 전원 |

## 12. 한계·확장

- 한계: 에이전트 4개 전부 Mock, 법령 인덱스는 샘플 6개 조문, 벤더·ERP 미연동, 온프레미스 LLM 미구축
- 확장 1: 법제처 Open API 전량 적재 + 사내 GPU LLM(또는 A.X 플랫폼) → A2 실제 RAG. 사내 메신저 알림 연동
- 확장 2: A1을 ERP·BOM 실연동, A4를 벤더 포털 연동, 승인 이력으로 프롬프트 튜닝
- 확장 3: 알람 → 자동 작업요청 생성(모니터링 연동), 예방정비 주기와 결합해 교체 선제 제안
- 확산: 같은 구조로 조선·에너지(한전기술)·화학 등 "법정 승인이 병목인" 모든 설비 산업 → AXgenticWire 위의 도메인 에이전트 팩

## 13. 예상 Q&A

- 에이전틱이라면서 사람이 다 승인하면 뭐가 자동화인가? → 일주일 중 정보수집·서류·문의(5일)를 에이전트가 하고, 사람은 판단(승인)만. 산업안전 규제상 승인 주체는 사람이어야 하며, 그 자체가 설계 요건.
- 외부 클라우드 못 쓰는데 LLM은? → `ai_configs.provider=LOCAL_LLM`, `egress_allowed=false`. GaiA(하이닉스 폐쇄망 LLM)가 선례. 3일 범위는 Mock.
- 법령이 바뀌면? → `law_index` 재적재, `legal_findings`는 건별 스냅샷이라 과거 판단 보존.
- 법령 답변이 틀리면? → 조문 인용 없는 답은 표시하지 않음, `required=UNKNOWN`으로 안전관리자에게 넘김. 가이드라인상 AI는 보조수단.
- 스마트글라스는? → 선택 채널. 같은 API의 `/glass` 라우트. 필수 아님.

## 14. 전임교수님께 여쭐 것

1. 에이전트 4개 + 오케스트레이터 구조를 "AI 확장 지점"으로 정의한 것이 적절한지, 1개로 줄이는 게 채점에 유리한지
2. 승인 상태머신(REQUESTED→…→APPROVED)과 체크리스트 게이트(409)를 핵심 화면 2개 안에서 시연하는 범위가 적정한지
3. 법령 인덱스(`law_index`)를 DB 테이블로 두고 RAG는 확장으로 미룬 설계가 Structured Data 요건을 충족하는지
4. 온프레미스 제약을 `ai_configs.provider/egress_allowed`로 표현한 것이 Security & Config Isolation 평가 기준에 맞는지


---

## 15. 산출물 목록과 루브릭 매핑 (자체 검증 완료 항목 ✅)

| 루브릭 | 세부 기준 | 산출물 (경로) | 검증 |
|---|---|---|---|
| 서비스 기획 & Architecture (30) | Use-Case 정의·UI 와이어프레임 완성도 | `docs/02_usecase/usecase_spec.md`, `usecase_diagram.svg`, `user_flow.svg` / `docs/03_wireframe/wireframe.html`(데모 애니메이션 포함), `wireframe_spec.md`(Figma 구조) | ✅ Mermaid 렌더, HTML 동작 |
| | AI 확장 지점 정의·프롬프트/JSON 스키마 타당성 | 본 문서 4·7장 / `docs/05_ai_ready/prompts.md`(4 에이전트+오케스트레이터 정책+가드레일+Playground 검증 절차) / `docs/05_ai_ready/schemas/*.schema.json` | ✅ 샘플 JSON이 스키마 통과, 역예제 거부 확인 |
| | GitHub 관리·R&R 분담 | `README.md`, `docs/01_planning/rnr_and_schedule.md`, `docs/01_planning/github_guide.md`, `.github/PULL_REQUEST_TEMPLATE.md`, `.gitignore` | ✅ |
| | FE-BE-DB 전체 시스템 구조 다이어그램 | `docs/04_architecture/architecture.svg`, `architecture.md`(4원칙 매핑), `state_machine.svg`, `sequence_agent_run.svg` | ✅ |
| 시스템 설계 & Scaffolding (30) | ERD 관계(1:N, N:M)·정규화 | `docs/06_erd/replaceflow.dbml`(dbdiagram), `schema_postgres.sql`, `seed_data.sql`, `erd.md` | ✅ PostgreSQL 16 실제 실행·재실행, CHECK 게이트 동작 |
| | Mock API RESTful 규격(Method/Path/Status) | `docs/07_api/openapi.yaml`(Swagger), `api_spec.md`, `postman/ReplaceFlow.postman_collection.json`(52 예시 응답, Mock Server용) | ✅ Redocly lint 0 error |
| | FE/BE 구조·DB 연동 | `frontend/`(Vue3+Vite, Mock 모드 토글), `backend/`(FastAPI, SQLAlchemy, SQLite↔PostgreSQL) | ✅ FE 빌드 성공, BE pytest 8/8 |
| | Mock API 데이터 바인딩 화면 시연 | 화면1·2 실동작: POST 202 → 폴링 4회 step 전이 → REVIEW → 승인 요청 → 체크리스트 409 → 승인 201 → APPROVED | ✅ 실제 BE에 curl로 E2E 재현 |
| Peer (40) | 기획·UX / 시스템 설계 / AI-Ready 확장성 / 구현·Pitch | `docs/08_presentation/`(구성안·대본·데모 시나리오), `docs/09_qa/qa_bank.md`, `e2e_test_checklist.md`, `self_review_rubric.md`, `retrospective_template.md` | ✅ |
