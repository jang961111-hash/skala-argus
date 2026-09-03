"""이식용 컬럼 타입 (CONTRACT §5 설계 원칙 1·4·5).

- `uuid_pk()` / `uuid_fk()` — 전 테이블 대리키는 UUID v4. PostgreSQL 은 네이티브
  `uuid`, SQLite 는 36자 문자열로 저장된다.
- `JSONB_` — `jsonb 는 구조가 가변인 곳에만`. PostgreSQL 에서는 JSONB, SQLite 에서는 JSON.
- `pg_enum()` — 상태는 PostgreSQL enum(룩업 테이블 아님). SQLite 에서는 VARCHAR + CHECK.
"""
from __future__ import annotations

import uuid
from enum import Enum as PyEnum

from sqlalchemy import JSON, Enum as SAEnum, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import mapped_column

# PostgreSQL 은 jsonb, 그 외(SQLite)는 JSON
JSONB_ = JSON().with_variant(postgresql.JSONB, "postgresql")

# PostgreSQL 은 native uuid, 그 외는 char(36)
UUID_ = String(36).with_variant(postgresql.UUID(as_uuid=False), "postgresql")


def new_uuid() -> str:
    return str(uuid.uuid4())


def uuid_pk():
    return mapped_column(UUID_, primary_key=True, default=new_uuid)


def uuid_fk(target: str, **kwargs):
    from sqlalchemy import ForeignKey

    return mapped_column(UUID_, ForeignKey(target), **kwargs)


def pg_enum(enum_cls: type[PyEnum], name: str) -> SAEnum:
    """PostgreSQL 네이티브 enum / SQLite VARCHAR+CHECK. 값(문자열)을 그대로 저장한다."""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=True,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda e: [m.value for m in e],
    )
