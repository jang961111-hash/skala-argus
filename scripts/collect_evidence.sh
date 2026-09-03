#!/usr/bin/env bash
# 기록 증거 자동 수집 — docs/10_project_record/RECORD_KEEPING.md §5
# 테스트·빌드 원본 로그와 인벤토리를 타임스탬프 붙여 저장한다.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REC="$ROOT/docs/10_project_record/02_evidence"
TS="$(date +%Y%m%d_%H%M)"
mkdir -p "$REC/test_results" "$REC/inventory"
cd "$ROOT"

echo "== 1/4 pytest =="
( cd backend && DATABASE_URL="sqlite:///./_collect.db" .venv/bin/python -m pytest -q > "$REC/test_results/pytest_$TS.log" 2>&1; rm -f _collect.db )
tail -1 "$REC/test_results/pytest_$TS.log"

echo "== 2/4 라이브 E2E =="
lsof -ti:8820 2>/dev/null | xargs kill -9 2>/dev/null; sleep 1
bash scripts/e2e_live_v3.sh > "$REC/test_results/e2e_live_v3_$TS.log" 2>&1
tail -1 "$REC/test_results/e2e_live_v3_$TS.log"

echo "== 3/4 프론트 빌드 =="
( cd frontend && npm run build > "$REC/test_results/fe_build_$TS.log" 2>&1 )
tail -2 "$REC/test_results/fe_build_$TS.log" | head -1

echo "== 4/4 인벤토리 =="
{
  echo "# 산출물 인벤토리"; echo
  echo "생성: $(date '+%Y-%m-%d %H:%M') · **작업 트리 실측**(커밋 시점 아님)"; echo
  echo "## 규모"; echo '```'
  printf "%-24s %s\n" "추적 파일(git)"   "$(git ls-files | wc -l | tr -d ' ')"
  printf "%-24s %s\n" "변경/신규(미커밋)" "$(git status --porcelain | wc -l | tr -d ' ')"
  printf "%-24s %s\n" "backend .py"     "$(find backend/app backend/tests -name '*.py' | wc -l | tr -d ' ')"
  printf "%-24s %s\n" "frontend .vue"   "$(find frontend/src -name '*.vue' | wc -l | tr -d ' ')"
  printf "%-24s %s\n" "docs 파일"        "$(find docs -type f | wc -l | tr -d ' ')"
  printf "%-24s %s\n" "OpenAPI paths"   "$(grep -cE '^  /' docs/07_api/openapi.yaml)"
  printf "%-24s %s\n" "ERD 테이블"       "$(grep -c '^Table ' docs/06_erd/replaceflow.dbml)"
  echo '```'; echo
  echo "## 디렉터리 구조 (깊이 3)"; echo '```'
  find . -maxdepth 3 -type d -not -path "*/.git*" -not -path "*/node_modules*" \
    -not -path "*/.venv*" -not -path "*/__pycache__*" -not -path "*/dist*" -not -path "*/.omc*" \
    | sort | sed 's|^\./||'
  echo '```'; echo
  echo "## backend"; echo '```'; find backend/app -name "*.py" | sort | sed 's|backend/app/||'; echo '```'; echo
  echo "## frontend"; echo '```'; find frontend/src \( -name "*.vue" -o -name "*.js" \) | sort | sed 's|frontend/src/||'; echo '```'; echo
  echo "## docs"; echo '```'; find docs -type f | sort | sed 's|docs/||'; echo '```'
} > "$REC/inventory/artifacts_inventory.md"
git log --format='%h  %ad  %s' --date=format:'%m-%d %H:%M' > "$REC/inventory/git_log.txt"
echo "인벤토리 갱신 완료"

echo
echo "수집 완료 — $REC (타임스탬프 $TS)"
echo "화면 캡처는 수동이다: BE 8000 + FE 5173 띄우고 9화면 재캡처 → 02_evidence/screenshots/"
