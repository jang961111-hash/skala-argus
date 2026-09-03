"""공통 스키마 기반 (CONTRACT §1).

- 필드 표기는 **camelCase**. 파이썬 쪽은 snake_case 로 쓰고 `alias_generator` 가 변환한다.
  `populate_by_name=True` 라 요청 본문은 camelCase·snake_case 둘 다 받는다.
- 시각은 **ISO 8601 + KST 오프셋**. SQLite 는 타임존을 잃어버리므로 naive 값은 UTC 로 보고
  KST 로 변환해 직렬화한다.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer
from pydantic.alias_generators import to_camel

KST = timezone(timedelta(hours=9))


def to_kst(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(KST)


def _iso_kst(value: datetime) -> str:
    return to_kst(value).isoformat()


#: `2026-09-03T10:22:00+09:00`
KstDatetime = Annotated[datetime, PlainSerializer(_iso_kst, return_type=str, when_used="always")]


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ErrorResponse(CamelModel):
    """CONTRACT §1.1 — 모든 4xx·5xx 응답 형태."""

    code: str
    message: str
    field_errors: list[dict] | None = None
