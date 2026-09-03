"""공통 FastAPI 의존성.

`get_current_user` 가 유일한 인증 게이트다. `/auth/signup`·`/auth/login` 을 뺀 전 API 에
걸린다(CONTRACT §1). 토큰이 없거나 손상되면 401 `TOKEN_INVALID`, 만료면 401 `TOKEN_EXPIRED`.
"""
from __future__ import annotations

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.enums import Role
from app.core.errors import AppError, ErrorCode
from app.core.security import decode_access_token
from app.db.session import get_db  # noqa: F401  (라우터에서 재수출해 쓴다)
from app.models import User


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization:
        raise AppError(ErrorCode.TOKEN_INVALID, "인증 토큰이 필요합니다")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise AppError(ErrorCode.TOKEN_INVALID, "Authorization 헤더 형식이 올바르지 않습니다 (Bearer {accessToken})")
    payload = decode_access_token(token.strip())  # 만료/위조를 각각의 코드로 올린다
    user = db.get(User, payload.get("sub") or "")
    if user is None:
        raise AppError(ErrorCode.TOKEN_INVALID, "토큰의 사용자를 찾을 수 없습니다")
    return user


def require_engineer(current: User = Depends(get_current_user)) -> User:
    if current.role is not Role.ENGINEER:
        raise AppError(ErrorCode.FORBIDDEN_ROLE, "엔지니어만 사용할 수 있는 기능입니다")
    return current


def require_safety_manager(current: User = Depends(get_current_user)) -> User:
    if current.role is not Role.SAFETY_MANAGER:
        raise AppError(ErrorCode.FORBIDDEN_ROLE, "안전관리자만 사용할 수 있는 기능입니다")
    return current
