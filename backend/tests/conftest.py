import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# Isolated SQLite DB per test session, before app modules read settings
_test_db = BACKEND / "test_replaceflow.db"
if _test_db.exists():
    _test_db.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db}"
os.environ["AI_PROVIDER"] = "MOCK"
os.environ["EGRESS_ALLOWED"] = "false"
os.environ["BACKGROUND_ADVANCE"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
    if _test_db.exists():
        _test_db.unlink()
