from __future__ import annotations

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class LawIndex(Base):
    """법제처 API에서 사전 적재된 법령 원문 인덱스 (사내 보관, 외부 전송 없음)."""

    __tablename__ = "law_index"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    law: Mapped[str] = mapped_column(String(200), index=True)
    article: Mapped[str] = mapped_column(String(50))
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    effective_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Search helpers: which equipment types / substances this article applies to
    equipment_types: Mapped[list] = mapped_column(JSON, default=list)
    substances: Mapped[list] = mapped_column(JSON, default=list)
