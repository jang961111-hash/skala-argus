# Argus 와이어프레임 스펙 v3.0 — 화면별 요소·API 매핑

- 기준 문서: `docs/CONTRACT.md` v3.0(팀 「API 명세서 v1.0」+「데이터 모델 정의서 v3.0」+「WRA 화면정의서 v2.0」 원문 이관)
- **디자인 토큰·컴포넌트 목록·Figma 페이지 구조·Acceptance Criteria 매핑·우선순위는 `docs/03_wireframe/figma_build_guide.md`(UX 담당, 읽기 전용)를 단일 진실 원천으로 삼는다.** 그 문서는 v2.0 화면정의서를 기준으로 작성됐지만 **9화면 Screen ID·Route·AC 번호는 CONTRACT §7 화면↔API 매트릭스와 그대로 일치**하므로 재작업 없이 참조한다. 이 문서는 그것과 중복하지 않고 **화면별 요소·호출 API 번호 표만** 남긴다.
- API base: `/api/v1`. **필드명은 camelCase**(`workRequestId`, `engineerNote` 등). 인증: 전 화면(로그인·회원가입 제외) `Authorization: Bearer {accessToken}` 필요.
- **API는 CONTRACT §4의 번호(1~15)로 인용한다** — REST 경로를 화면마다 새로 적지 않는다. 번호 전문은 `docs/CONTRACT.md` §4 참조.

---

## 0. 화면 목록 (CONTRACT §7)

| Screen ID | 경로 | 역할 | 호출 API(#) | 요소·API 표 |
|---|---|---|---|---|
| `WRA_C_00` | `/login` | 공통 | 2 | §1 |
| `WRA_C_01` | `/signup` | 공통 | 1 | §2 |
| `WRA_E_01` | `/home` | ENGINEER | 4(engineer)·6(mine)·7 | §3 |
| `WRA_E_02` | `/requests/new` | ENGINEER | 5·9·11 | §4 |
| `WRA_E_03` | `/requests/{id}/run` | ENGINEER | 12(폴링)·7 | §5 |
| `WRA_E_04` | `/requests/{id}/result` | ENGINEER | 7·13·8·14 | §6 |
| `WRA_E_05` | `/my/requests` | ENGINEER | 6·7·14 | §7 |
| `WRA_S_01` | `/manage/requests` | SAFETY_MANAGER | 4(safety)·6(status=PENDING) | §8 |
| `WRA_S_02` | `/manage/requests/{id}` | SAFETY_MANAGER | 7·10·15 | §9 |

화면 흐름도는 `docs/02_usecase/user_flow.mmd`/`.svg`, UC 대응표는 `docs/02_usecase/usecase_spec.md` §2 참조.

---

## 1. `WRA_C_00` 로그인 (`/login`)

**UC** UC-02

| # | 요소 | 내용 | API |
|---|---|---|---|
| ① | 로그인 카드 | 이메일·비밀번호 입력 | — |
| ② | 오류 배너 | `INVALID_CREDENTIALS` 시 표시 | #2 → 401 |
| ③ | 로그인 버튼 | 성공 시 응답의 **`redirectPath`로 그대로 이동**(FE가 role로 직접 분기하지 않는다) | #2 `POST /auth/login` → 200 `{accessToken, role, redirectPath}` |
| ④ | 회원가입 링크 | → `WRA_C_01` | — |

---

## 2. `WRA_C_01` 회원가입 (`/signup`)

**UC** UC-01

| # | 요소 | 내용 | API |
|---|---|---|---|
| ① | 가입 폼 | `name`(2~20자)·`email`·`password`(8자↑, 영문+숫자+특수문자)·`passwordConfirm` | — |
| ② | RoleSelect | 라디오(`ENGINEER`/`SAFETY_MANAGER`) — 필수 | — |
| ③ | 오류 표시 | 필수 누락/역할 미선택 → `VALIDATION_FAILED`, 비밀번호 불일치 → `PASSWORD_MISMATCH`, 중복 이메일 → `EMAIL_ALREADY_EXISTS` | #1 → 400/409 |
| ④ | 가입 버튼 | 성공 시 `WRA_C_00` 이동 | #1 `POST /auth/signup` → 201 |

---

## 3. `WRA_E_01` 엔지니어 메인 (`/home`)

**UC** UC-11

| # | 요소 | 내용 | API |
|---|---|---|---|
| GNB | GNB/Engineer | 탭(홈/요청 등록/내 요청) | #3 `GET /auth/me`(새로고침 시 역할 렌더링) |
| ① | KPI 카드 ×4 | 작성중·진행중(AI)·승인대기·반려보완. **평균 승인 소요시간 없음** | #4 `GET /dashboard/summary?role=engineer` |
| ② | 최근 요청 테이블 | 열: `requestNo`/설비/상태 칩/요청일 | #6 `GET /work-requests?mine=true` |
| ③ | 행 클릭 | **서버가 계산한 `nextAction`**을 따라 이동(`DRAFT`→이어서/`AI_RUNNING`→진행/`AI_DONE`→결과/그 외→상세) — 프론트가 상태로 직접 분기하지 않는다 | #7 |
| ④ | "신규 교체 요청" | → `WRA_E_02` | — |

---

## 4. `WRA_E_02` 부품 교체 요청 등록 (`/requests/new`)

**UC** UC-03, UC-04, UC-05

| # | 요소 | 내용 | API |
|---|---|---|---|
| ① | 기본 필드 | `equipment`·`line`·`substance`·`operatingCondition{temperature,pressure}`(자유 텍스트 — v3.0엔 설비 마스터가 없다) | — |
| ② | 제품 유형 선택 | `productType`(`VALVE`/`FITTING_TUBE`/`REGULATOR`/`FILTER`/**`ETC`**) | — |
| ③ | Field/DynamicSpec | 유형별 `specJson` 필수 키(CONTRACT §2): `pressureRating` / `connectionStandard`+`material` / `substanceType` / `freeSpec`. 불일치 시 등록 차단 | #5 → 400 `SPEC_SCHEMA_MISMATCH` |
| ④ | 제품명·증상·현장메모 | `productName`(필수), `symptom`·`siteMemo`(선택) | — |
| ⑤ | Upload/PhotoDropzone | 파트명 **`files`(배열)**, jpg/png/webp, 파일당 10MB, **최대 5장**. 서버가 EXIF 제거+320px 썸네일 생성 | #9 `POST /work-requests/{id}/photos` → 201 |
| ⑥ | "임시 저장" | `draft:true` — 업무 필드 전부 선택값 | #5 `POST /work-requests`(`draft:true`) → 201 |
| ⑦ | "AI 검증 시작" | `draft:false`로 생성 후 즉시 실행 트리거. body는 `{workRequestId}`만 — **경로가 `/work-requests/{id}/agent-runs`가 아니라 최상위 `/agent-runs`** | #5(`draft:false`) → 201, 이어서 #11 `POST /agent-runs` → 202 |

> **팀 확인 필요(CONTRACT §8-7)**: 사진 업로드(⑤)는 `workRequestId`가 있어야 호출 가능한 구조라, 폼 작성 중 사진을 먼저 첨부하려면 그 시점에 `draft:true`(⑥)가 암묵적으로 선행돼야 한다. 이 문서는 이 제약을 그대로 기록만 한다 — 임의 확정 아님.

---

## 5. `WRA_E_03` AI 검증 진행 (`/requests/{id}/run`)

**UC** UC-06

| # | 요소 | 내용 | API |
|---|---|---|---|
| ① | Card/Agent ×3 | `A1` 규격·호환 / `A2` 법령 / `A3` 안전서류. 상태 칩(`WAITING`/`RUNNING`/`DONE`/`FAILED`) | #12 `GET /agent-runs/{runId}` |
| ② | 폴링 | **`pollIntervalMs:2500`(서버가 값을 내려줌)** 간격. 특정 step만 실패해도 HTTP 200 유지 + `errorMessage` 표시 | #12 |
| ③ | "결과 확인" 버튼 | 응답의 **`allDone:true`** 이전엔 비활성. `true`가 되면 서버가 `status`를 `AI_DONE`으로 전환 | — |

---

## 6. `WRA_E_04` AI 결과 확인·수정 (`/requests/{id}/result`)

**UC** UC-07, UC-08 · **데모 클라이맥스**

| # | 요소 | 내용 | API |
|---|---|---|---|
| ① | 요청 정보 헤더 | 설비·제품명·유형·`specJson`·증상·현장메모·사진 썸네일 | #7 `GET /work-requests/{id}` |
| ② | Card/AIResultEditable — `A1`/`A2` | `items[]`(`{itemId,text,edited}`) 텍스트 항목 추가/삭제/편집 | — |
| ③ | Card/AIResultEditable — `A3` | `documents[]`(`{docId,type,name,content,edited}`) 초안 편집 | — |
| ④ | 저장 | 변경된 배열 **전체**를 보낸다(전체 치환, PUT-like) — 부분 patch가 아니다. 배열에 없는 기존 id는 삭제, id 없이 오면 신규 추가 | #13 `PATCH /agent-results/{id}` → 200 / 409 `RESULT_LOCKED` |
| ⑤ | 편집 표시 | `edited:true` 항목을 AI 원본과 시각적으로 구분(가드레일) | — |
| ⑥ | `engineerNote` textarea | 비어 있으면 제출 차단 | #8 `PATCH /work-requests/{id}` |
| ⑦ | "제출" 버튼 | 서버 검증 4가지(A1·A2·A3 결과 존재/`engineerNote`/A2 1건↑/상태 `AI_DONE`·`REJECTED`) | #14 `PATCH .../submit-approval` → 200 / 422 `SUBMIT_REQUIRED_FIELD_MISSING` |

---

## 7. `WRA_E_05` 내 요청 목록 (`/my/requests`)

**UC** UC-12, UC-10, UC-04

| # | 요소 | 내용 | API |
|---|---|---|---|
| ① | Tabs/StatusFilter | 상태 탭. **`status`는 콤마로 다중 지정 가능**(예: `REJECTED,DRAFT`) | #6 `GET /work-requests?mine=true&status=` |
| ② | 요청 테이블 | `requestNo`/설비/상태 칩/요청일. 빈 목록도 200 + `content:[]` | #6 |
| ③ | "이어서"(`DRAFT`) | `nextAction`이 가리키는 `WRA_E_02`로 이동 | #7 |
| ④ | "사유 보기"(`REJECTED`) | `approval.reason` 인라인 표시 | #7 |
| ⑤ | "수정 후 재제출" | `WRA_E_04` 재진입 → 제출 재호출 시 `PENDING` 복귀, 직전 `approval` 이력은 삭제되지 않고 보존 | #14 |

---

## 8. `WRA_S_01` 요청 관리(승인 대기) (`/manage/requests`)

**UC** UC-11

| # | 요소 | 내용 | API |
|---|---|---|---|
| GNB | GNB/SafetyManager | 탭(요청 관리/처리 이력) | — |
| ① | KPI 카드 ×4 | 승인대기·오늘처리·이번달승인·이번달거절 | #4 `GET /dashboard/summary?role=safety` |
| ② | 거절 사유 TOP5 | `rejectReasonsTop` | ①과 동일 응답 |
| ③ | 승인 대기 테이블 | `requestNo`/설비/요청자/요청일 | #6 `GET /work-requests?status=PENDING` |
| ④ | 행 클릭 | → `WRA_S_02` | #7 |

---

## 9. `WRA_S_02` 요청 상세(승인/거절) (`/manage/requests/{id}`)

**UC** UC-09 · **데모 클라이맥스**

| # | 요소 | 내용 | API |
|---|---|---|---|
| ① | 요청 정보 | 설비·제품명·유형·`specJson`·증상·현장메모 | #7 `GET /work-requests/{id}` |
| ② | 사진 썸네일 | 클릭 → 원본 열람 | #10 `GET /work-requests/{id}/photos` |
| ③ | Card/AIResultReadonly — `A1`/`A2`/`A3` | **`agentRun.results[].editable`는 항상 `false`**(안전관리자는 절대 수정 불가). `edited:true` 항목 구분은 유지 | ①에 포함 |
| ④ | `engineerNote` | 엔지니어 설명 | ①에 포함 |
| ⑤ | Panel/Decision | "승인"(사유 불필요, 즉시) / "거절"+사유(10자↑ 필수). **체크리스트 없음** | #15 `POST /approvals`(body `{workRequestId, decision, reason?, reasonCategory?}`, **최상위 경로**) |
| ⑥ | 승인 처리 | → `APPROVED` | #15 `{decision:"APPROVE"}` → 201 |
| ⑦ | 거절 처리 | 사유 미입력/10자 미만 → 차단 | #15 `{decision:"REJECT", reason}` → 201 / 400 `REJECT_REASON_REQUIRED` |
| — | 오류 | 권한 없음/이미 결정됨/`PENDING` 아님 | 403 `FORBIDDEN_ROLE` · 409 `ALREADY_DECIDED` · 409 `NOT_PENDING` |

---

## 10. Phase 2 — v3.0 범위 외

A4 벤더 에이전트, 법령·설비·부품 마스터·호환표(N:M 관계 포함)는 v3.0 DB(7테이블+제안1)에 없다 — 대응 화면·요소도 없다. 상세 사유는 `docs/02_usecase/usecase_spec.md` §3.5.
