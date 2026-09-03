"""v3.0 전체 흐름 (docs/CONTRACT.md §3 상태 전이, §4 API 15개).

DRAFT → PATCH → POST /agent-runs → 폴링 3회(A1→A2→A3) → AI_DONE → 결과 편집
→ submit-approval → PENDING → POST /approvals → APPROVED.
"""
import re

from PIL import Image

from tests.conftest import (
    UPLOADS_DIR,
    VALVE_FIELDS,
    create_ready_request,
    jpeg_bytes,
    run_agents_to_done,
)
from tests.test_auth import assert_error

WR = "/api/v1/work-requests"
RUNS = "/api/v1/agent-runs"
RESULTS = "/api/v1/agent-results"
APPROVALS = "/api/v1/approvals"

REQUEST_NO_RE = re.compile(r"^WR-\d{8}-\d{3}$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
KST_SUFFIX = "+09:00"


# ---------------------------------------------------------------- 전체 흐름
def test_full_flow(client, engineer, safety):
    # 1. 임시저장 — 업무 필드 검증을 건너뛴다
    r = client.post(WR, json={"draft": True, "symptom": "밸브 미세 누설 의심"}, headers=engineer)
    assert r.status_code == 201, r.text
    wr = r.json()
    wr_id = wr["workRequestId"]
    assert UUID_RE.match(wr_id), wr_id
    assert REQUEST_NO_RE.match(wr["requestNo"]), wr["requestNo"]
    assert wr["status"] == "DRAFT" and wr["nextAction"] == "CONTINUE"
    assert wr["id"] == wr_id  # FE 는 `id`, 계약 §1 예시는 `workRequestId` — 둘 다 낸다
    assert wr["createdAt"].endswith(KST_SUFFIX)
    assert wr["requesterName"] == "김민준" and wr["submittedAt"] is None

    # DRAFT 는 아직 필수값이 없어 AI 를 돌릴 수 없다
    body = assert_error(
        client.post(RUNS, json={"workRequestId": wr_id}, headers=engineer),
        400, "WORK_REQUEST_INCOMPLETE", has_field_errors=True,
    )
    assert {"equipment", "productType", "specJson"} <= {f["field"] for f in body["fieldErrors"]}

    # 2. 이어쓰기 — 보낸 필드만 반영된다
    r = client.patch(WR + f"/{wr_id}", json={k: v for k, v in VALVE_FIELDS.items() if k != "symptom"}, headers=engineer)
    assert r.status_code == 200, r.text
    patched = r.json()
    assert patched["symptom"] == "밸브 미세 누설 의심"  # 안 보낸 필드는 그대로
    assert patched["equipment"] == "가스캐비닛#2" and patched["specJson"] == {"pressureRating": "3000 psi"}
    assert patched["operatingCondition"] == {"temperature": "상온", "pressure": "3000 psi"}
    assert patched["status"] == "DRAFT"

    # 3. AI 실행 — body 는 workRequestId 하나뿐, 202
    r = client.post(RUNS, json={"workRequestId": wr_id}, headers=engineer)
    assert r.status_code == 202, r.text
    run = r.json()
    run_id = run["runId"]
    assert run["status"] == "RUNNING" and run["allDone"] is False
    assert run["pollIntervalMs"] == 2500
    assert [s["agentCode"] for s in run["steps"]] == ["A1", "A2", "A3"]
    assert all(s["status"] == "WAITING" for s in run["steps"])
    assert client.get(WR + f"/{wr_id}", headers=engineer).json()["status"] == "AI_RUNNING"

    # 진행 중 재실행 → 409
    assert_error(client.post(RUNS, json={"workRequestId": wr_id}, headers=engineer), 409, "RUN_ALREADY_IN_PROGRESS")

    # 4. 폴링 — 호출마다 A1 → A2 → A3 순으로 하나씩 DONE
    for i, code in enumerate(["A1", "A2", "A3"], start=1):
        r = client.get(RUNS + f"/{run_id}", headers=engineer)
        assert r.status_code == 200, r.text
        run = r.json()
        done = [s["agentCode"] for s in run["steps"] if s["status"] == "DONE"]
        assert done == ["A1", "A2", "A3"][:i], (i, done)
        assert run["allDone"] is (i == 3)
        assert run["status"] == ("DONE" if i == 3 else "RUNNING")
        assert next(s for s in run["steps"] if s["agentCode"] == code)["message"]

    # allDone 이면 서버가 AI_DONE 으로 전환한다
    detail = client.get(WR + f"/{wr_id}", headers=engineer).json()
    assert detail["status"] == "AI_DONE" and detail["nextAction"] == "RESULT"
    assert detail["agentRun"]["runId"] == run_id and detail["agentRun"]["id"] == run_id
    assert detail["approval"] is None and detail["photos"] == []

    results = {r["agentCode"]: r for r in detail["agentRun"]["results"]}
    assert set(results) == {"A1", "A2", "A3"}
    assert all(r["editable"] is True and r["edited"] is False for r in results.values())
    # 통일 구조: A1·A2 는 items, A3 는 documents
    for code in ("A1", "A2"):
        items = results[code]["payloadJson"]["items"]
        assert items and {"itemId", "text", "edited"} <= set(items[0])
    documents = results["A3"]["payloadJson"]["documents"]
    assert documents and {"docId", "type", "name", "content", "edited"} <= set(documents[0])
    assert [d["type"] for d in documents] == ["WORK_PERMIT", "RISK_ASSESSMENT"]

    # 5. engineerNote 없이 제출 → 422
    body = assert_error(
        client.patch(WR + f"/{wr_id}/submit-approval", headers=engineer),
        422, "SUBMIT_REQUIRED_FIELD_MISSING", has_field_errors=True,
    )
    assert "engineerNote" in {f["field"] for f in body["fieldErrors"]}

    client.patch(WR + f"/{wr_id}", json={"engineerNote": "제92조 운전정지·LOTO 적용이 필요합니다"}, headers=engineer)
    r = client.patch(WR + f"/{wr_id}/submit-approval", headers=engineer)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "PENDING" and r.json()["submittedAt"].endswith(KST_SUFFIX)

    # PENDING 이면 수정도 결과 편집도 잠긴다
    assert_error(client.patch(WR + f"/{wr_id}", json={"symptom": "x"}, headers=engineer), 409, "IMMUTABLE_STATUS")
    assert_error(
        client.patch(RESULTS + f"/{results['A1']['agentResultId']}", json={"items": []}, headers=engineer),
        409, "RESULT_LOCKED",
    )

    # 6. 승인 — 안전관리자만
    assert_error(
        client.post(APPROVALS, json={"workRequestId": wr_id, "decision": "APPROVE"}, headers=engineer),
        403, "FORBIDDEN_ROLE",
    )
    r = client.post(APPROVALS, json={"workRequestId": wr_id, "decision": "APPROVE"}, headers=safety)
    assert r.status_code == 201, r.text
    approval = r.json()
    assert approval["decision"] == "APPROVE" and approval["approverName"] == "이정호"
    assert approval["reason"] is None and approval["decidedAt"].endswith(KST_SUFFIX)
    assert "checklist" not in approval

    detail = client.get(WR + f"/{wr_id}", headers=safety).json()
    assert detail["status"] == "APPROVED" and detail["nextAction"] == "DETAIL"
    assert detail["approval"]["approvalId"] == approval["approvalId"]
    # 안전관리자 조회면 결과는 언제나 읽기 전용
    assert all(r["editable"] is False for r in detail["agentRun"]["results"])

    # 이미 결정된 요청 → 409
    assert_error(
        client.post(APPROVALS, json={"workRequestId": wr_id, "decision": "APPROVE"}, headers=safety),
        409, "ALREADY_DECIDED",
    )


# ------------------------------------------------------------ 결과 편집(치환)
def test_agent_result_full_replacement(client, engineer):
    wr_id = create_ready_request(client, engineer)
    detail = client.get(WR + f"/{wr_id}", headers=engineer).json()
    a2 = next(r for r in detail["agentRun"]["results"] if r["agentCode"] == "A2")
    items = a2["payloadJson"]["items"]
    assert len(items) >= 3

    # 1건 유지 · 1건 수정 · 1건 신규(itemId 없음) · 나머지는 배열에서 빠지므로 삭제
    r = client.patch(
        RESULTS + f"/{a2['agentResultId']}",
        json={
            "items": [
                {"itemId": items[0]["itemId"], "text": items[0]["text"]},
                {"itemId": items[1]["itemId"], "text": "엔지니어가 고친 조문"},
                {"text": "엔지니어가 새로 넣은 근거"},
            ]
        },
        headers=engineer,
    )
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["edited"] is True and updated["editable"] is True
    new_items = updated["payloadJson"]["items"]
    assert len(new_items) == 3  # 배열에 없던 항목은 삭제됐다
    assert new_items[0]["itemId"] == items[0]["itemId"] and new_items[0]["edited"] is False
    assert new_items[1]["text"] == "엔지니어가 고친 조문" and new_items[1]["edited"] is True
    assert new_items[2]["itemId"] and new_items[2]["itemId"] not in {i["itemId"] for i in items}
    assert new_items[2]["edited"] is True  # 신규 추가는 사람이 손댄 것

    # 상세에도 그대로 반영되고, 손대지 않은 A1 은 edited=false 로 남는다
    detail = client.get(WR + f"/{wr_id}", headers=engineer).json()
    by_code = {r["agentCode"]: r for r in detail["agentRun"]["results"]}
    assert by_code["A2"]["edited"] is True and by_code["A1"]["edited"] is False

    # A3 는 documents 로 보내야 한다
    a3 = by_code["A3"]
    assert_error(
        client.patch(RESULTS + f"/{a3['agentResultId']}", json={"items": [{"text": "x"}]}, headers=engineer),
        400, "VALIDATION_FAILED",
    )
    r = client.patch(
        RESULTS + f"/{a3['agentResultId']}",
        json={"documents": [{"type": "WORK_PERMIT", "name": "손으로 쓴 허가서", "content": "본문"}]},
        headers=engineer,
    )
    assert r.status_code == 200, r.text
    docs = r.json()["payloadJson"]["documents"]
    assert len(docs) == 1 and docs[0]["docId"] and docs[0]["edited"] is True

    assert_error(client.patch(RESULTS + "/no-such-id", json={"items": []}, headers=engineer), 404, "AGENT_RUN_NOT_FOUND")


def test_submit_requires_at_least_one_law(client, engineer):
    """A2 적용 법령이 0건이면 제출할 수 없다 (CONTRACT §4-14 ③)."""
    wr_id = create_ready_request(client, engineer)
    detail = client.get(WR + f"/{wr_id}", headers=engineer).json()
    a2 = next(r for r in detail["agentRun"]["results"] if r["agentCode"] == "A2")
    assert client.patch(RESULTS + f"/{a2['agentResultId']}", json={"items": []}, headers=engineer).status_code == 200

    body = assert_error(
        client.patch(WR + f"/{wr_id}/submit-approval", headers=engineer),
        422, "SUBMIT_REQUIRED_FIELD_MISSING", has_field_errors=True,
    )
    assert any("A2" in f["field"] for f in body["fieldErrors"]), body


# --------------------------------------------------------------- 거절·재제출
def test_reject_then_resubmit_keeps_history(client, engineer, safety):
    wr_id = create_ready_request(client, engineer)
    assert client.patch(WR + f"/{wr_id}/submit-approval", headers=engineer).status_code == 200

    # 사유 없음 / 10자 미만 → 400
    assert_error(
        client.post(APPROVALS, json={"workRequestId": wr_id, "decision": "REJECT"}, headers=safety),
        400, "REJECT_REASON_REQUIRED", has_field_errors=True,
    )
    assert_error(
        client.post(APPROVALS, json={"workRequestId": wr_id, "decision": "REJECT", "reason": "부적합"}, headers=safety),
        400, "REJECT_REASON_REQUIRED",
    )
    assert client.get(WR + f"/{wr_id}", headers=safety).json()["status"] == "PENDING"

    r = client.post(
        APPROVALS,
        json={
            "workRequestId": wr_id,
            "decision": "REJECT",
            "reason": "유독가스 라인이라 호환품 시트 재질로는 사용할 수 없습니다",
            "reasonCategory": "규격 부적합",
        },
        headers=safety,
    )
    assert r.status_code == 201, r.text
    first_approval_id = r.json()["approvalId"]
    assert r.json()["reasonCategory"] == "규격 부적합"

    detail = client.get(WR + f"/{wr_id}", headers=engineer).json()
    assert detail["status"] == "REJECTED" and detail["nextAction"] == "DETAIL"
    assert detail["approval"]["approvalId"] == first_approval_id

    # REJECTED 에서는 다시 수정·편집할 수 있다
    a1 = next(r for r in detail["agentRun"]["results"] if r["agentCode"] == "A1")
    assert a1["editable"] is True
    assert client.patch(WR + f"/{wr_id}", json={"engineerNote": "OEM 동일 규격으로 변경했습니다"}, headers=engineer).status_code == 200

    # 재제출 → PENDING 복귀. 직전 이력은 남아 있다
    assert client.patch(WR + f"/{wr_id}/submit-approval", headers=engineer).json()["status"] == "PENDING"
    r = client.post(APPROVALS, json={"workRequestId": wr_id, "decision": "APPROVE"}, headers=safety)
    assert r.status_code == 201
    second_approval_id = r.json()["approvalId"]
    assert second_approval_id != first_approval_id

    detail = client.get(WR + f"/{wr_id}", headers=safety).json()
    assert detail["status"] == "APPROVED"
    assert detail["approval"]["approvalId"] == second_approval_id  # 화면엔 최신 1건

    # append-only 실측 (CONTRACT §5 설계 원칙 3) — 화면은 최신 1건만 보여주지만
    # 직전 REJECT 행은 갱신되지 않고 그대로 남아 있어야 한다. 상세 응답은 최신 1건만
    # 노출하므로(§4-7) 보존 여부는 테이블을 직접 봐야 확인된다.
    from sqlalchemy import select

    from app.core.enums import ApprovalDecision
    from app.db.session import SessionLocal
    from app.models import Approval

    with SessionLocal() as db:
        rows = list(
            db.scalars(
                select(Approval).where(Approval.work_request_id == wr_id).order_by(Approval.decided_at)
            ).all()
        )
    assert [r.id for r in rows] == [first_approval_id, second_approval_id], "결정 이력이 갱신됐다(append-only 위반)"
    assert rows[0].decision is ApprovalDecision.REJECT and rows[1].decision is ApprovalDecision.APPROVE
    # 거절 사유·분류가 그대로 남아야 S_01 의 거절 사유 TOP5 집계가 성립한다
    assert rows[0].reason.startswith("유독가스 라인이라") and rows[0].reason_category == "규격 부적합"
    assert rows[1].reason is None


def test_approvals_errors(client, engineer, safety):
    wr_id = create_ready_request(client, engineer)  # AI_DONE — 아직 제출 전
    assert_error(
        client.post(APPROVALS, json={"workRequestId": wr_id, "decision": "APPROVE"}, headers=safety),
        409, "NOT_PENDING",
    )
    assert_error(
        client.post(APPROVALS, json={"workRequestId": "no-such-id", "decision": "APPROVE"}, headers=safety),
        404, "WORK_REQUEST_NOT_FOUND",
    )
    assert_error(
        client.post(APPROVALS, json={"workRequestId": wr_id, "decision": "MAYBE"}, headers=safety),
        400, "VALIDATION_FAILED",
    )


# ------------------------------------------------------------------ 권한 분리
def test_role_scoping(client, engineer, safety):
    """ENGINEER 는 본인 것만, SAFETY_MANAGER 는 PENDING 이상만."""
    draft_id = client.post(WR, json={"draft": True, "symptom": "임시"}, headers=engineer).json()["workRequestId"]
    assert_error(client.get(WR + f"/{draft_id}", headers=safety), 403, "FORBIDDEN_NOT_OWNER")

    # 다른 엔지니어는 남의 요청을 볼 수 없다
    other = {
        "name": "박서준", "email": "other.engineer@replaceflow.test",
        "password": "Passw0rd!", "passwordConfirm": "Passw0rd!", "role": "ENGINEER",
    }
    client.post("/api/v1/auth/signup", json=other)
    token = client.post("/api/v1/auth/login", json={"email": other["email"], "password": other["password"]}).json()
    other_headers = {"Authorization": f"Bearer {token['accessToken']}"}
    assert_error(client.get(WR + f"/{draft_id}", headers=other_headers), 403, "FORBIDDEN_NOT_OWNER")
    assert_error(
        client.patch(WR + f"/{draft_id}", json={"symptom": "x"}, headers=other_headers),
        403, "FORBIDDEN_NOT_OWNER",
    )
    assert client.get(WR, headers=other_headers).json()["page"]["totalElements"] == 0

    # 엔지니어는 등록, 안전관리자는 승인 — 서로의 기능은 403
    assert_error(client.post(WR, json={"draft": True}, headers=safety), 403, "FORBIDDEN_ROLE")
    assert_error(
        client.post(RUNS, json={"workRequestId": draft_id}, headers=safety), 403, "FORBIDDEN_ROLE"
    )

    # 안전관리자 목록에는 PENDING 이상만 보인다
    listing = client.get(WR, params={"size": 100}, headers=safety).json()
    assert listing["content"], listing
    assert {i["status"] for i in listing["content"]} <= {"PENDING", "APPROVED", "REJECTED"}


# --------------------------------------------------------------------- 목록
def test_list_paging_sort_filter(client, engineer, safety):
    r = client.get(WR, params={"page": 0, "size": 2}, headers=engineer)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"content", "page"}
    assert set(body["page"]) == {"number", "size", "totalElements", "totalPages"}
    assert body["page"]["number"] == 0 and body["page"]["size"] == 2
    assert len(body["content"]) == 2
    assert body["page"]["totalPages"] == -(-body["page"]["totalElements"] // 2)

    # status 콤마 다중 지정
    r = client.get(WR, params={"status": "REJECTED,DRAFT", "size": 100}, headers=engineer)
    assert r.status_code == 200
    assert {i["status"] for i in r.json()["content"]} <= {"REJECTED", "DRAFT"}
    assert r.json()["page"]["totalElements"] >= 2

    # nextAction 은 상태에서 서버가 계산한다
    expected = {"DRAFT": "CONTINUE", "AI_RUNNING": "RUN", "AI_DONE": "RESULT"}
    for row in client.get(WR, params={"size": 100}, headers=engineer).json()["content"]:
        assert row["nextAction"] == expected.get(row["status"], "DETAIL"), row

    # 정렬
    rows = client.get(WR, params={"sort": "requestNo,asc", "size": 100}, headers=engineer).json()["content"]
    assert [r["requestNo"] for r in rows] == sorted(r["requestNo"] for r in rows)

    # mine — 안전관리자는 본인이 등록한 것이 없다
    assert client.get(WR, params={"mine": "true"}, headers=safety).json()["page"]["totalElements"] == 0

    # 빈 결과도 200 + content: []
    empty = client.get(WR, params={"status": "DRAFT", "mine": "true"}, headers=safety)
    assert empty.status_code == 200 and empty.json()["content"] == []

    assert_error(client.get(WR, params={"status": "BOGUS"}, headers=engineer), 400, "VALIDATION_FAILED")
    assert_error(client.get(WR, params={"sort": "nope,desc"}, headers=engineer), 400, "VALIDATION_FAILED")


def test_request_no_is_unique_and_sequential(client, engineer):
    numbers = [
        client.post(WR, json={"draft": True, "symptom": f"채번 {i}"}, headers=engineer).json()["requestNo"]
        for i in range(3)
    ]
    assert all(REQUEST_NO_RE.match(n) for n in numbers), numbers
    assert len(set(numbers)) == 3
    sequences = [int(n.rsplit("-", 1)[1]) for n in numbers]
    assert sequences == sorted(sequences) and sequences[-1] - sequences[0] == 2


# --------------------------------------------------------------------- 사진
def test_photo_upload(client, engineer, safety):
    wr_id = create_ready_request(client, engineer)
    r = client.post(
        WR + f"/{wr_id}/photos",
        files=[("files", ("a.jpg", jpeg_bytes(), "image/jpeg")), ("files", ("b.png", jpeg_bytes(), "image/jpeg"))],
        headers=engineer,
    )
    assert r.status_code == 201, r.text
    photos = r.json()
    assert len(photos) == 2
    assert {
        "id", "photoId", "workRequestId", "fileName", "size",
        "storageKey", "thumbnailKey", "originalUrl", "thumbnailUrl", "uploadedAt",
    } == set(photos[0])
    assert photos[0]["thumbnailUrl"].startswith("/uploads/")
    assert photos[0]["uploadedAt"].endswith(KST_SUFFIX)

    listing = client.get(WR + f"/{wr_id}/photos", headers=engineer)
    assert listing.status_code == 200 and len(listing.json()) == 2

    # 썸네일은 320px 이하로 줄어든다
    thumb = UPLOADS_DIR / photos[0]["thumbnailKey"]
    assert thumb.exists()
    with Image.open(thumb) as image:
        assert max(image.size) <= 320

    assert_error(
        client.post(WR + f"/{wr_id}/photos", files=[("files", ("x.txt", b"hello", "text/plain"))], headers=engineer),
        400, "UNSUPPORTED_FILE_TYPE", has_field_errors=True,
    )
    assert_error(
        client.post(
            WR + f"/{wr_id}/photos",
            files=[("files", ("big.jpg", b"\x00" * (10 * 1024 * 1024 + 1), "image/jpeg"))],
            headers=engineer,
        ),
        413, "FILE_TOO_LARGE",
    )
    # 이미 2장 → 4장 더 올리면 5장 초과
    assert_error(
        client.post(
            WR + f"/{wr_id}/photos",
            files=[("files", (f"{i}.jpg", jpeg_bytes(), "image/jpeg")) for i in range(4)],
            headers=engineer,
        ),
        409, "PHOTO_LIMIT_EXCEEDED",
    )
    # 개수 초과는 한 장도 저장하지 않는다
    assert len(client.get(WR + f"/{wr_id}/photos", headers=engineer).json()) == 2

    assert_error(client.post(WR + "/no-such-id/photos", files=[("files", ("a.jpg", jpeg_bytes(), "image/jpeg"))], headers=engineer), 404, "WORK_REQUEST_NOT_FOUND")
    assert_error(client.get(WR + "/no-such-id/photos", headers=engineer), 404, "WORK_REQUEST_NOT_FOUND")


def test_photo_exif_is_stripped(client, engineer):
    """저장 전에 EXIF 를 떨어뜨린다 — 촬영 기기·위치가 그대로 남지 않게."""
    wr_id = create_ready_request(client, engineer)
    original = jpeg_bytes(with_exif=True)
    with Image.open(__import__("io").BytesIO(original)) as image:
        assert image.getexif().get(0x010F) == "ReplaceFlow Test Camera"  # 업로드 전엔 있다

    r = client.post(WR + f"/{wr_id}/photos", files=[("files", ("exif.jpg", original, "image/jpeg"))], headers=engineer)
    assert r.status_code == 201, r.text
    stored = UPLOADS_DIR / r.json()[0]["storageKey"]
    with Image.open(stored) as image:
        assert dict(image.getexif()) == {}


# ------------------------------------------------------------------ 대시보드
def test_dashboard_by_role(client, engineer, safety):
    r = client.get("/api/v1/dashboard/summary", params={"role": "engineer"}, headers=engineer)
    assert r.status_code == 200, r.text
    assert set(r.json()) == {"draft", "aiRunning", "pending", "rejected"}
    assert all(isinstance(v, int) for v in r.json().values())
    assert r.json()["draft"] >= 1

    r = client.get("/api/v1/dashboard/summary", params={"role": "safety"}, headers=safety)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"pending", "todayProcessed", "monthApproved", "monthRejected", "rejectReasonsTop"}
    assert isinstance(body["rejectReasonsTop"], list)
    if body["rejectReasonsTop"]:
        assert {"reason", "count"} == set(body["rejectReasonsTop"][0])

    # 토큰 역할과 다른 대시보드 → 403
    assert_error(client.get("/api/v1/dashboard/summary?role=safety", headers=engineer), 403, "FORBIDDEN_ROLE")
    assert_error(client.get("/api/v1/dashboard/summary?role=engineer", headers=safety), 403, "FORBIDDEN_ROLE")
    # role 은 필수다
    assert_error(client.get("/api/v1/dashboard/summary", headers=engineer), 400, "VALIDATION_FAILED")


def test_incomplete_create_vs_incomplete_run_use_different_codes(client, engineer):
    """같은 필수값 누락이지만 코드가 다르다.

    - `POST /work-requests` (draft=false) → 400 `VALIDATION_FAILED` (CONTRACT §4-5)
    - `POST /agent-runs` → 400 `WORK_REQUEST_INCOMPLETE` (CONTRACT §4-11)
    검증 로직을 공유하되 코드까지 공유하면 안 된다.
    """
    partial = {"draft": False, "equipment": "가스캐비닛#2", "symptom": "누설 의심"}
    body = assert_error(client.post(WR, json=partial, headers=engineer), 400, "VALIDATION_FAILED", has_field_errors=True)
    fields = {f["field"] for f in body["fieldErrors"]}
    assert {"line", "substance", "operatingCondition", "productName", "productType", "specJson"} <= fields
    assert "equipment" not in fields  # 채워진 필드는 빠진다

    # 같은 요청을 DRAFT 로 저장한 뒤 AI 를 돌리면 코드가 달라진다
    draft_id = client.post(WR, json={**partial, "draft": True}, headers=engineer).json()["workRequestId"]
    body = assert_error(
        client.post(RUNS, json={"workRequestId": draft_id}, headers=engineer),
        400, "WORK_REQUEST_INCOMPLETE", has_field_errors=True,
    )
    assert {"line", "productType"} <= {f["field"] for f in body["fieldErrors"]}

    # 계약 §6 에 없는 코드를 만들어 쓰지 않는다
    from app.core.errors import ErrorCode

    contract_codes = {
        "VALIDATION_FAILED", "PASSWORD_MISMATCH", "SPEC_SCHEMA_MISMATCH", "REJECT_REASON_REQUIRED",
        "UNSUPPORTED_FILE_TYPE", "WORK_REQUEST_INCOMPLETE", "INVALID_CREDENTIALS", "TOKEN_EXPIRED",
        "TOKEN_INVALID", "FORBIDDEN_ROLE", "FORBIDDEN_NOT_OWNER", "WORK_REQUEST_NOT_FOUND",
        "AGENT_RUN_NOT_FOUND", "EMAIL_ALREADY_EXISTS", "RUN_ALREADY_IN_PROGRESS", "IMMUTABLE_STATUS",
        "RESULT_LOCKED", "ALREADY_DECIDED", "NOT_PENDING", "PHOTO_LIMIT_EXCEEDED", "FILE_TOO_LARGE",
        "SUBMIT_REQUIRED_FIELD_MISSING", "INTERNAL_ERROR",
    }
    # 라우팅되지 않은 경로용 2개만 계약 표 밖이다 (프레임워크 레벨, 계약이 다루지 않음)
    extra = {c.value for c in ErrorCode} - contract_codes
    assert extra == {"NOT_FOUND", "METHOD_NOT_ALLOWED"}, extra


# --------------------------------------------------------- 스펙 스키마 검증
def test_spec_schema_per_product_type(client, engineer):
    valid = {
        "VALVE": {"pressureRating": "3000 psi"},
        "FITTING_TUBE": {"connectionStandard": "1/4 in VCR", "material": "SUS316L"},
        "REGULATOR": {"pressureRating": "250 psi"},
        "FILTER": {"substanceType": "N2"},
        "ETC": {"freeSpec": "씰킷 세트, 내열 200℃"},
    }
    for product_type, spec in valid.items():
        body = {**VALVE_FIELDS, "draft": False, "productType": product_type, "specJson": spec}
        assert client.post(WR, json=body, headers=engineer).status_code == 201, product_type

    # 유형에 맞지 않는 키 → 400 SPEC_SCHEMA_MISMATCH
    bad = {**VALVE_FIELDS, "draft": False, "productType": "FITTING_TUBE", "specJson": {"pressureRating": "3000 psi"}}
    body = assert_error(client.post(WR, json=bad, headers=engineer), 400, "SPEC_SCHEMA_MISMATCH", has_field_errors=True)
    assert {"specJson.connectionStandard", "specJson.material"} == {f["field"] for f in body["fieldErrors"]}

    # DRAFT 로는 통과하고, 나중에 PATCH 로 유형을 바꿀 때 다시 검증한다
    wr_id = client.post(WR, json={"draft": True, "productType": "FILTER"}, headers=engineer).json()["workRequestId"]
    assert_error(
        client.patch(WR + f"/{wr_id}", json={"specJson": {"pressureRating": "1 psi"}}, headers=engineer),
        400, "SPEC_SCHEMA_MISMATCH",
    )


# ---------------------------------------------------------------------- 기타
def test_agent_run_not_found_and_scoping(client, engineer, safety):
    assert_error(client.get(RUNS + "/no-such-run", headers=engineer), 404, "AGENT_RUN_NOT_FOUND")
    wr_id = create_ready_request(client, engineer)
    run_id = client.get(WR + f"/{wr_id}", headers=engineer).json()["agentRun"]["runId"]
    # 안전관리자는 아직 PENDING 이 아닌 요청의 run 을 볼 수 없다
    assert_error(client.get(RUNS + f"/{run_id}", headers=safety), 403, "FORBIDDEN_NOT_OWNER")


def test_error_format_is_never_fastapi_default(client, engineer):
    """계약 §1.1 — 404·405 같은 프레임워크 오류도 {code,message} 로 나간다."""
    r = client.get("/api/v1/no-such-endpoint", headers=engineer)
    assert r.status_code == 404 and "detail" not in r.json() and r.json()["code"] == "NOT_FOUND"
    r = client.delete("/api/v1/work-requests", headers=engineer)
    assert r.status_code == 405 and r.json()["code"] == "METHOD_NOT_ALLOWED"


def test_openapi_has_15_contract_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    for p in (
        "/api/v1/auth/signup", "/api/v1/auth/login", "/api/v1/auth/me",
        "/api/v1/dashboard/summary",
        "/api/v1/work-requests", "/api/v1/work-requests/{wr_id}",
        "/api/v1/work-requests/{wr_id}/photos", "/api/v1/work-requests/{wr_id}/submit-approval",
        "/api/v1/agent-runs", "/api/v1/agent-runs/{run_id}",
        "/api/v1/agent-results/{result_id}", "/api/v1/approvals",
    ):
        assert p in paths, p
    # 경로가 최상위로 옮겨졌다 — 하위 경로 버전은 없어야 한다
    assert "/api/v1/work-requests/{wr_id}/agent-runs" not in paths
    assert "/api/v1/work-requests/{wr_id}/approvals" not in paths
    assert "/api/v1/work-requests/{wr_id}/complete" not in paths
    assert "202" in paths["/api/v1/agent-runs"]["post"]["responses"]

    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert schemas["WorkRequestStatus"]["enum"] == [
        "DRAFT", "AI_RUNNING", "AI_DONE", "PENDING", "APPROVED", "REJECTED",
    ]
    assert schemas["AgentCode"]["enum"] == ["A1", "A2", "A3"]
    assert schemas["AgentStepStatus"]["enum"] == ["WAITING", "RUNNING", "DONE", "FAILED"]
    assert schemas["ProductType"]["enum"] == ["VALVE", "FITTING_TUBE", "REGULATOR", "FILTER", "ETC"]
    assert schemas["Role"]["enum"] == ["ENGINEER", "SAFETY_MANAGER"]
    assert client.get("/docs").status_code == 200


# --------------------------------------------------- FE(constants/domain.js) 정합
def test_fe_contract_alignment(client, engineer, safety):
    """FE 가 기대하는 어휘·키를 고정한다. 여기서 깨지면 화면이 조용히 빈칸이 된다."""
    # nextAction 어휘는 FE NEXT_ACTION 과 같아야 한다
    from app.core.enums import NextAction

    assert {a.value for a in NextAction} == {"CONTINUE", "RUN", "RESULT", "DETAIL"}

    # draft 는 쿼리스트링으로도 받는다 (FE 는 params: { draft } 로 보낸다)
    r = client.post(WR + "?draft=true", json={"symptom": "쿼리 draft"}, headers=engineer)
    assert r.status_code == 201 and r.json()["status"] == "DRAFT"

    wr_id = create_ready_request(client, engineer)
    detail = client.get(WR + f"/{wr_id}", headers=engineer).json()
    # 엔티티 자신의 id 는 `id` 로도 나온다 — FE 는 wr.id · run.id · result.id 를 쓴다
    assert detail["id"] == detail["workRequestId"]
    assert detail["agentRun"]["id"] == detail["agentRun"]["runId"]
    for result in detail["agentRun"]["results"]:
        assert result["id"] == result["agentResultId"]
    # 상세에 photos 가 포함된다 (FE toDetail 이 wr.photos 를 읽는다)
    assert detail["photos"] == []

    # 사진 URL 은 정적 마운트가 실제로 서빙한다
    r = client.post(WR + f"/{wr_id}/photos", files=[("files", ("a.jpg", jpeg_bytes(), "image/jpeg"))], headers=engineer)
    photo = r.json()[0]
    assert client.get(photo["thumbnailUrl"]).status_code == 200
    assert client.get(photo["originalUrl"]).status_code == 200
    assert client.get(WR + f"/{wr_id}", headers=engineer).json()["photos"][0]["id"] == photo["id"]

    # 승인 응답도 id 두 키
    client.patch(WR + f"/{wr_id}/submit-approval", headers=engineer)
    approval = client.post(APPROVALS, json={"workRequestId": wr_id, "decision": "APPROVE"}, headers=safety).json()
    assert approval["id"] == approval["approvalId"]
