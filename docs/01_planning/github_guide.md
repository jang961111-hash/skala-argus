# Argus — GitHub 운영 가이드

담당: DevOps & Infra 신서현 · 2026-09-02
목적: 루브릭 "GitHub 관리 · R&R 적절성" 대비 — **누가 무엇을 했는지 커밋·PR·이슈로 남는 상태**를 3일 내내 유지한다.

---

## 1. 레포 이름 · 기본 설정

| 항목 | 값 |
|---|---|
| 레포 이름 | `skala-argus` (대안: `argus-agent`) — 조직 계정이 있으면 `skala4-team-<번호>/skala-argus` |
| 설명 | Argus — 반도체 설비 부품 교체 승인 프로세스 에이전트 (SKALA 4기 Mini-project) |
| 공개 범위 | Private (발표 후 강사 요청 시 Public 전환) |
| 기본 브랜치 | `main` (보호: PR 필수, 리뷰 1명, force-push 금지) |
| 통합 브랜치 | `develop` |
| Collaborator | 은태현 · 문승은 · 신서현 · 정구현 · 장병헌 (전원 Write) |
| Topics | `skala`, `fastapi`, `vue3`, `agentic-ai`, `on-premise` |

초기 커밋은 신서현이 스캐폴딩(README·.gitignore·PR 템플릿·frontend/backend 뼈대)으로 1회 올리고, **그 뒤 각 폴더의 내용은 담당자가 본인 계정으로 커밋**한다.

## 2. 브랜치 전략

```
main      ── 발표용 안정 버전. develop 에서만 머지 (2일차 저녁·3일차 14:00 코드 프리즈)
develop   ── 통합 브랜치. feature 브랜치 PR 머지 대상
feature/{role}-{topic}
```

| role 접두어 | 담당 | 예시 |
|---|---|---|
| `pm` | 은태현 | `feature/pm-sample-data`, `feature/pm-slides` |
| `db` | 은태현(DBA) | `feature/db-erd`, `feature/db-models-seed` |
| `fe` | 문승은 | `feature/fe-timeline`, `feature/fe-approval-panel` |
| `ops` | 신서현 | `feature/ops-scaffold`, `feature/ops-e2e-checklist` |
| `api` | 정구현 | `feature/api-openapi`, `feature/api-workrequest-router` |
| `be` | 장병헌 | `feature/be-orchestrator`, `feature/be-approval-gate` |
| `docs` | 공통 문서 | `docs/usecase`, `docs/architecture` (role 접두어 대신 `docs/` 사용 가능) |
| `fix` | 버그 | `fix/fe-409-toast` |

규칙
- 브랜치는 `develop` 에서 딴다. 하루 이상 살아있는 feature 브랜치는 만들지 않는다 (작게 자주).
- `docs/CONTRACT.md` 변경은 `feature/pm-contract-*` 브랜치 + PM 승인 필수.
- 머지는 **Squash and merge** 대신 **Merge commit** 을 쓴다 — 개인 커밋이 이력에 그대로 남아야 R&R 채점에 유리하다.

## 3. 커밋 메시지 규칙

형식: `type(scope): subject` — 한글 허용, 50자 이내, 마침표 없음.

| type | 용도 |
|---|---|
| `feat` | 기능·화면·API 추가 |
| `fix` | 버그 수정 |
| `docs` | 문서(기획·ERD·API 명세·README) |
| `chore` | 환경·설정·의존성·.gitignore |
| `refactor` | 동작 변경 없는 구조 정리 |
| `test` | 테스트·E2E 체크리스트 |
| `style` | 포맷·CSS 등 |

scope: `fe` `be` `api` `db` `docs` `ops` `postman` `contract`

예시
```
feat(be): agent-runs 폴링마다 step 1개 DONE 전이 구현
feat(fe): 승인 패널 체크리스트 미완료 시 승인 버튼 비활성
fix(api): submit-approval 누락 정보 422 응답 스키마 CONTRACT 대조 수정
docs(db): ERD DBML 14개 테이블 · N:M 관계 근거 추가
chore(ops): vite proxy /api → localhost:8000 설정
```

본문(선택)에는 "왜"를 쓴다. 페어로 작업했으면 트레일러를 붙인다.
```
Co-authored-by: 문승은 <email@example.com>
```

## 4. PR 규칙 · 템플릿

- PR 대상: `feature/*` → `develop`. 제목은 커밋 규칙과 동일 (`feat(fe): 화면2 타임라인`).
- 리뷰어 1명 이상 (자기 담당 폴더가 아닌 사람). 승인 후 작성자가 머지.
- PR 본문은 아래 템플릿(`.github/PULL_REQUEST_TEMPLATE.md`)이 자동 삽입된다.

```markdown
## 무엇을 했나
<!-- 한 줄 요약. 예: 화면2 에이전트 타임라인 카드 4개 + 3초 폴링 -->

## 관련 산출물 / 루브릭 항목
<!-- 예: docs/03_wireframe 화면2 · 루브릭 "Mock API 데이터 바인딩 화면 시연" -->

## 변경 내용
- 

## CONTRACT 준수 확인
- [ ] 상태값 문자열이 `docs/CONTRACT.md` 와 동일하다
- [ ] Method / Path / Status Code 가 CONTRACT 표와 동일하다
- [ ] JSON 필드명이 CONTRACT 스키마와 동일하다

## 확인 방법
<!-- 실행 명령, 호출한 API, 스크린샷 -->

## 체크
- [ ] 로컬에서 실행 확인 (`uvicorn` / `npm run dev`)
- [ ] 담당 폴더 외 파일을 건드렸다면 담당자에게 알렸다
- [ ] 관련 이슈 번호: #
```

## 5. 이슈 라벨

| 라벨 | 색 | 용도 |
|---|---|---|
| `role:pm` `role:fe` `role:ops` `role:api` `role:be` `role:db` | 파랑 계열 | 담당 Role (R&R 추적) |
| `area:docs` `area:frontend` `area:backend` `area:db` `area:postman` | 회색 | 변경 영역 |
| `type:feature` `type:bug` `type:docs` `type:chore` | 초록/빨강/보라/노랑 | 작업 종류 |
| `rubric:usecase` `rubric:ai-ready` `rubric:erd` `rubric:api` `rubric:demo` `rubric:github` | 주황 | 루브릭 항목 매핑 |
| `day:1` `day:2` `day:3` | 검정 | 일정 |
| `priority:P0` (데모 필수) `priority:P1` `priority:P2` | 빨강 → 연두 | 범위 축소 시 P2부터 제외 |
| `blocked` | 진빨강 | 다른 사람 산출물 대기 |

이슈는 산출물 단위로 1일차 오전에 PM이 일괄 생성하고 담당자를 Assignee로 지정한다. 커밋·PR에 `#이슈번호` 를 적어 연결한다.

## 6. 각자 커밋이 남도록 하는 규칙 (R&R 채점 대비)

1. **담당 폴더는 담당자가 커밋한다.** 다른 사람 노트북에서 작업했더라도 본인 계정으로 push 하거나 `Co-authored-by` 를 붙인다.
2. **git 사용자 설정을 GitHub 계정과 일치**시킨다 (1일차 오전 확인).
   ```bash
   git config user.name  "GitHub표시이름"
   git config user.email "GitHub에 등록된 이메일"
   ```
   이메일이 GitHub 계정에 등록되어 있지 않으면 Contributors 그래프에 잡히지 않는다.
3. **하루 최소 커밋 2건·PR 1건** (문서만 바꿔도 된다). PM이 저녁 체크포인트에 `git shortlog -sn --all` 로 확인한다.
4. Merge commit 사용, Squash 금지 (개인 커밋 보존).
5. 문서 산출물(기획·UC·ERD·API 명세)도 레포에 커밋 — Notion·Drive에만 두지 않는다.
6. PR 본문에 루브릭 항목을 적어 "누가 어느 채점 항목을 담당했는지" 기록으로 남긴다.
7. 발표 슬라이드에 GitHub Insights → Contributors 캡처를 1장 넣는다 (3일차 14:00 캡처).

## 7. `.gitignore`

레포 루트 `/.gitignore` (frontend·backend 공통) — 실제 파일은 루트에 있다.

```gitignore
# --- Python / FastAPI ---
__pycache__/
*.py[cod]
.venv/
venv/
*.egg-info/
.pytest_cache/
.mypy_cache/
*.db
*.sqlite
*.sqlite3
backend/.env

# --- Node / Vite ---
node_modules/
frontend/dist/
frontend/.vite/
npm-debug.log*
yarn-error.log*
*.log

# --- 환경 · 비밀 ---
.env
.env.*
!.env.example
*.pem
*.key

# --- IDE / OS ---
.vscode/
.idea/
*.swp
.DS_Store
Thumbs.db

# --- 발표 산출물 중 대용량 ---
docs/08_presentation/*.pptx
docs/08_presentation/*.mp4
```

주의: `.env.example` 은 커밋한다 (Security & Config Isolation 증빙). 실제 `.env`·API 키·`argus.db` 는 절대 올리지 않는다.

## 8. `CODEOWNERS` 예시

`.github/CODEOWNERS` 로 두면 PR 생성 시 담당자가 자동 리뷰어로 지정된다. GitHub 아이디는 실제 계정으로 교체.

```
# 기본
*                                   @eun-taehyun

# 기획 · 일정 · 계약
/docs/01_planning/                  @eun-taehyun
/docs/CONTRACT.md                   @eun-taehyun @jeong-guhyeon @jang-byungheon
/docs/08_presentation/              @eun-taehyun @jang-byungheon

# UX · FE
/docs/02_usecase/                   @moon-seungeun
/docs/03_wireframe/                 @moon-seungeun
/frontend/                          @moon-seungeun

# DevOps
/.github/                           @shin-seohyun
/.gitignore                         @shin-seohyun
/docs/01_planning/github_guide.md   @shin-seohyun
/docs/09_qa/                        @shin-seohyun
/frontend/vite.config.js            @shin-seohyun
/backend/.env.example               @shin-seohyun

# API · 아키텍처
/docs/04_architecture/              @jeong-guhyeon
/docs/07_api/                       @jeong-guhyeon
/postman/                           @jeong-guhyeon
/backend/app/api/                   @jeong-guhyeon
/backend/app/schemas/               @jeong-guhyeon

# BE · AI
/docs/05_ai_ready/                  @jang-byungheon
/backend/app/services/              @jang-byungheon

# DB
/docs/06_erd/                       @eun-taehyun
/backend/app/models/                @eun-taehyun
/backend/app/db/                    @eun-taehyun
```

## 9. 일일 루틴 (요약)

| 시점 | 할 일 |
|---|---|
| 아침 | `git checkout develop && git pull`, 오늘 이슈 확인, feature 브랜치 생성 |
| 작업 중 | 작은 단위 커밋, 커밋 메시지 규칙 준수 |
| 저녁 | PR 생성 → 리뷰 → 머지, 이슈 닫기, PM이 `git shortlog -sn` 확인 |
| 2일차 저녁·3일차 14:00 | `develop` → `main` 머지, 태그 `v0.1-demo` |
