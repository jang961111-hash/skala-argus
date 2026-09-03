"""AuthService — signup / login (CONTRACT §4-1~3).

비밀번호는 bcrypt 해시로만 저장한다. `redirectPath` 는 서버가 정해 내려주고 프론트는
그 값을 그대로 쓴다 — 역할별 진입점을 프론트에 흩뿌리지 않기 위해서다.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.enums import Role
from app.core.errors import AppError, ErrorCode
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, SignupRequest

REDIRECT_PATH: dict[Role, str] = {
    Role.ENGINEER: "/home",
    Role.SAFETY_MANAGER: "/manage/requests",
}


def redirect_path_for(role: Role) -> str:
    return REDIRECT_PATH[role]


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def signup(self, body: SignupRequest) -> User:
        if body.password != body.password_confirm:
            raise AppError(
                ErrorCode.PASSWORD_MISMATCH,
                "비밀번호가 일치하지 않습니다",
                [{"field": "passwordConfirm", "message": "비밀번호 확인이 일치하지 않습니다"}],
            )
        if self.users.get_by_email(body.email) is not None:
            raise AppError(
                ErrorCode.EMAIL_ALREADY_EXISTS,
                "이미 사용 중인 이메일입니다",
            )
        user = User(
            name=body.name,
            email=body.email,
            password_hash=hash_password(body.password),
            role=body.role,
            created_at=datetime.now(timezone.utc),
        )
        return self.users.add(user)

    def login(self, body: LoginRequest) -> tuple[str, User]:
        user = self.users.get_by_email(body.email)
        if user is None or not verify_password(body.password, user.password_hash):
            # 계정 존재 여부를 흘리지 않도록 두 경우 모두 같은 응답을 준다
            raise AppError(ErrorCode.INVALID_CREDENTIALS, "이메일 또는 비밀번호가 올바르지 않습니다")
        return create_access_token(user.id, user.role.value), user
