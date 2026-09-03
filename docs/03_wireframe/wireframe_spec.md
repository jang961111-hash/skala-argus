# ReplaceFlow 와이어프레임 스펙 (Figma 재작업용)

- 산출물: `wireframe.html` (브라우저에서 바로 열어 데모 가능, 외부 리소스 없음)
- 기준 문서: `docs/CONTRACT.md` (상태값·API·샘플 데이터 고정), 기획서 4장·6장
- 스타일: Lo-Fi 그레이박스(Balsamiq 풍). 색은 상태 칩에만 최소 사용.
- API base: `/api/v1`

---

## 1. 화면1. 작업요청 목록 / 대시보드  (Route `/`)

**Actor** 엔지니어·안전관리자·관리자 · **UC** UC-01, UC-06

| # | 요소 | 내용 | 호출 API |
|---|---|---|---|
| 상단바 | 로고 / 메뉴(작업요청·지식관리·설정) / 검색 / 사용자 칩(이름·role) | 정적 | — |
| ① | KPI 카드 ×4 | 진행 중 `in_progress`(5), 승인 대기 `pending_approval`(2), 평균 승인 소요시간 `avg_approval_hours`(26.5h) **vs As-Is** `as_is_baseline_hours`(168h) 비교 바(▼84%), 이번 달 완료 `completed_this_month`(12) | `GET /dashboard/summary` → 200 DashboardSummary |
| ② | 작업요청 테이블 | 열: 요청 ID / 설비 / 부품 / 증상 / 상태 칩 / 에이전트 진행률 / 승인자 / 요청일. 상단 상태 필터 칩, 하단 페이저(total·page·size). 행 클릭 → 화면2 | `GET /work-requests?status=&page=&size=` → 200 `{items:[WorkRequestSummary], total}` |
| ③ | 에이전트 진행률 셀 | 4칸 미니 스텝(SPEC·LEGAL·SAFETY_DOC·VENDOR) + 바 + `n/4`. 회색 PENDING / 주황 RUNNING / 진회색 DONE. RUNNING 행은 5초 폴링 | `GET /agent-runs/{runId}` |
| ④ | 새 작업요청 버튼 | 모달: 설비 select, 부품 select, 증상, 현장 확인 메모 → 저장 후 화면2 이동(REQUESTED) | `GET /equipments`, `GET /parts`, `POST /work-requests` → 201 |
| ⑤ | 반려 사유 TOP | 가로 막대: 서류 누락 3 / 호환품 부적합 1 | ①의 `reject_reasons_top[]` 재사용 |
| ⑥ | 최근 알림 (선택) | 승인 코멘트·에이전트 완료 알림 목록. 3일 범위 밖, 정적 | — |

**샘플 행 5건 (CONTRACT 샘플)**

| 요청 ID | 설비 | 부품 | 상태 | 진행률 | 승인자 |
|---|---|---|---|---|---|
| WR-20260902-011 | EQ-GC-02 가스캐비닛#2 | VLV-SS316-1/4-NC | REQUESTED | 0/4 | — |
| WR-20260902-010 | EQ-VLV-07 공정가스 밸브#7 | VLV-SS316-1/4-NC | RUNNING | 2/4 | — |
| WR-20260901-009 | EQ-SCR-01 스크러버#1 | 인라인 필터 | REVIEW | 4/4 | — |
| WR-20260901-008 | EQ-GC-02 가스캐비닛#2 | 압력조정기 REG-2S | PENDING_APPROVAL | 4/4 | 이정호 |
| WR-20260829-007 | EQ-VLV-07 공정가스 밸브#7 | VLV-SS316-1/4-NC | APPROVED | 4/4 | 이정호 |

---

## 2. 화면2. 작업요청 상세 — 에이전트 타임라인 + 승인 패널  (Route `/work-requests/:id`)

**Actor** 엔지니어 → 안전관리자 · **UC** UC-02, UC-03, UC-04 · **데모 클라이맥스**

레이아웃: 상단 헤더(전폭) / 중앙 타임라인(가변) / 우측 승인 패널(300px 고정)

| # | 요소 | 내용 | 호출 API |
|---|---|---|---|
| ① | 요청 정보 헤더 | ID, 상태 칩, 요청자·일시, `approval_required_by`. 4셀: 설비(EQ-GC-02·GAS_CABINET·SiH4) / 부품(P-VLV-001·OEM·재고2) / 증상 / 현장 확인 메모 | `GET /work-requests/{id}` → 200 WorkRequestDetail(latest_run, approvals 포함) / 404 |
| ② | 데모 재생(에이전트 실행) 버튼 | 클릭 → 상태 REQUESTED→RUNNING, 카드가 2초 간격으로 PENDING→RUNNING→DONE. 초기화 버튼 병행 | `POST /work-requests/{id}/agent-runs` → 202 `{run_id, overall_status:"RUNNING"}` / 409(이미 APPROVED·DONE) |
| ③ | 오케스트레이터 바 | "A1~A4 병렬 실행·상태 관리·결과 통합" + 진행 카운트(n/4) | 2초 폴링 `GET /agent-runs/{runId}` (Mock: 호출마다 step 1개 DONE, 순서 SPEC→LEGAL→SAFETY_DOC→VENDOR) |
| ④ | 에이전트 카드 ×4 (2×2) | 각 카드: 코드(A1~A4)·이름·상태 칩(대기/실행 중/완료)·입력 설명·결과 요약·"상세 ›" 링크. 결과는 `steps[].result` 요약 (A1 spec_match/alternatives, A2 법령 3·절차 4, A3 서류 2건+누락, A4 RFQ·납기) | 상세: `GET /parts/{partId}/compatibility`, `GET /laws/search?q=&equipmentType=&substance=`, `GET /documents/{docId}` |
| ⑤ | 통합 요약 + 엔지니어 액션 | `summary` 문장 표시. 승인 요청 버튼(run 완료 전 비활성) → PENDING_APPROVAL | `PATCH /work-requests/{id}/submit-approval` → 200 / 422(누락) / 409(run 미완료) |
| ⑥ | 승인 패널 (잠금/읽기전용 오버레이) | REVIEW 전 잠금 오버레이. ENGINEER 역할이면 반투명 읽기 전용 마스크. 적용 법령 3건: 산안규칙 제92조(인용문 포함) / 화관법 제24조 / 고압가스법 시행규칙 별표 — 조문 클릭 시 원문 | A2 `applicable_laws[]` |
| ⑦ | 필수 절차 체크리스트 ×4 | `WORK_PERMIT`(BEFORE) / `RISK_ASSESSMENT`(BEFORE) / `LOTO_GAS_ISOLATION`(BEFORE) / `GAS_DETECTOR_CHECK`(AFTER). 카운터 "n/4 체크". 4개 모두 체크 시에만 승인 버튼 활성. 서류 초안 링크 3건(DOC-0101 작업허가서 ⚠누락: 작업자 2명 이름, DOC-0102 위험성평가표, DOC-0103 RFQ) | `GET /documents/{docId}` |
| ⑧ | 결정 + 코멘트 | textarea(엔지니어에게 바로 전달) + 승인(primary, 조건부 활성) / 반려 / 보완요청. 서버는 체크 미완료 APPROVE를 409 | `POST /work-requests/{id}/approvals` → 201 Approval `{decision, checklist{4}, comment}` |
| ⑨ | 역할 전환 토글 | 데모용. ENGINEER: 실행·승인 요청 활성, 패널 읽기 전용 / SAFETY_MANAGER: 패널 활성, 실행 버튼 비활성 | — (실서비스는 로그인 role) |

**인터랙션 (HTML에 구현됨)**
1. `데모 재생` → 4카드 순차 2초 애니메이션(실행 중 점멸 → 완료 녹색 테두리), 토스트로 호출 API 표시
2. 4개 DONE → `overall_status=REVIEW`, 요약 표시, 승인 패널 잠금 해제, 승인 요청 버튼 활성
3. `승인 요청` → 상태 PENDING_APPROVAL
4. 역할 토글 `안전관리자` → 패널 조작 가능
5. 체크 4/4 → 승인 버튼 활성 → 승인 → 상태 APPROVED (반려 REJECTED / 보완요청 REVIEW)
6. `초기화` → 처음 상태

---

## 3. 화면 흐름도 (User Flow)

3레인(엔지니어 / 시스템 / 안전관리자) 박스-화살표 다이어그램.
화면1 → 새 작업요청 모달 → 화면2(엔지니어) → [시스템: 오케스트레이터 → A1~A4 → 결과 통합] → 결과 검토·보완 → [안전관리자: 승인 패널 → 승인/반려/보완 → APPROVED] → 발주·작업·완료(DONE).
반려/보완은 적색 점선으로 화면2(엔지니어)로 회귀. 하단에 상태 스트립
`REQUESTED → RUNNING → REVIEW → PENDING_APPROVAL → APPROVED | REJECTED → DONE`.

## 4. 글라스 뷰 (선택, Route `/glass/:id`)

360px 다크 모바일 프레임, 6단계 큰 글씨 카드(부품 확인 / 작업허가서 / LOTO·가스차단·퍼지 / 교체 작업 / 가스 감지기 확인 / 완료 보고). 완료 단계 녹색. 데이터는 화면2와 동일(`GET /work-requests/{id}` → `latest_run.steps[].result`). 별도 API 없음.

---

## 5. Figma 페이지 구조 제안

```
📁 ReplaceFlow_Wireframe
 ├─ Page: 00_Cover            프로젝트명·버전·상태값 범례
 ├─ Page: 01_Components       (로컬 컴포넌트)
 │    ├─ Chip/Status          variants: REQUESTED · RUNNING · REVIEW · PENDING_APPROVAL · APPROVED · REJECTED · DONE
 │    ├─ Chip/StepStatus      variants: 대기(PENDING) · 실행 중(RUNNING) · 완료(DONE) · 실패(FAILED)
 │    ├─ Card/KPI             props: label, value, unit, compareBar(bool)
 │    ├─ Card/Agent           props: code(A1~A4), name, agentKey, status, resultSlot
 │    ├─ Row/WorkRequest      테이블 행 (진행률 미니 스텝 포함)
 │    ├─ Progress/AgentSteps  4칸 스텝 + 바
 │    ├─ Panel/Approval       하위: Law/Item, Checklist/Item, Doc/Link, Decision/Buttons
 │    ├─ Toggle/Role          ENGINEER · SAFETY_MANAGER
 │    ├─ Button               variants: primary · default · danger · disabled · small
 │    ├─ Annotation/Badge     ① 숫자 배지 (주황 #E8552B)
 │    └─ Note/Callout         노란 주석 박스
 ├─ Page: 02_Screen1_Dashboard
 │    ├─ Frame: S1_Dashboard_Default        (1440×900, Desktop)
 │    ├─ Frame: S1_Dashboard_Filtered       (status=PENDING_APPROVAL)
 │    ├─ Frame: S1_NewRequest_Modal
 │    └─ Frame: S1_Annotations              (우측 주석 컬럼)
 ├─ Page: 03_Screen2_Detail
 │    ├─ Frame: S2_Detail_01_Requested      (패널 잠금, 카드 4 PENDING)
 │    ├─ Frame: S2_Detail_02_Running        (A1 DONE, A2 RUNNING, A3·A4 PENDING)
 │    ├─ Frame: S2_Detail_03_Review         (4 DONE, 요약, 패널 활성·엔지니어 읽기전용)
 │    ├─ Frame: S2_Detail_04_SafetyManager  (역할 전환, 체크 2/4, 승인 비활성)
 │    ├─ Frame: S2_Detail_05_Approved       (체크 4/4 → APPROVED, 토스트)
 │    ├─ Frame: S2_AgentCard_Detail_Modal   (조문 인용·호환표·서류 초안 탭)
 │    └─ Frame: S2_Annotations
 ├─ Page: 04_UserFlow
 │    └─ Frame: Flow_3Lanes                 (FigJam 또는 Figma 섹션, 상태 스트립 포함)
 ├─ Page: 05_Glass_Optional
 │    └─ Frame: Glass_6Steps                (360×640, Mobile)
 └─ Page: 99_Prototype
      S2_01 → S2_02 → S2_03 → S2_04 → S2_05 를 After delay 2000ms로 연결 (데모 재생 재현)
```

**네이밍 규칙** `S{화면번호}_{화면명}_{상태}`, 컴포넌트는 `Category/Name`, variant 값은 CONTRACT의 상태 문자열 그대로.
**주석 규칙** 각 프레임 우측 320px 주석 컬럼, 배지 번호 = 이 문서의 # 번호, 각 항목에 API 경로 표기.
**색 토큰(최소)** ink #333 / line #8A8A8A / box #ECECEC / note #FFF6C2 / RUNNING #F2A63A / DONE #4CAF50 / annotation #E8552B.
