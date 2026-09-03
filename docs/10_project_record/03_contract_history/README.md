# 계약 변천사

| 버전 | 시각 | 근거 | 파일 | 상태 |
|---|---|---|---|---|
| v1.0 | 09-02 | 기획서 E안v3 | `docs/CONTRACT_v1.0_archived.md` | 보존 |
| v2.0 | 09-03 14:41 | 화면정의서 v2.0 **+ 오케스트레이터 추론** | `docs/CONTRACT_v2.0_superseded.md` | **폐기** |
| **v3.0** | 09-03 15:00 | 팀 「API 명세서 v1.0」 + 「데이터 모델 정의서 v3.0」 **원문** | `docs/CONTRACT.md` | **현행** |

## v2.0 이 폐기된 이유
추론으로 만들었고 팀 원본과 근본적으로 달랐다. 상세는 `01_timeline/incident_log.md` I-01.

## 버전별 핵심 차이

| 항목 | v1.0 | v2.0(폐기) | **v3.0(현행)** |
|---|---|---|---|
| 화면 | 2 | 9 | **9** |
| 테이블 | 14 | 16 | **7 + 제안 1** |
| PK | `WR-`/`RUN-` 문자열 | 동일 | **UUID v4 + `request_no` 분리** |
| 상태 | 7종 | 8종 | **6종** `DRAFT`·`AI_RUNNING`·`AI_DONE`·`PENDING`·`APPROVED`·`REJECTED` |
| 에이전트 | 4종 SPEC/LEGAL/SAFETY_DOC/VENDOR | 3종 SPEC/LEGAL/SAFETY_DOC | **3종 `A1`/`A2`/`A3`** |
| 인증 | 없음 | JWT | **JWT Bearer** |
| 승인 | 체크리스트 4항목 **409 blocking** | blocking 폐지 | **폐지** (자가승인 403 은 유지) |
| 오류 포맷 | `{detail}` | `{detail}` | **`{code, message, fieldErrors?}`** |
| API | 15 | 19 | **15** |
| 필드 표기 | snake_case | snake_case | **camelCase** |
| N:M | 2개 | 2개 | **0개** (Phase 2) |

## 미확정 (계약 §8 — 팀 확인 필요)
서비스명(FixGuide/Argus) · `reasonCategory` enum화 여부 · 사진 업로드 시 DRAFT 선생성 전제 · `approvals` append-only 유지 여부 · 결과 수정을 항목 단위 API 로 쪼갤지
