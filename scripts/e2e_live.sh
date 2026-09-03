#!/usr/bin/env bash
# 라이브 End-to-End 검증 — 실제 uvicorn 서버를 띄우고 docs/09_qa/e2e_test_checklist.md 의
# 정상 경로와 오류 경로를 HTTP status code 로 실측한다. pytest(TestClient)와 달리
# 네트워크 스택·CORS·직렬화를 실제로 통과시키므로 발표 데모와 같은 조건이다.
#
# 사용법:  bash scripts/e2e_live.sh          (backend/.venv 가 있어야 함, Python 3.10+)
# 종료코드: 실패 건수 (0 이면 전부 통과)

set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8765}"
B="http://localhost:${PORT}/api/v1"
PY="$ROOT/backend/.venv/bin/python"
[ -x "$PY" ] || { echo "backend/.venv 가 없다. README 의 빠른 시작을 먼저 실행하라 (Python 3.10+)"; exit 99; }

cd "$ROOT/backend"
[ -f .env ] || cp .env.example .env
rm -f replaceflow.db                      # 시드부터 재현하기 위해 매번 초기화
"$PY" -m uvicorn app.main:app --port "$PORT" > /tmp/rf_e2e_uvicorn.log 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT
for _ in $(seq 1 40); do curl -sf "$B/dashboard/summary" >/dev/null 2>&1 && break; sleep 0.5; done

PASS=0; FAIL=0
BODY=/tmp/rf_e2e_body.json
chk(){ if [ "$2" = "$3" ]; then printf '  PASS  %-28s %s\n' "$1" "$2"; PASS=$((PASS+1));
       else printf '  FAIL  %-28s 기대 %s, 실제 %s\n' "$1" "$3" "$2"; FAIL=$((FAIL+1)); fi; }
# payload 를 파일로 넘긴다 — 중첩 따옴표 이스케이프에서 나는 오탐을 없애기 위해
req(){ local m=$1 u=$2 f=${3:-}
       if [ -n "$f" ]; then curl -s -o "$BODY" -w '%{http_code}' -X "$m" "$u" -H 'Content-Type: application/json' --data-binary "@$f"
       else curl -s -o "$BODY" -w '%{http_code}' -X "$m" "$u"; fi; }
field(){ "$PY" -c "import json,sys;d=json.load(open('$BODY'));print(d.get('$1',''))"; }

P=/tmp/rf_payload.json
echo "== 1. 작업요청 생성 =="
cat > $P <<'J'
{"tenant_id":"T-001","equipment_id":"EQ-GC-02","part_id":"P-VLV-001",
 "symptom":"가스 유량 이상, 밸브 누설 의심","site_check_note":"현장 확인 결과 밸브 시트 마모","requested_by":"U-001"}
J
chk "POST /work-requests" "$(req POST "$B/work-requests" $P)" "201"
WR=$(field id); chk "생성 직후 상태" "$(field status)" "REQUESTED"; echo "        WR=$WR"

echo "== 2. 상태머신 순서 가드 =="
echo '{"approver_id":"U-002","decision":"APPROVE","checklist":{}}' > $P
chk "승인 선행 차단" "$(req POST "$B/work-requests/$WR/approvals" $P)" "409"
chk "제출 선행 차단" "$(req PATCH "$B/work-requests/$WR/submit-approval")" "409"

echo "== 3. 에이전트 비동기 실행 =="
chk "POST agent-runs" "$(req POST "$B/work-requests/$WR/agent-runs")" "202"
RUN=$(field run_id); chk "실행 직후 상태" "$(field overall_status)" "RUNNING"; echo "        RUN=$RUN"
chk "중복 실행 차단" "$(req POST "$B/work-requests/$WR/agent-runs")" "409"

echo "== 4. 폴링 4회 — step 순차 DONE =="
for i in 1 2 3 4; do
  req GET "$B/agent-runs/$RUN" >/dev/null
  R=$("$PY" -c "
import json;d=json.load(open('$BODY'))
print(str(len([s for s in d['steps'] if s['status']=='DONE']))+'/'+d['overall_status'])")
  EXP=$i/$([ "$i" -eq 4 ] && echo REVIEW || echo RUNNING)
  chk "폴링 ${i}회 (DONE/상태)" "$R" "$EXP"
done
chk "REVIEW 후 재조회 멱등" "$(req GET "$B/agent-runs/$RUN" >/dev/null; field overall_status)" "REVIEW"

echo "== 5. 승인 요청 — 누락 422 → 보완 200 =="
chk "누락 상태로 제출" "$(req PATCH "$B/work-requests/$WR/submit-approval")" "422"
echo '{"missing_info":{"작업자 2명 이름":"김민준, 박수진"}}' > $P
chk "보완 후 제출" "$(req PATCH "$B/work-requests/$WR/submit-approval" $P)" "200"
chk "상태 전이" "$(field status)" "PENDING_APPROVAL"

echo "== 6. 승인 게이트 (Human-in-the-loop) =="
echo '{"approver_id":"U-002","decision":"APPROVE","checklist":{"WORK_PERMIT":true,"RISK_ASSESSMENT":true,"LOTO_GAS_ISOLATION":true,"GAS_DETECTOR_CHECK":false}}' > $P
chk "체크리스트 미완 차단" "$(req POST "$B/work-requests/$WR/approvals" $P)" "409"
echo '{"approver_id":"U-001","decision":"APPROVE","checklist":{"WORK_PERMIT":true,"RISK_ASSESSMENT":true,"LOTO_GAS_ISOLATION":true,"GAS_DETECTOR_CHECK":true}}' > $P
chk "요청자 자가승인 차단" "$(req POST "$B/work-requests/$WR/approvals" $P)" "409"
echo '{"approver_id":"U-002","decision":"APPROVE","checklist":{"WORK_PERMIT":true,"RISK_ASSESSMENT":true,"LOTO_GAS_ISOLATION":true,"GAS_DETECTOR_CHECK":true},"comment":"작업자 명단 확인 완료. 승인."}' > $P
chk "안전관리자 승인" "$(req POST "$B/work-requests/$WR/approvals" $P)" "201"
chk "승인 후 상태" "$(req GET "$B/work-requests/$WR" >/dev/null; field status)" "APPROVED"
chk "승인건 재실행 차단" "$(req POST "$B/work-requests/$WR/agent-runs")" "409"
chk "작업 완료 처리" "$(req PATCH "$B/work-requests/$WR/complete")" "200"
chk "최종 상태" "$(field status)" "DONE"

echo "== 7. 조회 계열 =="
chk "대시보드 KPI" "$(req GET "$B/dashboard/summary")" "200"
chk "as-is 기준시간" "$("$PY" -c "import json;print(float(json.load(open('$BODY'))['as_is_baseline_hours']))")" "168.0"
chk "법령 검색(한글 질의)" "$(curl -s -o $BODY -w '%{http_code}' -G --data-urlencode 'q=운전정지' "$B/laws/search")" "200"
chk "설비 목록" "$(req GET "$B/equipments")" "200"
chk "부품 호환성" "$(req GET "$B/parts/P-VLV-001/compatibility")" "200"
chk "AI 설정 조회" "$(req GET "$B/tenants/T-001/ai-config")" "200"

echo "== 8. Security & Config Isolation =="
echo '[{"agent_type":"LEGAL","provider":"OPENAI","egress_allowed":false}]' > $P
chk "외부 provider+egress 차단" "$(req PUT "$B/tenants/T-001/ai-config" $P)" "409"
echo '[{"agent_type":"LEGAL","provider":"AX_PLATFORM","model_name":"ax-1","egress_allowed":true}]' > $P
chk "egress 허용 시 통과" "$(req PUT "$B/tenants/T-001/ai-config" $P)" "200"

echo "== 9. 404 경로 =="
chk "없는 작업요청" "$(req GET "$B/work-requests/WR-NOPE")" "404"
chk "없는 실행" "$(req GET "$B/agent-runs/RUN-9999")" "404"
chk "없는 문서" "$(req GET "$B/documents/DOC-9999")" "404"

echo "== 10. 문서 =="
chk "Swagger UI" "$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:${PORT}/docs")" "200"
chk "OpenAPI 스키마" "$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:${PORT}/openapi.json")" "200"

echo
echo "라이브 E2E: 통과 ${PASS} / 실패 ${FAIL}"
exit "$FAIL"
