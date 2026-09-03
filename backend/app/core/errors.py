"""단일 에러 포맷 (CONTRACT §1.1 / §6).

모든 4xx·5xx 응답은 `{code, message, fieldErrors?}` 다.
FastAPI 기본 `{"detail": ...}` 는 main.py 의 예외 핸들러에서 전부 이 형태로 바뀐다.
`fieldErrors` 는 입력 유효성 오류(400·422)에서만 포함한다.
"""
from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    # 400
    VALIDATION_FAILED = "VALIDATION_FAILED"
    PASSWORD_MISMATCH = "PASSWORD_MISMATCH"
    SPEC_SCHEMA_MISMATCH = "SPEC_SCHEMA_MISMATCH"
    REJECT_REASON_REQUIRED = "REJECT_REASON_REQUIRED"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    WORK_REQUEST_INCOMPLETE = "WORK_REQUEST_INCOMPLETE"
    # 401
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    # 403
    FORBIDDEN_ROLE = "FORBIDDEN_ROLE"
    FORBIDDEN_NOT_OWNER = "FORBIDDEN_NOT_OWNER"
    # 404
    WORK_REQUEST_NOT_FOUND = "WORK_REQUEST_NOT_FOUND"
    AGENT_RUN_NOT_FOUND = "AGENT_RUN_NOT_FOUND"
    NOT_FOUND = "NOT_FOUND"  # 라우팅되지 않은 경로 (계약 표에 없는 일반 케이스)
    # 409
    EMAIL_ALREADY_EXISTS = "EMAIL_ALREADY_EXISTS"
    RUN_ALREADY_IN_PROGRESS = "RUN_ALREADY_IN_PROGRESS"
    IMMUTABLE_STATUS = "IMMUTABLE_STATUS"
    RESULT_LOCKED = "RESULT_LOCKED"
    ALREADY_DECIDED = "ALREADY_DECIDED"
    NOT_PENDING = "NOT_PENDING"
    PHOTO_LIMIT_EXCEEDED = "PHOTO_LIMIT_EXCEEDED"
    # 413
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    # 422
    SUBMIT_REQUIRED_FIELD_MISSING = "SUBMIT_REQUIRED_FIELD_MISSING"
    # 405 / 500
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


STATUS_BY_CODE: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_FAILED: 400,
    ErrorCode.PASSWORD_MISMATCH: 400,
    ErrorCode.SPEC_SCHEMA_MISMATCH: 400,
    ErrorCode.REJECT_REASON_REQUIRED: 400,
    ErrorCode.UNSUPPORTED_FILE_TYPE: 400,
    ErrorCode.WORK_REQUEST_INCOMPLETE: 400,
    ErrorCode.INVALID_CREDENTIALS: 401,
    ErrorCode.TOKEN_EXPIRED: 401,
    ErrorCode.TOKEN_INVALID: 401,
    ErrorCode.FORBIDDEN_ROLE: 403,
    ErrorCode.FORBIDDEN_NOT_OWNER: 403,
    ErrorCode.WORK_REQUEST_NOT_FOUND: 404,
    ErrorCode.AGENT_RUN_NOT_FOUND: 404,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.EMAIL_ALREADY_EXISTS: 409,
    ErrorCode.RUN_ALREADY_IN_PROGRESS: 409,
    ErrorCode.IMMUTABLE_STATUS: 409,
    ErrorCode.RESULT_LOCKED: 409,
    ErrorCode.ALREADY_DECIDED: 409,
    ErrorCode.NOT_PENDING: 409,
    ErrorCode.PHOTO_LIMIT_EXCEEDED: 409,
    ErrorCode.FILE_TOO_LARGE: 413,
    ErrorCode.SUBMIT_REQUIRED_FIELD_MISSING: 422,
    ErrorCode.METHOD_NOT_ALLOWED: 405,
    ErrorCode.INTERNAL_ERROR: 500,
}

# 우리가 던지지 않은 HTTPException(라우팅 404, 405 등)을 계약 포맷으로 옮길 때 쓴다
CODE_BY_STATUS: dict[int, ErrorCode] = {
    400: ErrorCode.VALIDATION_FAILED,
    401: ErrorCode.TOKEN_INVALID,
    403: ErrorCode.FORBIDDEN_ROLE,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    413: ErrorCode.FILE_TOO_LARGE,
    422: ErrorCode.VALIDATION_FAILED,
}


class FieldError(dict):
    """`{"field": ..., "message": ...}` 한 건."""

    def __init__(self, field: str, message: str):
        super().__init__(field=field, message=message)


class AppError(Exception):
    """계약 §6 의 에러 코드를 그대로 들고 다니는 도메인 예외."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        field_errors: list[dict] | None = None,
        status_code: int | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.field_errors = field_errors
        self.status_code = status_code or STATUS_BY_CODE.get(code, 500)

    def to_payload(self) -> dict:
        payload: dict = {"code": self.code.value, "message": self.message}
        if self.field_errors:
            payload["fieldErrors"] = self.field_errors
        return payload
