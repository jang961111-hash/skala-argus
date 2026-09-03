# DevOps / CI 리허설 리포트

담당: DevOps & Infra 신서현 · 2026-09-03 (Day 2)
관련 파일: `.github/workflows/ci.yml`

**v3.0 갱신**: `docs/10_project_record/RECORD_KEEPING.md` 상시 지침 반영. E2E 대상을 `scripts/e2e_live.sh`(v1.0, `docs/CONTRACT.md` v3.0 기준 무효)에서 **`scripts/e2e_live_v3.sh`**로 교체했다. 이하 1절은 v3.0 기준으로 다시 쓴다 — v1.0 수치(35/35, PORT 8801)는 **틀린 게 아니라 대상이 바뀐 것**이라 삭제하지 않고 이 문단에 남긴다.

---

## 1. CI 잡별 로컬 예행 결과 (v3.0)

`.github/workflows/ci.yml` 각 스텝을 러너와 동일한 명령으로 로컬에서 직접 돌렸다.

| 잡 | 명령 | 종료코드 | 소요시간 | 결과 |
|---|---|---|---|---|
| YAML 문법 검증 | `backend/.venv/bin/python -c "yaml.safe_load(...)"` | 0 | <1s | 파싱 성공, `jobs: [backend-test, frontend-build, e2e]`, e2e 스텝 5개(`upload-artifact` 포함) 확인 |
| backend-test | `pip install -q -r requirements.txt` | 0 | 0s (이미 설치됨) | OK |
| backend-test | `pytest -q` | 0 | 1s | **8 passed**, warning 2건(starlette httpx deprecation, 기능 영향 없음) |
| frontend-build | `npm ci --silent` | 0 | 1s | OK (`package-lock.json` 존재 확인) |
| frontend-build | `npm run build` | 0 | 2s | `dist/` 생성, gzip 결과 index.js 69.39kB |
| e2e | `bash scripts/e2e_live_v3.sh` (기본 PORT=8820, 스크립트 자체 기본값 — CI와 동일 조건) | 0 | 4s | **64 / 64 통과**, 실패 0 |
| e2e (파이프라인 exit code 검증) | `bash -eo pipefail -c 'bash scripts/e2e_live_v3.sh \| tee log'` | 0 | 4s | GitHub Actions `run:` 기본 셸(`bash --noprofile --norc -eo pipefail`)과 동일 조건으로 재현 — `tee`를 거쳐도 스크립트 실패 시 파이프라인이 실패로 잡히는 것 확인 |

(v1.0 참고용 이전 실측 — 대상 무효화됨: `PORT=8801 bash scripts/e2e_live.sh` → 35/35 통과, 1s, 2026-09-03. `docs/10_project_record/02_evidence/test_results/e2e_live_v3_*.log` 3건이 팀장 쪽 `collect_evidence.sh` 실행으로 이미 64/0 실측을 남겨뒀고, 위 표의 수치는 그것과 별개로 이 세션에서 CI 워크플로 예행 목적으로 직접 재실측한 것 — 값이 일치함을 교차 확인했다.)

**주의(정직하게 기록)**: `backend-test`/`e2e` 로컬 예행은 기존 `backend/.venv`(이미 의존성 설치됨)로 돌렸다. CI에서는 `e2e` 잡이 `python -m venv .venv`로 **매번 새로 venv를 만든다** — 이 스텝 자체는 로컬에서 별도로 새 venv를 만들어 재현하지는 않았고, `pip install -r requirements.txt`가 멱등하게 성공하는 것과 동일 명령이 기존 venv에서 통과하는 것으로 간접 확인했다. 최초 PR이 올라가면 Actions 로그에서 fresh-venv 케이스를 1회 직접 확인할 것.

CI는 3개 잡(backend-test / frontend-build / e2e)으로 구성했고 `e2e`는 `needs: [backend-test, frontend-build]`로 앞 두 잡이 통과해야 시작한다. pip·npm 캐시(`actions/setup-python`·`actions/setup-node`의 `cache:` 옵션)를 적용했다.

**`collect_evidence.sh`를 CI에 넣을지 판단**: 안 넣기로 했다. 이 스크립트는 pytest→E2E→FE build→인벤토리를 한 번에 도는데, CI에서는 pytest와 FE build를 이미 `backend-test`/`frontend-build` 잡이 각자 병렬로 돌리고 있어서 그대로 넣으면 같은 작업을 중복 실행하게 되고, 잡 경계(뭐가 실패했는지 한눈에 안 보임)도 흐려진다. 게다가 `collect_evidence.sh`는 `docs/10_project_record/02_evidence/` 아래에 파일을 쓰는데, **CI가 만든 파일이 워킹 트리에 남으면 다음 사람이 실수로 커밋할 위험**이 있다(레코드킵 원칙은 "실측 로그를 남긴다"이지 "CI가 리포에 써넣는다"가 아니다). 그래서 `e2e` 잡은 `scripts/e2e_live_v3.sh`만 직접 돌리고, 로그는 `actions/upload-artifact@v4`로 **Actions 아티팩트**(리포 밖, 14일 보관)에만 남기도록 했다. 로컬 증거 수집은 지금처럼 팀원이 `bash scripts/collect_evidence.sh`를 직접 돌려 `docs/10_project_record/02_evidence/`에 커밋하는 흐름을 유지한다 — CI 자동 커밋 도입은 하지 않았다(원한다면 별도 논의 필요).

---

## 2. 재현 환경 요구사항 (팀원 5명 각자 노트북)

**함정 1**: macOS 기본 `python3`은 **3.9**다. `backend/requirements.txt` 상단 주석대로 SQLAlchemy 모델이 PEP 604 문법(`str | None`)을 쓰기 때문에 **3.9에서는 임포트 단계에서 죽는다.** 반드시 3.10 이상, CI와 동일하게 맞추려면 **3.11**을 쓸 것.

**함정 2 (같은 계열 — bash 버전)**: macOS 기본 `/bin/bash`도 **3.2**다 (`bash --version` 로 이 세션에서 실측 확인). `scripts/e2e_live_v3.sh`는 `set -u` 상태에서 `"${arr[@]}"` 를 전개하는데, **bash 3.2에서는 빈 배열일 때 이게 `unbound variable`로 죽는다** (팀장이 발견·수정, `${arr[@]+"${arr[@]}"}` 패턴으로 교체). 팀원이 Homebrew로 bash 5.x를 새로 깔았더라도 `#!/usr/bin/env bash`가 PATH 순서에 따라 여전히 `/bin/bash`(3.2)를 집을 수 있다 — 재현 안 되면 `bash --version`부터 확인.

```bash
# bash 버전 확인 — 3.x 여도 3.2는 위 버그가 있다. Homebrew bash(5.x)가 있으면 PATH 앞쪽에 두는 게 안전
bash --version | head -1
brew install bash          # 필요시
```

### 확인 순서 (팀원 각자 1회)
```bash
# 1. Python 버전 확인 — 3.9면 아래 설치 필요
python3 --version

# 2. (3.9인 경우만) Homebrew로 3.11 설치
brew install python@3.11

# 3. 레포 backend 폴더에서 전용 venv 생성 (스크립트가 backend/.venv 경로를 하드코딩해서 찾는다)
cd backend
/opt/homebrew/opt/python@3.11/bin/python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest -q          # 8 passed 나오면 OK

# 4. Node 버전 확인 — 18 이상 (CI는 20 사용)
node --version
# 18 미만이면: brew install node@20  (또는 nvm install 20)

# 5. 프론트 의존성
cd ../frontend
npm ci                        # package-lock.json 이 있으므로 npm install 대신 ci
npm run build                 # dist/ 생성되면 OK

# 6. E2E 라이브 검증 v3.0 (백엔드 venv 필요, 위 3번 선행) — v1.0 스크립트(e2e_live.sh)는 CONTRACT v3.0 기준 무효이니 쓰지 말 것
cd ..
bash scripts/e2e_live_v3.sh          # 마지막 줄 "실패 0" 이면 OK (기본 PORT=8820)
```

---

## 3. 발표 당일 리스크 및 대응 (명령 한 줄 복구)

| 리스크 | 증상 | 복구 명령 (한 줄) |
|---|---|---|
| 네트워크 없음 | `npm ci`/`pip install` 실패, GitHub Actions 연동 불가 | 발표는 로컬 실행이 기준이므로 **사전에** `npm ci && npm run build`, `backend/.venv/bin/pytest -q`를 발표 직전 오프라인 캐시 상태로 1회 완주해 둔다. 당일엔 재설치 시도 금지 — `npm run dev` / `uvicorn app.main:app --port 8000`만 실행 |
| 포트 충돌 (8000/5173 등 이미 사용 중) | `Address already in use` | `lsof -ti:8000 \| xargs kill -9` (5173은 `lsof -ti:5173 \| xargs kill -9`) |
| 포트 충돌 (E2E 전용 8820) | `scripts/e2e_live_v3.sh` 기동 실패 또는 응답 `000` — 직전에 깨진 실행이 서버 프로세스를 못 내리고 남긴 경우 | `lsof -ti:8820 \| xargs kill -9` (`collect_evidence.sh`가 매 실행 전 자동으로 이걸 한다) |
| DB 파일 꼬임 (`argus.db` 상태 이상) | 이전 데모 데이터 잔존, 상태머신 불일치 | `rm -f backend/argus.db` (수동 데모용. E2E 스크립트는 자기 DB를 알아서 지운다 — v1.0은 `argus.db`, v3.0은 `backend/e2e_v3.db`를 매 실행 초기화) |
| E2E 상태 오염 (첫 실행만 대량 실패) | 직전에 죽은 서버·DB가 남아 46건 실패 → 재실행하면 3건으로 줄어드는 패턴 (팀장 실측 사례) | 포트부터 정리(`lsof -ti:8820 \| xargs kill -9`) 후 재실행. 반복돼도 안 줄면 서버 코드 문제이니 CONTRACT 대조 필요 |
| npm 캐시 없음 (새 노트북/캐시 삭제됨) | `npm ci` 느림 또는 실패 | `cd frontend && rm -rf node_modules && npm ci` (오프라인이면 캐시 있는 팀원 노트북의 `node_modules`를 그대로 tar로 옮겨 `tar xzf` 복원) |
| `.env` 파일 없음 (신규 노트북) | 백엔드 기동 실패 | `cd backend && cp .env.example .env` |

---

## 4. `.gitignore` 실측 점검 — 후속 조치 반영 (2026-09-03 갱신)

**최초 발견(위 발견 시점 실측)**: `git status --porcelain=v1` 에서 `.omc/state/hud-stdin-cache.json` 이 tracked 상태로 수정 표시되고, 이 세션이 만든 `frontend/.omc/` 가 untracked 로 새로 생겼다. `.gitignore`에 `.omc/` 항목이 없어서 `git add .` 시 그대로 커밋될 위험이 있었다.

**조치 완료 (팀장)**: `.gitignore` 에 `.omc/` · `**/.omc/` 2줄 추가 + 인덱스에서 제거. 이번 세션에서 재확인:
```
$ grep -n omc .gitignore
44:.omc/
45:**/.omc/
$ git ls-files | grep '^\.omc'
(출력 없음 — 더 이상 추적되지 않음)
```
`git status --porcelain` 에도 이제 `.omc/` 관련 항목이 전혀 안 뜬다. **인덱스 기준으로는 해결됨.**

**미해결 — 커밋 이력**: 과거 커밋에 `.omc/state/*` 가 이미 들어가 있어 `git log`로 보면 여전히 남아 있다. 팀장이 `git filter-branch --index-filter` 로 이력에서 purge 시도했으나 **다른 트랙(팀원)이 동시에 파일을 쓰고 있어 거부됨** — 팀장 승인은 받았고, 작업 트리가 조용해지는 시점에 재시도 예정. **발표 전까지 이 purge가 안 끝나도 기능·데모에는 영향 없음**(인덱스에서는 이미 빠졌으므로 새 커밋에는 안 실림) — 다만 `git clone` 직후 레포 크기나 `.omc/state/*` 이력 노출이 남아있다는 점은 알아둘 것.

---

## 5. 브랜치 보호 규칙 — GitHub 웹 설정 클릭 순서

`docs/01_planning/github_guide.md`의 브랜치 전략(`main` 보호, PR 필수, 리뷰 1명, force-push 금지)을 실제로 걸려면 저장소 관리자가 아래 순서로 클릭한다 (Actions/워크플로 설정은 이미 코드로 커밋되지만, 브랜치 보호는 GitHub 웹 UI에서만 가능하다).

1. 저장소 페이지 상단 **Settings** 탭 클릭
2. 좌측 메뉴 **Branches** 클릭
3. **Branch protection rules** 섹션에서 **Add branch protection rule** (또는 **Add rule**) 클릭
4. **Branch name pattern** 입력란에 `main` 입력
5. **Require a pull request before merging** 체크
   - 하위 옵션 **Require approvals** 체크, 숫자를 **1**로 설정
6. **Require status checks to pass before merging** 체크
   - 검색창에서 `backend-test`, `frontend-build`, `e2e` 3개 잡 이름을 찾아 체크 (CI가 최소 1회 실행된 뒤에만 목록에 뜬다 — PR 하나를 먼저 올려서 워크플로를 한 번 돌려야 함)
   - **Require branches to be up to date before merging** 체크
7. **Require conversation resolution before merging** 체크 (선택, 권장)
8. **Do not allow force pushes**가 기본으로 잠겨 있는지 확인 — **Allow force pushes** 체크박스는 반드시 **해제 상태 유지**
9. **Allow deletions** 체크박스도 **해제 상태 유지**
10. 맨 아래 **Create**(신규 규칙) 또는 **Save changes**(수정) 버튼 클릭
11. 같은 방식으로 **Branch name pattern**에 `develop` 입력 후 2~10 반복 (요구 리뷰어 수는 팀 재량으로 0 또는 1)
12. 저장 후 `main` 대상 아무 PR이나 열어 **Merge** 버튼이 상태 체크 통과 전까지 비활성화되는지 확인

---

## 요약

- `.github/workflows/ci.yml` v3.0 갱신 — e2e 잡이 `scripts/e2e_live_v3.sh` 실행(v1.0은 CONTRACT 무효), 로그를 `actions/upload-artifact`로 남기고 리포에는 커밋 안 함
- 로컬 예행 전부 통과: pytest 8/8, npm build OK, E2E v3.0 64/64 (기본 PORT=8820), pipefail 조건에서도 파이프라인 exit code 정상 전파 확인
- Python 3.9·bash 3.2(둘 다 macOS 기본) 함정 문서화, 포트 8820 충돌·E2E 상태 오염 복구 명령 추가
- `.gitignore`의 `.omc/` 누락은 팀장이 인덱스 기준 해결(재확인 완료) — 커밋 이력 purge만 트리가 조용해지면 재시도 예정, 발표 전 기능에는 영향 없음
- 브랜치 보호 규칙은 GitHub 웹 UI 전용이라 클릭 순서 12단계로 문서화 (Settings → Branches → Add rule)
- `collect_evidence.sh`는 CI에 넣지 않기로 판단(잡 중복·워킹트리 오염 위험) — 이유를 1절에 기록
