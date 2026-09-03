"""End-to-end flow per docs/CONTRACT.md: create → agent-run 202 → poll 4x → REVIEW → submit → approve."""

FULL = {"WORK_PERMIT": True, "RISK_ASSESSMENT": True, "LOTO_GAS_ISOLATION": True, "GAS_DETECTOR_CHECK": True}
ORDER = ["SPEC", "LEGAL", "SAFETY_DOC", "VENDOR"]


def test_full_flow(client):
    # 1. create work request → 201 REQUESTED
    r = client.post(
        "/api/v1/work-requests",
        json={
            "tenant_id": "T-001",
            "equipment_id": "EQ-GC-02",
            "part_id": "P-VLV-001",
            "symptom": "가스 유량 이상, 밸브 누설 의심",
            "site_check_note": "현장 확인 결과 밸브 시트 마모",
            "requested_by": "U-001",
        },
    )
    assert r.status_code == 201, r.text
    wr = r.json()
    wr_id = wr["id"]
    assert wr_id.startswith("WR-") and wr["status"] == "REQUESTED"
    for k in ("tenant_id", "equipment_id", "part_id", "symptom", "site_check_note", "requested_by", "created_at", "updated_at"):
        assert k in wr

    # approvals before PENDING_APPROVAL → 409
    r = client.post(f"/api/v1/work-requests/{wr_id}/approvals", json={"approver_id": "U-002", "decision": "APPROVE", "checklist": FULL})
    assert r.status_code == 409

    # submit-approval before run → 409
    r = client.patch(f"/api/v1/work-requests/{wr_id}/submit-approval")
    assert r.status_code == 409

    # 2. POST agent-runs → 202, 4 PENDING steps
    r = client.post(f"/api/v1/work-requests/{wr_id}/agent-runs")
    assert r.status_code == 202, r.text
    assert r.json()["overall_status"] == "RUNNING"
    run_id = r.json()["run_id"]
    assert run_id.startswith("RUN-")
    assert client.get(f"/api/v1/work-requests/{wr_id}").json()["status"] == "RUNNING"

    # duplicate run while RUNNING → 409
    assert client.post(f"/api/v1/work-requests/{wr_id}/agent-runs").status_code == 409

    # 3. GET 4 times → one step DONE per call, in order
    for i, agent in enumerate(ORDER, start=1):
        r = client.get(f"/api/v1/agent-runs/{run_id}")
        assert r.status_code == 200, r.text
        run = r.json()
        steps = run["steps"]
        assert [s["agent"] for s in steps] == ORDER
        done = [s["agent"] for s in steps if s["status"] == "DONE"]
        assert done == ORDER[:i], (i, done)
        assert steps[i - 1]["result"] is not None
        assert run["overall_status"] == ("REVIEW" if i == 4 else "RUNNING")

    # result shapes match CONTRACT
    by_agent = {s["agent"]: s["result"] for s in run["steps"]}
    assert by_agent["SPEC"]["spec_match"] is True and by_agent["SPEC"]["current_part"] == "VLV-SS316-1/4-NC"
    assert by_agent["SPEC"]["alternatives"][0]["allowed_for_toxic_gas"] is False
    assert len(by_agent["LEGAL"]["applicable_laws"]) == 3 and len(by_agent["LEGAL"]["required_procedures"]) == 4
    docs = by_agent["SAFETY_DOC"]["documents"]
    assert [d["type"] for d in docs] == ["WORK_PERMIT", "RISK_ASSESSMENT"]
    assert docs[0]["missing"] == ["작업자 2명 이름"]
    assert by_agent["VENDOR"]["lead_time_est_days"] == 3 and by_agent["VENDOR"]["rfq_doc_id"].startswith("DOC-")
    assert run["summary"] and run["model_name"] == "mock-v1" and run["prompt_version"] == "replaceflow-v0.1"
    assert run["approval_required_by"] == "SAFETY_MANAGER" and run["completed_at"]

    # extra GET is idempotent once REVIEW
    assert client.get(f"/api/v1/agent-runs/{run_id}").json()["overall_status"] == "REVIEW"

    # work request is REVIEW, detail includes latest_run
    detail = client.get(f"/api/v1/work-requests/{wr_id}").json()
    assert detail["status"] == "REVIEW" and detail["latest_run"]["run_id"] == run_id and detail["approvals"] == []

    # documents are real rows
    doc = client.get(f"/api/v1/documents/{docs[0]['doc_id']}")
    assert doc.status_code == 200 and doc.json()["type"] == "WORK_PERMIT" and doc.json()["missing"] == ["작업자 2명 이름"]
    assert client.get("/api/v1/documents/DOC-9999").status_code == 404

    # 4. submit-approval with missing info → 422; with info → 200 PENDING_APPROVAL
    r = client.patch(f"/api/v1/work-requests/{wr_id}/submit-approval")
    assert r.status_code == 422, r.text
    r = client.patch(f"/api/v1/work-requests/{wr_id}/submit-approval", json={"missing_info": {"작업자 2명 이름": "김민준, 박수진"}})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "PENDING_APPROVAL"
    assert client.get(f"/api/v1/documents/{docs[0]['doc_id']}").json()["missing"] == []

    # 5. APPROVE with incomplete checklist → 409
    r = client.post(
        f"/api/v1/work-requests/{wr_id}/approvals",
        json={"approver_id": "U-002", "decision": "APPROVE", "checklist": {**FULL, "GAS_DETECTOR_CHECK": False}, "comment": "x"},
    )
    assert r.status_code == 409, r.text
    assert client.get(f"/api/v1/work-requests/{wr_id}").json()["status"] == "PENDING_APPROVAL"

    # engineer cannot approve → 409
    r = client.post(f"/api/v1/work-requests/{wr_id}/approvals", json={"approver_id": "U-001", "decision": "APPROVE", "checklist": FULL})
    assert r.status_code == 409

    # 6. full checklist → 201, status APPROVED
    r = client.post(
        f"/api/v1/work-requests/{wr_id}/approvals",
        json={"approver_id": "U-002", "decision": "APPROVE", "checklist": FULL, "comment": "작업자 명단 확인 완료. 승인."},
    )
    assert r.status_code == 201, r.text
    ap = r.json()
    assert ap["approval_id"].startswith("AP-") and ap["decision"] == "APPROVE" and ap["checklist"] == FULL
    assert ap["work_request_id"] == wr_id and ap["approver_id"] == "U-002" and ap["decided_at"]
    detail = client.get(f"/api/v1/work-requests/{wr_id}").json()
    assert detail["status"] == "APPROVED" and len(detail["approvals"]) == 1

    # agent-run on APPROVED → 409
    assert client.post(f"/api/v1/work-requests/{wr_id}/agent-runs").status_code == 409

    # 7. complete → DONE
    r = client.patch(f"/api/v1/work-requests/{wr_id}/complete")
    assert r.status_code == 200 and r.json()["status"] == "DONE"


def test_reject_and_request_info(client):
    # seeded WR-20260831-002 is PENDING_APPROVAL
    r = client.get("/api/v1/work-requests", params={"status": "PENDING_APPROVAL"})
    assert r.status_code == 200
    wr_id = r.json()["items"][0]["id"]
    r = client.post(
        f"/api/v1/work-requests/{wr_id}/approvals",
        json={"approver_id": "U-002", "decision": "REJECT", "checklist": {}, "comment": "호환품 부적합: 유독가스 라인"},
    )
    assert r.status_code == 201 and r.json()["decision"] == "REJECT"
    assert client.get(f"/api/v1/work-requests/{wr_id}").json()["status"] == "REJECTED"


def test_404s(client):
    assert client.get("/api/v1/work-requests/WR-NOPE").status_code == 404
    assert client.post("/api/v1/work-requests/WR-NOPE/agent-runs").status_code == 404
    assert client.get("/api/v1/agent-runs/RUN-9999").status_code == 404
    assert client.post("/api/v1/work-requests/WR-NOPE/approvals", json={"approver_id": "U-002", "decision": "APPROVE"}).status_code == 404
    assert client.get("/api/v1/parts/P-NOPE/compatibility").status_code == 404
    assert client.get("/api/v1/tenants/T-NOPE/ai-config").status_code == 404


def test_list_and_seed(client):
    r = client.get("/api/v1/work-requests", params={"page": 1, "size": 3})
    body = r.json()
    assert r.status_code == 200 and len(body["items"]) == 3 and body["total"] >= 5
    item = body["items"][0]
    for k in ("id", "equipment_id", "part_id", "status", "agent_progress", "created_at"):
        assert k in item
    assert client.get("/api/v1/work-requests", params={"status": "BOGUS"}).status_code == 422


def test_dashboard(client):
    r = client.get("/api/v1/dashboard/summary")
    assert r.status_code == 200, r.text
    d = r.json()
    assert set(d) == {"in_progress", "pending_approval", "avg_approval_hours", "as_is_baseline_hours", "completed_this_month", "reject_reasons_top"}
    assert d["as_is_baseline_hours"] == 168
    assert d["avg_approval_hours"] > 0
    assert d["in_progress"] >= 1
    assert isinstance(d["reject_reasons_top"], list)
    if d["reject_reasons_top"]:
        assert {"reason", "count"} <= set(d["reject_reasons_top"][0])


def test_laws_search(client):
    r = client.get("/api/v1/laws/search", params={"q": "운전정지"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(i["article"] == "제92조" for i in items)
    assert {"id", "law", "article", "title", "text", "effective_date", "source_uri"} <= set(items[0])
    r = client.get("/api/v1/laws/search", params={"equipmentType": "GAS_CABINET", "substance": "SiH4"})
    assert r.status_code == 200 and len(r.json()["items"]) >= 2
    assert len(client.get("/api/v1/laws/search").json()["items"]) == 6


def test_master_and_ai_config(client):
    assert len(client.get("/api/v1/equipments").json()) == 3
    assert len(client.get("/api/v1/parts").json()) == 4
    comp = client.get("/api/v1/parts/P-VLV-001/compatibility").json()
    assert comp["part"]["part_no"] == "VLV-SS316-1/4-NC"
    assert comp["alternatives"][0]["part_no"] == "VLV-SS316-1/4-NC-EQ" and comp["alternatives"][0]["allowed_for_toxic_gas"] is False

    cfg = client.get("/api/v1/tenants/T-001/ai-config").json()
    assert len(cfg) == 4 and all(c["provider"] == "LOCAL_LLM" and c["egress_allowed"] is False for c in cfg)
    # external provider without egress → 409 (Security & Config Isolation)
    r = client.put("/api/v1/tenants/T-001/ai-config", json=[{"agent_type": "LEGAL", "provider": "OPENAI", "egress_allowed": False}])
    assert r.status_code == 409
    r = client.put("/api/v1/tenants/T-001/ai-config", json=[{"agent_type": "LEGAL", "provider": "AX_PLATFORM", "model_name": "ax-1", "egress_allowed": True}])
    assert r.status_code == 200
    assert next(c for c in r.json() if c["agent_type"] == "LEGAL")["provider"] == "AX_PLATFORM"


def test_openapi(client):
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    for p in (
        "/api/v1/work-requests", "/api/v1/work-requests/{wr_id}", "/api/v1/work-requests/{wr_id}/agent-runs",
        "/api/v1/agent-runs/{run_id}", "/api/v1/work-requests/{wr_id}/submit-approval", "/api/v1/work-requests/{wr_id}/approvals",
        "/api/v1/documents/{doc_id}", "/api/v1/parts/{part_id}/compatibility", "/api/v1/laws/search", "/api/v1/dashboard/summary",
        "/api/v1/tenants/{tenant_id}/ai-config", "/api/v1/equipments", "/api/v1/parts",
    ):
        assert p in paths, p
    assert "202" in paths["/api/v1/work-requests/{wr_id}/agent-runs"]["post"]["responses"]
    assert client.get("/docs").status_code == 200
