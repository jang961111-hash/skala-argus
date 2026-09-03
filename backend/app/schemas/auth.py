"""인증 스키마 (CONTRACT §4-1~3).

응답 모델 어디에도 `password_hash` 필드가 없다 — 해시가 새어 나갈 경로 자체를 없앤다.
`passwordConfirm` 불일치는 별도 코드(400 `PASSWORD_MISMATCH`)라서 여기서 검증하지 않고
서비스가 판정한다. 여기서 걸리는 것은 전부 400 `VALIDATION_FAILED` 다.
"""
from __future__ import annotations

import re

from pydantic import Field, field_validator

from app.core.enums import Role
from app.schemas.base import CamelModel, KstDatetime

# 외부 의존성(email-validator) 없이 형식만 본다
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
# 8자 이상, 영문 + 숫자 + 특수문자 (CONTRACT §4-1)
PASSWORD_SPECIALS = r"!@#$%^&*()\-_=+\[\]{};:'\",.<>/?\\|`~"


def validate_password_policy(value: str) -> str:
    if len(value) < 8:
        raise ValueError("비밀번호는 8자 이상이어야 합니다")
    if len(value.encode("utf-8")) > 72:
        raise ValueError("비밀번호는 72바이트를 넘을 수 없습니다")
    if not re.search(r"[A-Za-z]", value):
        raise ValueError("비밀번호에 영문이 포함되어야 합니다")
    if not re.search(r"\d", value):
        raise ValueError("비밀번호에 숫자가 포함되어야 합니다")
    if not re.search(f"[{PASSWORD_SPECIALS}]", value):
        raise ValueError("비밀번호에 특수문자가 포함되어야 합니다")
    return value


class SignupRequest(CamelModel):
    name: str = Field(min_length=2, max_length=20, examples=["김민준"])
    email: str = Field(examples=["engineer@replaceflow.test"])
    password: str = Field(examples=["Passw0rd!"])
    password_confirm: str = Field(examples=["Passw0rd!"])
    role: Role = Field(examples=["ENGINEER"])

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("이메일 형식이 올바르지 않습니다")
        return v

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return validate_password_policy(v)


class LoginRequest(CamelModel):
    email: str = Field(examples=["engineer@replaceflow.test"])
    password: str = Field(min_length=1, examples=["Passw0rd!"])

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(CamelModel):
    #: 같은 값을 `id` 와 `userId` 두 키로 낸다 — 계약 §1 은 한정명을, FE 는 `id` 를 쓴다
    id: str
    user_id: str
    name: str
    email: str
    role: Role
    redirect_path: str
    created_at: KstDatetime


class LoginResponse(CamelModel):
    """`redirectPath` 는 서버가 정한다 — 프론트는 그 값을 그대로 쓴다 (CONTRACT §4-2)."""

    access_token: str
    token_type: str = "Bearer"
    role: Role
    redirect_path: str
