"""인증 (docs/CONTRACT.md §4-1~3, §1.1, §6).

signup 201/400/409 · login 200/401 · me 200/401 · 미인증 401 · `password_hash` 미노출 ·
모든 오류가 `{code, message, fieldErrors?}` 단일 포맷인지.
"""
import time

import jwt

SIGNUP = "/api/v1/auth/signup"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"

NEW_USER = {
    "name": "신규엔지니어",
    "email": "New.Engineer@replaceflow.test",
    "password": "Passw0rd!",
    "passwordConfirm": "Passw0rd!",
    "role": "ENGINEER",
}


def assert_error(response, status: int, code: str, *, has_field_errors: bool | None = None):
    """계약 §1.1 단일 포맷 — FastAPI 기본 `detail` 이 새어 나오면 실패한다."""
    assert response.status_code == status, response.text
    body = response.json()
    assert "detail" not in body, body
    assert body["code"] == code, body
    assert isinstance(body.get("message"), str) and body["message"]
    if has_field_errors is True:
        assert body.get("fieldErrors"), body
        assert {"field", "message"} <= set(body["fieldErrors"][0])
    if has_field_errors is False:
        assert "fieldErrors" not in body, body
    return body


def _assert_no_hash(payload):
    text = repr(payload)
    assert "password_hash" not in text and "passwordHash" not in text
    assert "$2b$" not in text
    assert "Passw0rd!" not in text


def test_signup_201(client):
    r = client.post(SIGNUP, json=NEW_USER)
    assert r.status_code == 201, r.text
    user = r.json()
    # 엔티티 자신의 id 는 `id` 와 `userId` 두 키로 나온다 (FE 는 `id`, 계약 §1 예시는 한정명)
    assert set(user) == {"id", "userId", "name", "email", "role", "redirectPath", "createdAt"}
    assert user["id"] == user["userId"]
    assert user["email"] == "new.engineer@replaceflow.test"  # 소문자로 정규화
    assert user["role"] == "ENGINEER" and user["redirectPath"] == "/home"
    assert user["createdAt"].endswith("+09:00")  # KST 오프셋 포함
    _assert_no_hash(user)


def test_signup_409_duplicate_email(client):
    assert_error(client.post(SIGNUP, json=NEW_USER), 409, "EMAIL_ALREADY_EXISTS", has_field_errors=False)
    # 대소문자만 다른 이메일도 중복이다
    assert_error(
        client.post(SIGNUP, json={**NEW_USER, "email": "NEW.ENGINEER@replaceflow.test"}),
        409, "EMAIL_ALREADY_EXISTS",
    )


def test_signup_400_password_mismatch(client):
    r = client.post(SIGNUP, json={**NEW_USER, "email": "mismatch@replaceflow.test", "passwordConfirm": "Other1234!"})
    assert_error(r, 400, "PASSWORD_MISMATCH", has_field_errors=True)


def test_signup_400_validation_failed(client):
    cases = {
        "필수 누락": {"email": "a@b.co", "password": "Passw0rd!"},
        "이메일 형식": {**NEW_USER, "email": "not-an-email"},
        "이름 1자": {**NEW_USER, "email": "n1@b.co", "name": "김"},
        "8자 미만": {**NEW_USER, "email": "n2@b.co", "password": "Pw1!", "passwordConfirm": "Pw1!"},
        "숫자 없음": {**NEW_USER, "email": "n3@b.co", "password": "Password!", "passwordConfirm": "Password!"},
        "특수문자 없음": {**NEW_USER, "email": "n4@b.co", "password": "Password1", "passwordConfirm": "Password1"},
        "영문 없음": {**NEW_USER, "email": "n5@b.co", "password": "12345678!", "passwordConfirm": "12345678!"},
        "역할 없음": {**NEW_USER, "email": "n6@b.co", "role": "ADMIN"},
    }
    for label, body in cases.items():
        assert_error(client.post(SIGNUP, json=body), 400, "VALIDATION_FAILED", has_field_errors=True), label


def test_login_200_returns_redirect_path(client):
    r = client.post(LOGIN, json={"email": "engineer@replaceflow.test", "password": "Passw0rd!"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"accessToken", "tokenType", "role", "redirectPath"}
    assert body["tokenType"] == "Bearer" and body["role"] == "ENGINEER"
    assert body["redirectPath"] == "/home"
    _assert_no_hash(body)

    r = client.post(LOGIN, json={"email": "safety@replaceflow.test", "password": "Passw0rd!"})
    assert r.json()["role"] == "SAFETY_MANAGER" and r.json()["redirectPath"] == "/manage/requests"


def test_login_401(client):
    assert_error(
        client.post(LOGIN, json={"email": "engineer@replaceflow.test", "password": "WrongPass1!"}),
        401, "INVALID_CREDENTIALS",
    )
    # 없는 계정도 같은 응답 — 계정 존재 여부를 흘리지 않는다
    assert_error(
        client.post(LOGIN, json={"email": "nobody@replaceflow.test", "password": "Passw0rd!"}),
        401, "INVALID_CREDENTIALS",
    )


def test_me_200(client, engineer):
    r = client.get(ME, headers=engineer)
    assert r.status_code == 200
    assert r.json()["email"] == "engineer@replaceflow.test"
    _assert_no_hash(r.json())


def test_unauthenticated_401_everywhere(client):
    """CONTRACT §1: /auth/signup·/auth/login 을 뺀 전 API 는 토큰이 필요하다."""
    for method, path in (
        ("get", ME),
        ("get", "/api/v1/dashboard/summary?role=engineer"),
        ("post", "/api/v1/work-requests"),
        ("get", "/api/v1/work-requests"),
        ("get", "/api/v1/work-requests/some-id"),
        ("patch", "/api/v1/work-requests/some-id"),
        ("post", "/api/v1/work-requests/some-id/photos"),
        ("get", "/api/v1/work-requests/some-id/photos"),
        ("patch", "/api/v1/work-requests/some-id/submit-approval"),
        ("post", "/api/v1/agent-runs"),
        ("get", "/api/v1/agent-runs/some-id"),
        ("patch", "/api/v1/agent-results/some-id"),
        ("post", "/api/v1/approvals"),
    ):
        kwargs = {"json": {}} if method in {"post", "patch"} else {}
        r = getattr(client, method)(path, **kwargs)
        assert_error(r, 401, "TOKEN_INVALID"), f"{method.upper()} {path}"


def test_malformed_tokens_401(client):
    for header in ("Bearer", "Bearer ", "Token abc", "Bearer not-a-jwt", "Bearer a.b.c"):
        assert_error(client.get(ME, headers={"Authorization": header}), 401, "TOKEN_INVALID"), header


def test_expired_token_401(client):
    """만료는 TOKEN_INVALID 가 아니라 TOKEN_EXPIRED 다."""
    now = int(time.time())
    token = jwt.encode(
        {"sub": "whoever", "role": "ENGINEER", "iat": now - 7200, "exp": now - 3600},
        "test-secret-key-at-least-32-bytes-long!",
        algorithm="HS256",
    )
    assert_error(client.get(ME, headers={"Authorization": f"Bearer {token}"}), 401, "TOKEN_EXPIRED")


def test_token_signed_with_other_key_401(client):
    now = int(time.time())
    token = jwt.encode(
        {"sub": "x", "role": "ENGINEER", "exp": now + 3600},
        "a-completely-different-key-32-bytes-long",
        algorithm="HS256",
    )
    assert_error(client.get(ME, headers={"Authorization": f"Bearer {token}"}), 401, "TOKEN_INVALID")


def test_password_hash_never_leaks(client, engineer, safety):
    wr_id = client.get("/api/v1/work-requests", headers=engineer).json()["content"][0]["workRequestId"]
    for headers, path in (
        (engineer, ME),
        (engineer, "/api/v1/work-requests"),
        (engineer, f"/api/v1/work-requests/{wr_id}"),
        (engineer, "/api/v1/dashboard/summary?role=engineer"),
        (safety, "/api/v1/dashboard/summary?role=safety"),
    ):
        r = client.get(path, headers=headers)
        assert r.status_code == 200, path
        _assert_no_hash(r.json())
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    _assert_no_hash(schemas["UserResponse"])


def test_auth_endpoints_in_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    for p in ("/api/v1/auth/signup", "/api/v1/auth/login", "/api/v1/auth/me"):
        assert p in paths, p
    assert "201" in paths["/api/v1/auth/signup"]["post"]["responses"]
