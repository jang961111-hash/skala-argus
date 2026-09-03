#!/usr/bin/env bash
# 라이브 E2E 검증 v3.0 — docs/CONTRACT.md v3.0(팀 「API 명세서 v1.0」 REQ-F-0001) 기준.
# scripts/e2e_live.sh(v1.0)는 그대로 보존한다 — 체크리스트 409/VENDOR 4단계/`/complete`/접두어 ID/{detail} 오류
# 등 v3.0에서 전부 사라진 것들을 검증하고 있어 그 자체로는 무효지만, v1.0 증빙으로 남긴다.
#
# BE(backend/services/) 가 아직 이 계약대로 구현 중이라 지금은 문법 검증(bash -n)만 통과한다.
# 실측은 BE 완료 후 돌린다. 이 스크립트가 실패하면 "BE 구현이 계약과 다르다"는 뜻 — 문서를 실측에
# 맞추지 말고 계약(docs/CONTRACT.md)이 맞는지부터 확인할 것.
#
# 사용법:  bash scripts/e2e_live_v3.sh      (backend/.venv 필요, Python 3.10+)
# 종료코드: 실패 건수 (0 이면 전부 통과)
#
# 포트 8000·5173·5199·8810 은 다른 세션이 쓰고 있으므로 건드리지 않는다. 8820 이상만 쓴다.

set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8820}"
B="http://localhost:${PORT}/api/v1"
PY="$ROOT/backend/.venv/bin/python"
[ -x "$PY" ] || { echo "backend/.venv 가 없다. README 의 빠른 시작을 먼저 실행하라 (Python 3.10+)"; exit 99; }

DB_FILE="$ROOT/backend/e2e_v3.db"
cd "$ROOT/backend"
[ -f .env ] || cp .env.example .env
rm -f "$DB_FILE"

# 포트가 실제로 빌 때까지 기다린다 (사고 로그 I-06 재발 방지).
# 이전 실행의 서버가 남아 있으면 아래 준비 대기 루프가 "그 서버"의 응답을 보고
# 통과해 버리고, DB 는 방금 지워진 상태라 대량 실패가 난다. 연속 실행에서 재현됨.
for _ in $(seq 1 30); do
  _pids=$(lsof -ti:"$PORT" 2>/dev/null || true)
  [ -z "$_pids" ] && break
  echo "$_pids" | xargs kill -9 2>/dev/null || true
  sleep 0.4
done
if lsof -ti:"$PORT" >/dev/null 2>&1; then
  echo "포트 $PORT 를 비우지 못했다 — 다른 프로세스가 점유 중이다." >&2
  exit 98
fi

DATABASE_URL="sqlite:///./e2e_v3.db" "$PY" -m uvicorn app.main:app --port "$PORT" > /tmp/rf_e2e_v3_uvicorn.log 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null; rm -f "$DB_FILE"' EXIT

for _ in $(seq 1 40); do
  kill -0 "$SRV" 2>/dev/null || { echo "서버가 기동 직후 죽었다. /tmp/rf_e2e_v3_uvicorn.log 확인" >&2; exit 97; }
  code=$(curl -s -o /dev/null -w '%{http_code}' "$B/auth/me" 2>/dev/null)
  [ -n "$code" ] && [ "$code" != "000" ] && break
  sleep 0.5
done

PASS=0; FAIL=0
BODY=/tmp/rf_e2e_v3_body.json
P=/tmp/rf_e2e_v3_payload.json

# 단순 값 비교 (성공 응답 등)
chk(){ if [ "$2" = "$3" ]; then printf '  PASS  %-46s %s\n' "$1" "$2"; PASS=$((PASS+1));
       else printf '  FAIL  %-46s 기대 %s, 실제 %s\n' "$1" "$3" "$2"; FAIL=$((FAIL+1)); fi; }

# payload 는 파일로 넘긴다 — 중첩 따옴표 이스케이프 오탐 방지 (scripts/e2e_live.sh 계승)
req(){ local m=$1 u=$2 f=${3:-} tok=${4:-}
       # macOS 기본 bash 3.2 는 set -u 에서 빈 배열 "${arr[@]}" 를 unbound 로 본다.
       # ${arr[@]+"${arr[@]}"} 는 3.2·4.x·5.x 전부에서 안전하다.
       local authhdr=()
       [ -n "$tok" ] && authhdr=(-H "Authorization: Bearer $tok")
       if [ -n "$f" ]; then curl -s -o "$BODY" -w '%{http_code}' -X "$m" "$u" -H 'Content-Type: application/json' ${authhdr[@]+"${authhdr[@]}"} --data-binary "@$f"
       else curl -s -o "$BODY" -w '%{http_code}' -X "$m" "$u" ${authhdr[@]+"${authhdr[@]}"}; fi; }
field(){ "$PY" -c "import json;d=json.load(open('$BODY'));print(d.get('$1',''))" 2>/dev/null; }
errcode(){ "$PY" -c "import json;d=json.load(open('$BODY'));print(d.get('code',''))" 2>/dev/null; }
# CONTRACT §1.1/§6 — 단일 오류 포맷 {code, message, fieldErrors?}. detail 키가 나오면 v1.0 잔재 → 실패.
errformat(){ "$PY" -c "
import json
d = json.load(open('$BODY'))
print('OK' if (isinstance(d, dict) and 'code' in d and 'message' in d and 'detail' not in d) else 'FAIL')
" 2>/dev/null; }

# 오류 응답 전용 체크 — status/code/포맷 3가지를 한 번에 본다 (§13 "위 모든 오류 응답이 {code,message} 형태인지")
chkerr(){ local name=$1 actstatus=$2 expstatus=$3 expcode=$4
          local actcode; actcode=$(errcode)
          local fmt; fmt=$(errformat)
          if [ "$actstatus" = "$expstatus" ] && [ "$actcode" = "$expcode" ] && [ "$fmt" = "OK" ]; then
            printf '  PASS  %-46s %s %s (fmt=%s)\n' "$name" "$actstatus" "$actcode" "$fmt"; PASS=$((PASS+1))
          else
            printf '  FAIL  %-46s 기대 %s/%s, 실제 %s/%s (fmt=%s)\n' "$name" "$expstatus" "$expcode" "$actstatus" "$actcode" "$fmt"; FAIL=$((FAIL+1))
          fi; }

ENG_EMAIL="engineer-e2e@argus.test"
ENG2_EMAIL="engineer2-e2e@argus.test"
SAFETY_EMAIL="safety-e2e@argus.test"

echo "== 1. 인증 (CONTRACT §4 #1~#3) =="
cat > "$P" <<J
{"name":"김민준","email":"$ENG_EMAIL","password":"Passw0rd!","passwordConfirm":"Passw0rd!","role":"ENGINEER"}
J
chk "signup 엔지니어" "$(req POST "$B/auth/signup" "$P")" "201"                                    # CONTRACT §4-1
ENG_ID=$(field id)

chkerr "signup 중복 이메일" "$(req POST "$B/auth/signup" "$P")" "409" "EMAIL_ALREADY_EXISTS"        # CONTRACT §4-1

cat > "$P" <<J
{"name":"김민준","email":"eng-mismatch-e2e@argus.test","password":"Passw0rd!","passwordConfirm":"Different1!","role":"ENGINEER"}
J
chkerr "signup 비밀번호 불일치" "$(req POST "$B/auth/signup" "$P")" "400" "PASSWORD_MISMATCH"        # CONTRACT §4-1

cat > "$P" <<J
{"email":"$ENG_EMAIL","password":"Passw0rd!"}
J
chk "login 엔지니어" "$(req POST "$B/auth/login" "$P")" "200"                                       # CONTRACT §4-2
TOKEN_ENG=$(field accessToken)
chk "login role" "$(field role)" "ENGINEER"
chk "login redirectPath" "$(field redirectPath)" "/home"                                            # CONTRACT §4-2 "redirectPath 는 서버가 내려준다"

cat > "$P" <<J
{"email":"$ENG_EMAIL","password":"WrongPass1!"}
J
chkerr "login 잘못된 비밀번호" "$(req POST "$B/auth/login" "$P")" "401" "INVALID_CREDENTIALS"        # CONTRACT §4-2

chk "auth/me (토큰 있음)" "$(req GET "$B/auth/me" '' "$TOKEN_ENG")" "200"                            # CONTRACT §4-3
chkerr "auth/me (토큰 없음)" "$(req GET "$B/auth/me")" "401" "TOKEN_INVALID"                         # CONTRACT §1 "전 API 필수"

cat > "$P" <<J
{"name":"이정호","email":"$SAFETY_EMAIL","password":"Passw0rd!","passwordConfirm":"Passw0rd!","role":"SAFETY_MANAGER"}
J
chk "signup 안전관리자" "$(req POST "$B/auth/signup" "$P")" "201"

cat > "$P" <<J
{"email":"$SAFETY_EMAIL","password":"Passw0rd!"}
J
chk "login 안전관리자" "$(req POST "$B/auth/login" "$P")" "200"
TOKEN_SAFETY=$(field accessToken)
chk "login redirectPath (안전관리자)" "$(field redirectPath)" "/manage/requests"                     # CONTRACT §4-2

echo "== 2. DRAFT 생성·이어쓰기 (CONTRACT §3 상태 전이표) =="
cat > "$P" <<J
{"draft":true,"productName":"SS-8-VCR"}
J
chk "draft 생성" "$(req POST "$B/work-requests" "$P" "$TOKEN_ENG")" "201"                            # CONTRACT §4-5
WR_ID=$(field id)
chk "draft 상태" "$(field status)" "DRAFT"
_cv1=$("$PY" -c "
import re,json
d=json.load(open('$BODY'))
print('OK' if re.fullmatch(r'WR-\d{8}-\d{3}', d.get('requestNo','')) else 'FAIL:'+d.get('requestNo',''))
")
chk "draft requestNo 형식(WR-YYYYMMDD-NNN)" "$_cv1" "OK"
_cv2=$("$PY" -c "
import re,json
d=json.load(open('$BODY'))
u=r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'
print('OK' if re.fullmatch(u, d.get('id',''), re.I) else 'FAIL:'+d.get('id',''))
")
chk "draft id 는 UUID" "$_cv2" "OK"

echo "== 미완성 상태로 실행 시도 → 400 (CONTRACT §4-11) =="
cat > "$P" <<J
{"workRequestId":"$WR_ID"}
J
chkerr "미완성 draft 로 agent-runs 시도" "$(req POST "$B/agent-runs" "$P" "$TOKEN_ENG")" "400" "WORK_REQUEST_INCOMPLETE"

cat > "$P" <<J
{"equipment":"가스캐비닛#2","line":"A라인","substance":"SiH4",
 "operatingCondition":{"temperature":"상온","pressure":"3000 psi"},
 "productType":"VALVE","specJson":{"pressureRating":"3000 psi"},
 "symptom":"가스 유량 이상, 밸브 누설 의심","siteMemo":"현장 확인 결과 밸브 시트 마모"}
J
chk "PATCH 로 이어쓰기" "$(req PATCH "$B/work-requests/$WR_ID" "$P" "$TOKEN_ENG")" "200"              # CONTRACT §4-8

echo "== 3. 정식 생성 검증 (CONTRACT §4-5, 별도 요청으로 음성 경로만 확인) =="
cat > "$P" <<J
{"draft":false,"productName":"REG-2S"}
J
chkerr "필수값 누락" "$(req POST "$B/work-requests" "$P" "$TOKEN_ENG")" "400" "VALIDATION_FAILED"

cat > "$P" <<J
{"draft":false,"equipment":"가스캐비닛#2","line":"A라인","substance":"SiH4",
 "operatingCondition":{"temperature":"상온","pressure":"3000 psi"},
 "productName":"SS-8-VCR","productType":"VALVE","specJson":{"wrongKey":"3000 psi"},
 "symptom":"가스 유량 이상"}
J
chkerr "specJson 키 불일치(productType=VALVE→pressureRating 필요)" "$(req POST "$B/work-requests" "$P" "$TOKEN_ENG")" "400" "SPEC_SCHEMA_MISMATCH"

echo "== 4. 에이전트 실행·폴링 (CONTRACT §4-11, §4-12) =="
cat > "$P" <<J
{"workRequestId":"$WR_ID"}
J
chk "agent-runs 시작" "$(req POST "$B/agent-runs" "$P" "$TOKEN_ENG")" "202"
RUN_ID=$(field runId)
chk "실행 직후 status" "$(field status)" "RUNNING"

chkerr "중복 실행 차단" "$(req POST "$B/agent-runs" "$P" "$TOKEN_ENG")" "409" "RUN_ALREADY_IN_PROGRESS"

for i in 1 2 3; do
  req GET "$B/agent-runs/$RUN_ID" '' "$TOKEN_ENG" >/dev/null
  DONE_N=$("$PY" -c "
import json
d=json.load(open('$BODY'))
print(len([s for s in d['steps'] if s['status']=='DONE']))
")
  chk "폴링 ${i}회 — DONE step 수(누적)" "$DONE_N" "$i"
  chk "폴링 ${i}회 — pollIntervalMs 존재" "$(field pollIntervalMs)" "2500"
done
chk "3회째 allDone" "$(field allDone)" "True"                                                        # python bool → 'True' 문자열

chk "3회째 이후 작업요청 status=AI_DONE" "$(req GET "$B/work-requests/$WR_ID" '' "$TOKEN_ENG" >/dev/null; field status)" "AI_DONE"

echo "== 5. 결과 편집 — 전체 치환 (CONTRACT §4-13) =="
req GET "$B/work-requests/$WR_ID" '' "$TOKEN_ENG" >/dev/null
RESULT_A1_ID=$("$PY" -c "
import json
d=json.load(open('$BODY'))
r=[x for x in d['agentRun']['results'] if x['agentCode']=='A1'][0]
print(r['id'])
")
cat > "$P" <<J
{"items":[{"text":"대체 호환: SS-8-VCR-2","edited":true}]}
J
chk "agent-results PATCH (전체 치환)" "$(req PATCH "$B/agent-results/$RESULT_A1_ID" "$P" "$TOKEN_ENG")" "200"
chk "edited=true 로 전환" "$(field edited)" "True"
_cv3=$("$PY" -c "
import json
d=json.load(open('$BODY'))
print(len(d['payloadJson']['items']))
")
chk "기존 항목 삭제 + 신규 추가 반영(items 1개)" "$_cv3" "1"
_cv4=$("$PY" -c "
import json
d=json.load(open('$BODY'))
print('OK' if d['payloadJson']['items'][0].get('itemId') else 'FAIL')
")
chk "itemId 없이 보낸 신규 항목은 서버가 채번" "$_cv4" "OK"

echo "== 6. 제출 (CONTRACT §4-14) =="
chkerr "engineerNote 없이 제출" "$(req PATCH "$B/work-requests/$WR_ID/submit-approval" '' "$TOKEN_ENG")" "422" "SUBMIT_REQUIRED_FIELD_MISSING"

cat > "$P" <<J
{"engineerNote":"압력 등급 상향 반영, 제38조 작업허가 필요 판단."}
J
chk "engineerNote 채우기" "$(req PATCH "$B/work-requests/$WR_ID" "$P" "$TOKEN_ENG")" "200"
chk "engineerNote 채운 뒤 제출" "$(req PATCH "$B/work-requests/$WR_ID/submit-approval" '' "$TOKEN_ENG")" "200"
chk "제출 후 status=PENDING" "$(field status)" "PENDING"

echo "== 7. 권한 (CONTRACT §1 '권한' 행, §4-7) =="
cat > "$P" <<J
{"workRequestId":"$WR_ID","decision":"APPROVE"}
J
chkerr "엔지니어가 승인 시도" "$(req POST "$B/approvals" "$P" "$TOKEN_ENG")" "403" "FORBIDDEN_ROLE"

cat > "$P" <<J
{"name":"박수진","email":"$ENG2_EMAIL","password":"Passw0rd!","passwordConfirm":"Passw0rd!","role":"ENGINEER"}
J
req POST "$B/auth/signup" "$P" >/dev/null
cat > "$P" <<J
{"email":"$ENG2_EMAIL","password":"Passw0rd!"}
J
req POST "$B/auth/login" "$P" >/dev/null
TOKEN_ENG2=$(field accessToken)
chkerr "타인 요청 조회(엔지니어2 → 엔지니어1 소유)" "$(req GET "$B/work-requests/$WR_ID" '' "$TOKEN_ENG2")" "403" "FORBIDDEN_NOT_OWNER"

echo "== 8. 승인/거절 (CONTRACT §4-15) =="
cat > "$P" <<J
{"workRequestId":"$WR_ID","decision":"REJECT","reason":"짧음"}
J
chkerr "거절 사유 없음/과짧음" "$(req POST "$B/approvals" "$P" "$TOKEN_SAFETY")" "400" "REJECT_REASON_REQUIRED"

cat > "$P" <<J
{"workRequestId":"$WR_ID","decision":"REJECT","reason":"9자짜리사유임요"}
J
chkerr "거절 사유 9자(10자 미만) — CONTRACT §4-15 '10자 이상'" "$(req POST "$B/approvals" "$P" "$TOKEN_SAFETY")" "400" "REJECT_REASON_REQUIRED"

cat > "$P" <<J
{"workRequestId":"$WR_ID","decision":"REJECT","reason":"규격 부적합: 유독가스 라인에 호환품 사용 불가"}
J
chk "정상 거절(사유 10자 이상)" "$(req POST "$B/approvals" "$P" "$TOKEN_SAFETY")" "201"
chk "거절 후 status=REJECTED" "$(req GET "$B/work-requests/$WR_ID" '' "$TOKEN_ENG" >/dev/null; field status)" "REJECTED"

chk "재제출(REJECTED→PENDING, 직전 approval 이력 보존)" "$(req PATCH "$B/work-requests/$WR_ID/submit-approval" '' "$TOKEN_ENG")" "200"
chk "재제출 후 status=PENDING" "$(field status)" "PENDING"

cat > "$P" <<J
{"workRequestId":"$WR_ID","decision":"APPROVE"}
J
chk "정상 승인(사유 선택)" "$(req POST "$B/approvals" "$P" "$TOKEN_SAFETY")" "201"
chk "승인 후 status=APPROVED" "$(req GET "$B/work-requests/$WR_ID" '' "$TOKEN_ENG" >/dev/null; field status)" "APPROVED"

# CONTRACT §6: 중복 승인은 409(ALREADY_DECIDED 또는 NOT_PENDING — 둘 중 BE 체크 순서에 따라 달라짐, 원문에 우선순위 명시 없음)
DUP_STATUS=$(req POST "$B/approvals" "$P" "$TOKEN_SAFETY")
DUP_CODE=$(errcode)
chk "중복 승인 차단(409)" "$DUP_STATUS" "409"
chk "중복 승인 오류코드가 ALREADY_DECIDED 또는 NOT_PENDING" "$("$PY" -c "print('OK' if '$DUP_CODE' in ('ALREADY_DECIDED','NOT_PENDING') else 'FAIL:$DUP_CODE')")" "OK"

echo "== 9. 불변 상태 (CONTRACT §3 마지막 행) =="
cat > "$P" <<J
{"engineerNote":"수정 시도"}
J
chkerr "APPROVED 상태에서 work-requests PATCH" "$(req PATCH "$B/work-requests/$WR_ID" "$P" "$TOKEN_ENG")" "409" "IMMUTABLE_STATUS"

cat > "$P" <<J
{"items":[{"text":"수정 시도","edited":true}]}
J
chkerr "APPROVED 상태에서 agent-results PATCH" "$(req PATCH "$B/agent-results/$RESULT_A1_ID" "$P" "$TOKEN_ENG")" "409" "RESULT_LOCKED"

echo "== 10. 대시보드 (CONTRACT §4-4) =="
chk "role=engineer" "$(req GET "$B/dashboard/summary?role=engineer" '' "$TOKEN_ENG")" "200"
_cv5=$("$PY" -c "
import json
d=json.load(open('$BODY'))
print('OK' if set(d.keys())=={'draft','aiRunning','pending','rejected'} else 'FAIL:'+str(sorted(d.keys())))
")
chk "engineer 대시보드에 평균승인시간 없음" "$_cv5" "OK"

chk "role=safety" "$(req GET "$B/dashboard/summary?role=safety" '' "$TOKEN_SAFETY")" "200"
_cv6=$("$PY" -c "
import json
d=json.load(open('$BODY'))
print('OK' if 'rejectReasonsTop' in d else 'FAIL')
")
chk "safety 대시보드에 rejectReasonsTop 존재" "$_cv6" "OK"

chkerr "role 불일치(엔지니어 토큰으로 safety 조회)" "$(req GET "$B/dashboard/summary?role=safety" '' "$TOKEN_ENG")" "403" "FORBIDDEN_ROLE"

echo "== 11. 목록 (CONTRACT §4-6) =="
chk "mine=true" "$(req GET "$B/work-requests?mine=true" '' "$TOKEN_ENG")" "200"
chk "status 콤마 다중 지정(REJECTED,DRAFT)" "$(req GET "$B/work-requests?status=REJECTED,DRAFT" '' "$TOKEN_ENG")" "200"
_cv7=$("$PY" -c "
import json
d=json.load(open('$BODY'))
print(d['page']['number'])
")
chk "page.number 0-base" "$_cv7" "0"
_cv8=$("$PY" -c "
import json
d=json.load(open('$BODY'))
print('OK' if (not d['content']) or 'nextAction' in d['content'][0] else 'FAIL')
")
chk "목록 항목에 nextAction 존재" "$_cv8" "OK"

echo "== 12. 404 =="
chkerr "없는 workRequest" "$(req GET "$B/work-requests/00000000-0000-4000-8000-000000000000" '' "$TOKEN_ENG")" "404" "WORK_REQUEST_NOT_FOUND"
chkerr "없는 run" "$(req GET "$B/agent-runs/00000000-0000-4000-8000-000000000000" '' "$TOKEN_ENG")" "404" "AGENT_RUN_NOT_FOUND"

echo "== 13. 오류 포맷 =="
echo "  (chkerr 가 매 오류 응답마다 errformat() 으로 {code,message} 형태 + detail 키 부재를 함께 검증했다 — CONTRACT §1.1/§6)"

echo "== 14. 사진 업로드 (CONTRACT §4-9, backend/app/services/photo_service.py) =="
# 제한값은 photo_service.py 실측: 파일당 10MB(413 FILE_TOO_LARGE), 요청당 5장(409 PHOTO_LIMIT_EXCEEDED),
# 형식은 jpg/png/webp 만(그 외 400 UNSUPPORTED_FILE_TYPE). 파트명 files(배열).
PHOTO_DIR=/tmp/rf_e2e_v3_photos
mkdir -p "$PHOTO_DIR"
"$PY" -c "
from PIL import Image
Image.new('RGB', (10, 10), color='red').save('$PHOTO_DIR/valid.jpg', 'JPEG')
"
dd if=/dev/zero of="$PHOTO_DIR/toolarge.jpg" bs=1m count=11 >/dev/null 2>&1
echo "이미지 아님" > "$PHOTO_DIR/wrong.txt"

# method url token file1 [file2...] — 매번 image/jpeg 로 명시(curl 의 확장자 추정에 기대지 않는다)
photoreq(){ local m=$1 u=$2 tok=$3; shift 3
  local parts=(); for f in "$@"; do parts+=(-F "files=@$f;type=image/jpeg"); done
  curl -s -o "$BODY" -w '%{http_code}' -X "$m" "$u" -H "Authorization: Bearer $tok" "${parts[@]}"; }

chk "사진 업로드 1장 → 201" "$(photoreq POST "$B/work-requests/$WR_ID/photos" "$TOKEN_ENG" "$PHOTO_DIR/valid.jpg")" "201"
_cv9=$("$PY" -c "
import json
p=json.load(open('$BODY'))[0]
print('OK' if p.get('originalUrl') and p.get('thumbnailUrl') else 'FAIL')
")
chk "응답에 originalUrl/thumbnailUrl 존재" "$_cv9" "OK"

chk "사진 목록 조회 → 200" "$(req GET "$B/work-requests/$WR_ID/photos" '' "$TOKEN_ENG")" "200"
_cv10=$("$PY" -c "
import json
d=json.load(open('$BODY'))
print('OK' if len(d) >= 1 else 'FAIL:'+str(len(d)))
")
chk "방금 업로드한 사진이 목록에 있음" "$_cv10" "OK"

chkerr "허용 외 형식(.txt)" "$(curl -s -o "$BODY" -w '%{http_code}' -X POST "$B/work-requests/$WR_ID/photos" -H "Authorization: Bearer $TOKEN_ENG" -F "files=@$PHOTO_DIR/wrong.txt;type=text/plain")" "400" "UNSUPPORTED_FILE_TYPE"

chkerr "10MB 초과" "$(curl -s -o "$BODY" -w '%{http_code}' -X POST "$B/work-requests/$WR_ID/photos" -H "Authorization: Bearer $TOKEN_ENG" -F "files=@$PHOTO_DIR/toolarge.jpg;type=image/jpeg")" "413" "FILE_TOO_LARGE"

chk "사진 4장 추가(누적 5장) → 201" "$(photoreq POST "$B/work-requests/$WR_ID/photos" "$TOKEN_ENG" "$PHOTO_DIR/valid.jpg" "$PHOTO_DIR/valid.jpg" "$PHOTO_DIR/valid.jpg" "$PHOTO_DIR/valid.jpg")" "201"
chkerr "6번째 사진 → 초과 차단" "$(photoreq POST "$B/work-requests/$WR_ID/photos" "$TOKEN_ENG" "$PHOTO_DIR/valid.jpg")" "409" "PHOTO_LIMIT_EXCEEDED"

# 이 스크립트가 만든 것만 정리 — WR_ID 는 이번 실행에서 새로 발급된 UUID 라 다른 세션의 업로드와 겹치지 않는다
rm -rf "$PHOTO_DIR"
[ -n "${WR_ID:-}" ] && rm -rf "$ROOT/backend/uploads/$WR_ID"

echo
echo "라이브 E2E v3.0: 통과 ${PASS} / 실패 ${FAIL}"
exit "$FAIL"
