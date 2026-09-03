# ReplaceFlow Frontend (Vue 3 + Vite)

반도체 설비 부품 교체 승인 프로세스 에이전트 **ReplaceFlow** 의 웹 프론트엔드.
`docs/CONTRACT.md` 의 REST/JSON 계약만 바라보며 동작한다.

## 1. 설치 / 실행

```bash
cd frontend
npm install

# (A) 백엔드(FastAPI, :8000)와 함께 실행 — /api 요청은 vite proxy 가 http://localhost:8000 으로 전달
npm run dev            # http://localhost:5173

# (B) 백엔드 없이 Mock 모드로 실행 — HTTP 호출 없이 src/mock/data.js 인메모리 데이터 사용
npm run dev:mock       # = VITE_USE_MOCK=true vite

# 프로덕션 빌드 / 미리보기
npm run build
npm run preview
```

## 2. Mock 모드

`VITE_USE_MOCK=true` 이면 `src/api/client.js` 가 axios 대신 **동일한 계약(경로·상태코드·스키마)** 을 구현한 인메모리 Mock 을 export 한다. 화면 코드는 어느 쪽인지 알 필요가 없다.

Mock 은 CONTRACT.md 의 "Mock 동작" 을 그대로 시뮬레이션한다.

| 동작 | Mock 응답 |
|---|---|
| `POST /work-requests/{id}/agent-runs` | 202 `{run_id, overall_status:"RUNNING"}`, steps 4개 모두 `PENDING`, work_request.status=`RUNNING` |
| `GET /agent-runs/{runId}` (호출마다) | 다음 step 하나가 `DONE` (SPEC→LEGAL→SAFETY_DOC→VENDOR), 그 다음 step 은 `RUNNING` |
| 4개 모두 DONE | `overall_status=REVIEW`, `summary` 채움, work_request.status=`REVIEW` |
| `PATCH …/submit-approval` | run 이 REVIEW 가 아니면 409, 증상/메모 없으면 422, 성공 시 `PENDING_APPROVAL` |
| `POST …/approvals` APPROVE | checklist 4항목 모두 true 아니면 409, 성공 시 `APPROVED` + 대시보드 KPI(평균 승인시간·완료 건수) 갱신 |
| `POST …/approvals` REJECT / REQUEST_INFO | `REJECTED` / `REVIEW`(엔지니어가 보완 후 재요청) |
| `POST …/agent-runs` (APPROVED/DONE 상태) | 409 |

타임라인 컴포넌트는 3초 폴링을 하므로 Mock 에서는 약 12초에 4개 카드가 순차 완료된다 (기획서 90초 데모 시나리오).

상단 바에 `MOCK` 배지가 표시되면 Mock 모드다.

## 3. 환경 변수

`.env.example` 참고. Vite 규칙에 따라 `VITE_` 접두사만 클라이언트에 노출된다.

| 변수 | 기본값 | 설명 |
|---|---|---|
| `VITE_USE_MOCK` | `false` | `true` 면 HTTP 대신 인메모리 Mock 사용 |
| `VITE_API_BASE` | `/api/v1` | axios baseURL. 개발 시 vite proxy 가 `/api` → `http://localhost:8000` |

## 4. 폴더 구조

```
frontend/
├─ index.html
├─ vite.config.js            # port 5173, proxy /api → :8000
├─ package.json
├─ .env.example
└─ src/
   ├─ main.js
   ├─ App.vue                # 상단 바(브랜드·MOCK 배지·역할 전환 엔지니어/안전관리자)
   ├─ assets/main.css        # UI 라이브러리 없는 최소 CSS
   ├─ api/client.js          # axios 인스턴스(baseURL /api/v1) + Mock 구현. FE 가 BE 를 아는 유일한 지점
   ├─ mock/data.js           # CONTRACT.md 샘플 데이터 (T-001, U-001~4, EQ/P/WR 5건, AgentRun 스텝 결과)
   ├─ store/session.js       # reactive 역할 store (ENGINEER=U-001 김민준 / SAFETY_MANAGER=U-002 이정호)
   ├─ router/index.js        # /  →  화면1,  /work-requests/:id  →  화면2
   ├─ views/
   │  ├─ WorkRequestListView.vue    # 화면1: KPI 카드(/dashboard/summary) + 요청 테이블(/work-requests) + 새 작업요청 모달
   │  └─ WorkRequestDetailView.vue  # 화면2: 요청 정보 헤더 + AgentTimeline + ApprovalPanel
   └─ components/
      ├─ StatusChip.vue       # CONTRACT 상태 문자열 → 라벨/색상
      ├─ AgentTimeline.vue    # A1~A4 카드, "에이전트 실행" → POST agent-runs → 3초 폴링 GET /agent-runs/{id}
      └─ ApprovalPanel.vue    # 적용 법령·서류 초안·체크리스트 4개·승인/반려/보완요청 (역할·상태 게이트)
```

## 5. 데모 흐름 (90초)

1. 화면1 `+ 새 작업요청` → 설비/부품/증상 입력 → 생성 시 화면2로 이동 (`REQUESTED`)
2. `에이전트 실행` → A1~A4 카드가 3초 간격으로 `대기 → 실행 중 → 완료`, 종합 요약 표시 (`REVIEW`)
3. 엔지니어 `승인 요청` → `PENDING_APPROVAL`
4. 상단 바에서 **안전관리자** 로 전환 → 체크리스트 4개 체크 → `승인` 버튼 활성화 → 승인 (`APPROVED`)
5. 화면1로 돌아가면 KPI(평균 승인 소요시간·이번 달 완료) 갱신

## 6. AI-Ready "Interface First" 가 FE 에 반영된 방식

- **FE 는 JSON 계약만 안다.** 화면은 `GET /agent-runs/{id}` 가 돌려주는 `steps[].agent / status / result` 구조만 렌더링한다. 뒤에서 4개 에이전트가 Mock 인지, 사내 GPU LLM 인지, AX Platform 인지는 FE 코드에 전혀 나타나지 않는다. `model_name` / `prompt_version` 은 표시만 한다.
- **비동기 파이프라인 전제.** `POST …/agent-runs` 는 202 + `run_id` 만 받고, 이후 3초 폴링으로 step 상태를 그린다. 나중에 실제 LLM 이 수십 초 걸려도 화면 코드는 바뀌지 않는다.
- **Mock 과 HTTP 가 같은 인터페이스.** `src/api/client.js` 는 `USE_MOCK` 에 따라 같은 메서드 집합(`getAgentRun`, `createApproval` …)을 가진 두 구현체 중 하나를 export 한다. 컴포넌트는 `import api from '../api/client'` 만 한다. BE 의 `AgentOrchestrator` + `AgentService` 인터페이스(Mock → LLM 구현체 교체)와 대칭 구조.
- **상태·필드명은 CONTRACT.md 문자열을 그대로 사용.** `StatusChip` 매핑, 체크리스트 키(`WORK_PERMIT`, `RISK_ASSESSMENT`, `LOTO_GAS_ISOLATION`, `GAS_DETECTOR_CHECK`), 에이전트 키(`SPEC`, `LEGAL`, `SAFETY_DOC`, `VENDOR`) 모두 계약서와 동일하므로 OpenAPI/Postman/BE 와 어긋나면 즉시 드러난다.
- **승인 게이트는 FE·BE 이중.** FE 는 체크리스트 미완료 시 승인 버튼을 비활성화하고, BE(Mock 포함)는 같은 조건에서 409 를 반환한다. 계약서의 규칙 하나가 양쪽에서 동일하게 구현된다.
