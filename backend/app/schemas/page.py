"""페이지네이션 (CONTRACT §1) — `page` 는 0-base, 응답은 `content[]` + `page{}`."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

from app.schemas.base import CamelModel

T = TypeVar("T")


class PageMeta(CamelModel):
    number: int  # 0-base
    size: int
    total_elements: int
    total_pages: int


class Page(BaseModel, Generic[T]):
    content: list[T]
    page: PageMeta


def page_meta(number: int, size: int, total: int) -> dict:
    return {
        "number": number,
        "size": size,
        "totalElements": total,
        "totalPages": (total + size - 1) // size if size else 0,
    }
