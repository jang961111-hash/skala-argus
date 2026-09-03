import io
import os
import shutil
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# 앱 모듈이 설정을 읽기 전에 테스트 전용 DB·업로드 경로를 잡는다
_test_db = BACKEND / "test_argus.db"
_test_uploads = BACKEND / "test_uploads"
if _test_db.exists():
    _test_db.unlink()
if _test_uploads.exists():
    shutil.rmtree(_test_uploads, ignore_errors=True)
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db}"
os.environ["AI_PROVIDER"] = "MOCK"
os.environ["EGRESS_ALLOWED"] = "false"
os.environ["BACKGROUND_ADVANCE"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-bytes-long!"
os.environ["UPLOADS_DIR"] = "test_uploads"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.main import app  # noqa: E402

SEED_PASSWORD = "Passw0rd!"
ENGINEER_EMAIL = "engineer@argus.test"
SAFETY_EMAIL = "safety@argus.test"

UPLOADS_DIR = _test_uploads

VALVE_FIELDS = {
    "equipment": "가스캐비닛#2",
    "line": "A라인",
    "substance": "SiH4",
    "operatingCondition": {"temperature": "상온", "pressure": "3000 psi"},
    "productName": "SS-8-VCR",
    "productType": "VALVE",
    "specJson": {"pressureRating": "3000 psi"},
    "symptom": "가스 유량 이상, 밸브 누설 의심",
    "siteMemo": "현장 확인 결과 밸브 시트 마모",
}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
    if _test_db.exists():
        _test_db.unlink()
    if _test_uploads.exists():
        shutil.rmtree(_test_uploads, ignore_errors=True)


def login(client, email: str, password: str = SEED_PASSWORD) -> dict[str, str]:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['accessToken']}"}


@pytest.fixture(scope="session")
def engineer(client) -> dict[str, str]:
    """시드 엔지니어 — 시드 작업요청 6건의 요청자."""
    return login(client, ENGINEER_EMAIL)


@pytest.fixture(scope="session")
def safety(client) -> dict[str, str]:
    """시드 안전관리자."""
    return login(client, SAFETY_EMAIL)


def jpeg_bytes(size=(200, 150), color=(120, 30, 30), with_exif: bool = False) -> bytes:
    buffer = io.BytesIO()
    image = Image.new("RGB", size, color)
    if with_exif:
        exif = Image.Exif()
        exif[0x010F] = "Argus Test Camera"  # Make
        exif[0x0110] = "RF-1000"  # Model
        image.save(buffer, format="JPEG", exif=exif.tobytes())
    else:
        image.save(buffer, format="JPEG")
    return buffer.getvalue()


def run_agents_to_done(client, headers, wr_id: str) -> str:
    """AI 실행을 걸고 3회 폴링해 AI_DONE 까지 진행시킨다. run_id 를 돌려준다."""
    r = client.post("/api/v1/agent-runs", json={"workRequestId": wr_id}, headers=headers)
    assert r.status_code == 202, r.text
    run_id = r.json()["runId"]
    for _ in range(3):
        client.get(f"/api/v1/agent-runs/{run_id}", headers=headers)
    return run_id


def create_ready_request(client, headers, **overrides) -> str:
    """제출 직전(AI_DONE + engineerNote)까지 만들어 둔 요청의 id 를 돌려준다."""
    body = {**VALVE_FIELDS, "draft": False, **overrides}
    r = client.post("/api/v1/work-requests", json=body, headers=headers)
    assert r.status_code == 201, r.text
    wr_id = r.json()["workRequestId"]
    run_agents_to_done(client, headers, wr_id)
    client.patch(f"/api/v1/work-requests/{wr_id}", json={"engineerNote": "제92조 운전정지·LOTO 적용 필요"}, headers=headers)
    return wr_id
