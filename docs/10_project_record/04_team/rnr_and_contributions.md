# R&R 과 담당별 산출물

팀: 광주 2반 5조 · SKALA 4기 Full-Stack Engineering AI 웹 서비스 설계 Mini-project

| 담당 | 역할 | 주요 산출물 |
|---|---|---|
| **장병헌** | 지휘·BE·발표 | 범위 결정(게이트) · Figma/Stitch · Supabase · 발표 · `docs/08_presentation/` |
| 은태현 | PM · DBA | `docs/00_INDEX.md` · `09_qa/self_review_rubric.md` · `09_qa/progress_board.md` · ERD 검증 |
| 문승은 | Product & UX · FE | `frontend/**` 9화면 · `03_wireframe/figma_build_guide.md` · `wireframe_spec.md` |
| 신서현 | DevOps & Infra | `.github/workflows/ci.yml` · `09_qa/devops_report.md` · E2E · 재현 환경 |
| 정구현 | API Architect · BE | `docs/07_api/openapi.yaml` · `postman/` · `scripts/e2e_live_v3.sh` · `09_qa/postman_verification.md` |

## 커밋 정책 (`decision_log.md` D-08)
커밋은 팀장 계정 단일 명의. **커밋 본문에 담당 역할·이름을 명시**한다.
```
feat(be): 인증·역할 분기 구현

담당: 정구현 (API Architect) · 장병헌 (BE)
커밋: 장병헌 계정 통합 커밋 — 팀 합의
Contract: docs/CONTRACT.md v3.0 §2.1
```
발표·`qa_bank.md` 에서 **"각자 계정으로 커밋했다"고 말하지 않는다.** `git shortlog -sn` 한 줄로 반박된다.

## 사람이 직접 해야 하는 것 (에이전트 대행 불가)
| 담당 | 항목 | 상태 |
|---|---|---|
| 장병헌 | Figma 또는 Stitch 와이어프레임 | ⏳ 도구 선택 대기 |
| 장병헌 | Supabase 프로젝트 생성 + DDL·시드 실행 | ⏳ 진행 중 (`docs/06_erd/supabase_apply.md`) |
| 은태현 | 발표 슬라이드 실물 제작 | ⏳ |
| 전원 | 회고 각자 작성 · 리허설 3회 · 타 조 질의 1개 | ⏳ |
