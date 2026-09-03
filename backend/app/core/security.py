"""비밀번호 해싱(bcrypt) + JWT Bearer 토큰 (CONTRACT §1 / §5).

- 비밀번호: `bcrypt` 로만 저장한다(평문 저장 금지). `password_hash` 는 60자 `$2b$…`.
  bcrypt 는 72바이트를 넘는 입력을 거부하므로 길이 검증을 여기서 함께 제공한다.
- 토큰: HS256 JWT. 서명 키는 Settings(`.env`)에서만 온다 — 이 모듈이 os.environ 을 읽지 않는다.
  만료와 위조를 구분해 각각 TOKEN_EXPIRED / TOKEN_INVALID 로 올린다.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode

BCRYPT_ROUNDS = 12
BCRYPT_MAX_BYTES = 72


# --------------------------------------------------------------------- password
def password_too_long(password: str) -> bool:
    return len(password.encode("utf-8")) > BCRYPT_MAX_BYTES


def hash_password(password: str) -> str:
    if password_too_long(password):
        raise AppError(
            ErrorCode.VALIDATION_FAILED,
            f"비밀번호는 {BCRYPT_MAX_BYTES}바이트를 넘을 수 없습니다",
            [{"field": "password", "message": f"최대 {BCRYPT_MAX_BYTES}바이트"}],
        )
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("ascii")


def verify_password(password: str, stored: str | None) -> bool:
    if not stored or password_too_long(password):
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ------------------------------------------------------------------------ token
def create_access_token(user_id: str, role: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=settings.token_ttl_hours)).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """유효한 payload 를 돌려준다. 만료는 TOKEN_EXPIRED, 그 외 위조·손상은 TOKEN_INVALID."""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AppError(ErrorCode.TOKEN_EXPIRED, "토큰이 만료되었습니다. 다시 로그인하세요") from exc
    except jwt.PyJWTError as exc:
        raise AppError(ErrorCode.TOKEN_INVALID, "토큰이 유효하지 않습니다") from exc
