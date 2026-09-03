# Argus — E2E 연동 테스트 체크리스트 (DevOps용)

담당: 신서현 · 실행 시점: 2일차 17:00 CP4(1차) · 3일차 09:30(2차, 전 항목) · 3일차 14:00 코드 프리즈 후(3차, P0만)
기준: `docs/CONTRACT.md` REST API 표 · Mock 동작 · 승인 규칙. 결과 칸은 ✔ / ✘ / — (미실행) 으로 기록하고 실패 시 이슈 번호를 적는다.

사전 조건
- BE: `uvicorn app.main:app --reload --port 8000` 기동, `AI_PROVIDER=MOCK`, `BACKGROUND_ADVANCE=false`, 시드 데이터(요청 5건, 사용자 4명, 설비 3, 부품 4, 법령 6) 적재
- FE: `VITE_USE_MOCK=false`, `npm run dev` → http://localhost:5173
- 도구: 브라우저 DevTools Network 탭 + Postman(또는 curl) 로 상태코드 확인

---

## 1. 정상 흐름 (P0 — 데모 경로)

| ID | 시나리오 | 호출 API | 기대 상태코드 / 화면 결과 | 결과 | 담당 |
|---|---|---|---|---|---|
| E2E-01 | 화면1 진입, KPI 표시 | `GET /api/v1/dashboard/summary` | 200 · `in_progress`, `pending_approval`, `avg_approval_hours`, `as_is_baseline_hours`(168), `completed_this_month` 5개 KPI 카드 표시 | ☐ | 신서현 |
| E2E-02 | 작업요청 목록 5건 표시 | `GET /api/v1/work-requests?page=1&size=20` | 200 · `{items:[…], total:5}` · 상태 뱃지 REQUESTED/RUNNING/REVIEW/PENDING_APPROVAL/APPROVED 각 1건 | ☐ | 신서현 |
| E2E-03 | 상태 필터 | `GET /api/v1/work-requests?status=PENDING_APPROVAL` | 200 · items 1건, total 1 | ☐ | 신서현 |
| E2E-04 | 설비·부품 드롭다운 로드 | `GET /api/v1/equipments`, `GET /api/v1/parts` | 200 · 설비 3(EQ-GC-02, EQ-VLV-07, EQ-SCR-01), 부품 4 | ☐ | 문승은 |
| E2E-05 | 작업요청 생성 | `POST /api/v1/work-requests` body: equipment_id=EQ-GC-02, part_id=P-VLV-001, symptom, site_check_note, requested_by=U-001 | **201** · 응답 `id`(WR-…), `status:"REQUESTED"` · 화면2로 이동, 상단 요청 정보 표시 | ☐ | 정구현 |
| E2E-06 | 상세 조회 (run 없음) | `GET /api/v1/work-requests/{id}` | 200 · `latest_run: null`, `approvals: []` · 타임라인 4카드 모두 비활성, "에이전트 실행" 버튼 활성 | ☐ | 문승은 |
| E2E-07 | 에이전트 실행 | `POST /api/v1/work-requests/{id}/agent-runs` | **202** · `{run_id, overall_status:"RUNNING"}` · work_request.status → `RUNNING` · 4카드 `PENDING` | ☐ | 장병헌 |
| E2E-08 | 폴링 1회차 | `GET /api/v1/agent-runs/{runId}` | 200 · SPEC `DONE`, 나머지 `PENDING` · SPEC 카드 결과 요약(`spec_match`, 대안 1건 `allowed_for_toxic_gas:false`) | ☐ | 장병헌 |
| E2E-09 | 폴링 2회차 | 동일 | 200 · LEGAL `DONE` · 적용 법령 3건 · 필수 절차 4건 | ☐ | 장병헌 |
| E2E-10 | 폴링 3회차 | 동일 | 200 · SAFETY_DOC `DONE` · 문서 2건, WORK_PERMIT `missing:["작업자 2명 이름"]` | ☐ | 장병헌 |
| E2E-11 | 폴링 4회차 | 동일 | 200 · VENDOR `DONE` · `overall_status:"REVIEW"` · `summary` 표시 · 폴링 중단 · work_request.status `REVIEW` | ☐ | 장병헌 |
| E2E-12 | 상세 재조회 (run 포함) | `GET /api/v1/work-requests/{id}` | 200 · `latest_run.overall_status:"REVIEW"`, `status:"REVIEW"` · 승인 요청 버튼 활성 | ☐ | 정구현 |
| E2E-13 | 서류 초안 열람 | `GET /api/v1/documents/DOC-0101` | 200 · `type:"WORK_PERMIT"`, `missing` 배열 · 모달/패널에 본문 표시 | ☐ | 문승은 |
| E2E-14 | 호환표 열람 | `GET /api/v1/parts/P-VLV-001/compatibility` | 200 · `{part, alternatives:[…]}` · SPEC 카드 상세 | ☐ | 문승은 |
| E2E-15 | 법령 검색 | `GET /api/v1/laws/search?q=정비&equipmentType=GAS_CABINET&substance=SiH4` | 200 · `{items:[LawArticle]}` 1건 이상 | ☐ | 정구현 |
| E2E-16 | 누락 정보 보완 후 승인 요청 | `PATCH /api/v1/work-requests/{id}/submit-approval` (누락 항목 채움) | **200** · `status:"PENDING_APPROVAL"` · 승인 패널 활성 | ☐ | 장병헌 |
| E2E-17 | 안전관리자 전환 | (FE 세션 store) | 사용자 U-002 이정호(SAFETY_MANAGER) 로 전환, 승인/반려 버튼 노출 | ☐ | 문승은 |
| E2E-18 | 체크리스트 4개 체크 후 승인 | `POST /api/v1/work-requests/{id}/approvals` body: decision=APPROVE, checklist 4개 true, comment | **201** · `Approval` 응답 · `status:"APPROVED"` · 상태 뱃지 갱신 | ☐ | 장병헌 |
| E2E-19 | 대시보드 갱신 | `GET /api/v1/dashboard/summary` | 200 · `pending_approval` 감소, `avg_approval_hours` 재계산 | ☐ | 은태현 |
| E2E-20 | 반려 흐름 | 별도 요청에 `POST …/approvals` decision=REJECT, comment="호환품 부적합" | 201 · `status:"REJECTED"` · 반려 사유가 `reject_reasons_top` 에 반영 | ☐ | 장병헌 |
| E2E-21 | 보완요청 흐름 | `POST …/approvals` decision=REQUEST_INFO, comment | 201 · 상태는 `REVIEW` 로 회귀(또는 CONTRACT 결정에 따름) · 코멘트가 엔지니어 화면에 표시 | ☐ | 장병헌 |
| E2E-22 | AI 설정 조회·수정 | `GET/PUT /api/v1/tenants/T-001/ai-config` | 200 · `[AiConfig]` · provider `LOCAL_LLM`, `egress_allowed:false` 기본값 확인 | ☐ | 정구현 |

## 2. 오류 케이스 (P0 — 루브릭 "Status Code 준수")

| ID | 시나리오 | 호출 API | 기대 상태코드 / 화면 결과 | 결과 | 담당 |
|---|---|---|---|---|---|
| ERR-404-01 | 없는 요청 상세 | `GET /api/v1/work-requests/WR-NOPE` | **404** · `{detail:…}` · FE "요청을 찾을 수 없습니다" 안내 후 목록 복귀 | ☐ | 정구현 |
| ERR-404-02 | 없는 요청에 에이전트 실행 | `POST /api/v1/work-requests/WR-NOPE/agent-runs` | **404** | ☐ | 정구현 |
| ERR-404-03 | 없는 run 조회 | `GET /api/v1/agent-runs/RUN-NOPE` | **404** · FE 폴링 중단 + 에러 토스트 | ☐ | 장병헌 |
| ERR-404-04 | 없는 문서 | `GET /api/v1/documents/DOC-NOPE` | **404** | ☐ | 정구현 |
| ERR-404-05 | 없는 요청에 승인 | `POST /api/v1/work-requests/WR-NOPE/approvals` | **404** | ☐ | 정구현 |
| ERR-409-01 | APPROVED 요청에 에이전트 재실행 | `POST /api/v1/work-requests/{APPROVED id}/agent-runs` | **409** · FE "이미 승인된 요청입니다" · 버튼 비활성 | ☐ | 장병헌 |
| ERR-409-02 | DONE 요청에 에이전트 재실행 | 동일 (DONE id) | **409** | ☐ | 장병헌 |
| ERR-409-03 | run 미완료 상태에서 승인 요청 | `PATCH …/submit-approval` (overall_status RUNNING) | **409** · FE "에이전트 실행이 끝난 뒤 요청하세요" | ☐ | 장병헌 |
| ERR-409-04 | **체크리스트 미완료 상태 APPROVE (데모 포함)** | `POST …/approvals` checklist 중 1개 이상 false, decision=APPROVE | **409** · FE 승인 버튼 비활성 + (직접 호출 시) "필수 체크리스트 4항목을 완료하세요" 토스트 | ☐ | 장병헌 |
| ERR-409-05 | 체크리스트 미완료 상태 REJECT | 동일, decision=REJECT | **201** (반려는 체크리스트 무관) | ☐ | 장병헌 |
| ERR-422-01 | 누락 정보 있는 상태에서 승인 요청 | `PATCH …/submit-approval` (WORK_PERMIT missing 미보완) | **422** · 응답에 누락 항목 목록 · FE 누락 필드 하이라이트 | ☐ | 장병헌 |
| ERR-422-02 | 필수 필드 없는 생성 | `POST /api/v1/work-requests` body 에 equipment_id 누락 | **422** (FastAPI 검증) · FE 폼 검증 메시지 | ☐ | 정구현 |
| ERR-422-03 | 잘못된 decision 값 | `POST …/approvals` decision="OK" | **422** | ☐ | 정구현 |
| ERR-422-04 | 잘못된 status 필터 | `GET /api/v1/work-requests?status=FOO` | **422** (또는 200 빈 목록 — CONTRACT 결정 후 고정) | ☐ | 정구현 |

## 3. 비기능 · 연동 점검

| ID | 항목 | 확인 방법 | 기대 결과 | 결과 | 담당 |
|---|---|---|---|---|---|
| NF-01 | CORS | 브라우저 콘솔 | `http://localhost:5173` 에서 호출 시 CORS 오류 없음 | ☐ | 신서현 |
| NF-02 | vite proxy | Network 탭 | `/api/v1/*` 요청이 8000 으로 전달, 응답 헤더 `content-type: application/json` | ☐ | 신서현 |
| NF-03 | 필드명 일치 | 응답 JSON vs CONTRACT | `run_id`, `overall_status`, `steps[].agent`, `checklist` 키 등 대소문자·스네이크 케이스 동일 | ☐ | 정구현 |
| NF-04 | 폴링 간격·중단 | Network 탭 | 3초(±) 간격, REVIEW 도달 후 추가 호출 없음 | ☐ | 문승은 |
| NF-05 | Swagger | http://localhost:8000/docs | 15개 엔드포인트, 응답 코드 200/201/202/404/409/422 문서화 | ☐ | 정구현 |
| NF-06 | Mock 모드 단독 실행 | `npm run dev:mock` | BE 종료 상태에서 90초 시나리오 완주 | ☐ | 문승은 |
| NF-07 | Postman Mock 단독 실행 | `VITE_API_BASE` 를 Mock URL 로 교체 | 목록·상세·타임라인 표시 (전이는 예시 응답 순서대로) | ☐ | 정구현 |
| NF-08 | DB 전환 | `DATABASE_URL` 을 Supabase 로 교체 후 기동 | 시드 후 목록 5건 동일 표시 (실패 시 SQLite 유지, 리스크 R2) | ☐ | 은태현 |
| NF-09 | audit_logs | DB 조회 | 승인 시 `approvals` 1행 + `audit_logs` 1행 | ☐ | 은태현 |
| NF-10 | 새로고침 복원 | 화면2에서 F5 | `GET /work-requests/{id}` 로 latest_run 복원, 타임라인 상태 유지 | ☐ | 문승은 |

---

## 4. 데모 리허설 체크리스트 (3일차 13:00 · 14:00 · 14:40)

### 4.1 환경
| 항목 | 확인 | 결과 |
|---|---|---|
| 발표 노트북 + 백업 노트북 2대에 동일 구성 (`develop` 최신, `.env` 동일) | `git log -1` 해시 일치 | ☐ |
| BE 기동 (`uvicorn … --port 8000`), Swagger 접속 확인 | http://localhost:8000/docs | ☐ |
| FE 기동 (`npm run dev`), `VITE_USE_MOCK=false` | http://localhost:5173 | ☐ |
| Postman Mock 서버 URL 살아있음 (백업) | Postman 에서 `GET /work-requests` 200 | ☐ |
| 네트워크: 강의실 Wi-Fi 없이도 localhost 데모 가능 (Supabase 미사용 시 SQLite) | 비행기 모드 테스트 | ☐ |
| 전원·어댑터·HDMI/USB-C 젠더 | 물리 확인 | ☐ |

### 4.2 브라우저
| 항목 | 결과 |
|---|---|
| Chrome 시크릿 창 (확장 프로그램·자동완성 차단), 확대 125%로 글자 크기 확보 | ☐ |
| 탭 순서: ① 화면1 목록 ② Swagger ③ Postman Mock 백업용 FE(`VITE_API_BASE` 바꾼 두 번째 dev 서버, 포트 5174) | ☐ |
| DevTools Network 탭을 발표 중 잠깐 열어 202 / 409 코드 보여줄 준비 (선택) | ☐ |
| 알림·팝업·화면보호기 끄기, 북마크바 숨김 | ☐ |

### 4.3 데이터 리셋 방법 (리허설마다 실행)
```bash
# SQLite 기본
cd backend
pkill -f uvicorn || true
rm -f argus.db
uvicorn app.main:app --port 8000        # 기동 시 자동 시드 (요청 5건 초기 상태로 복원)

# 확인
curl -s localhost:8000/api/v1/work-requests | python -c "import sys,json; d=json.load(sys.stdin); print(d['total'], [i['status'] for i in d['items']])"
# 기대: 5 ['REQUESTED', 'RUNNING', 'REVIEW', 'PENDING_APPROVAL', 'APPROVED']
```
- Supabase 사용 시: `python -m app.db.seed --reset` (시드 스크립트에 reset 옵션 제공, DBA 확인)
- FE Mock 모드는 새로고침만으로 초기화

### 4.4 백업 경로: Postman Mock 서버 전환 (BE 장애 시 30초 내)
1. 두 번째 터미널에서 미리 기동해 둔 `VITE_API_BASE=https://<mock-id>.mock.pstmn.io/api/v1 npm run dev -- --port 5174` 탭으로 전환
2. Postman Mock 예시 응답은 데모 순서(목록 → 생성 201 → agent-runs 202 → agent-runs GET 4단계 → submit-approval 200 → approvals 409 → approvals 201)로 저장되어 있어야 함 — `postman/` 컬렉션의 Examples 이름을 순서 접두어로 정렬
3. 발표자 멘트: "백엔드는 Swagger로 별도 시연하겠습니다" → Swagger 탭에서 `POST …/agent-runs` 202, `POST …/approvals` 409 실호출
4. 최후 수단: `npm run dev:mock` (FE 인메모리 Mock) — 네트워크 무관

### 4.5 타이밍
| 구간 | 목표 | 결과 |
|---|---|---|
| 슬라이드 (문제·해결·아키텍처·ERD·API·AI-Ready) | 9분 | ☐ |
| 데모 | 90초 (최대 2분 30초) | ☐ |
| 확장·마무리 | 2분 | ☐ |
| 총 | ≤ 15분 (리허설 2회 측정값 기록: ___분 / ___분) | ☐ |
