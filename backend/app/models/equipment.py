from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Equipment(Base):
    __tablename__ = "equipments"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"))
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(32))  # GAS_CABINET | VALVE | PIPING | SCRUBBER ...
    line: Mapped[str | None] = mapped_column(String(50), nullable=True)
    substances: Mapped[list] = mapped_column(JSON, default=list)


class Part(Base):
    __tablename__ = "parts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"))
    part_no: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    spec: Mapped[dict] = mapped_column(JSON, default=dict)
    grade: Mapped[str] = mapped_column(String(16))  # OEM | EQUIVALENT | REFURB
    toxic_gas_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    stock: Mapped[int] = mapped_column(Integer, default=0)


class EquipmentPart(Base):
    __tablename__ = "equipment_parts"
    equipment_id: Mapped[str] = mapped_column(ForeignKey("equipments.id"), primary_key=True)
    part_id: Mapped[str] = mapped_column(ForeignKey("parts.id"), primary_key=True)
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_replaced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PartCompatibility(Base):
    __tablename__ = "part_compatibility"
    part_id: Mapped[str] = mapped_column(ForeignKey("parts.id"), primary_key=True)
    alt_part_id: Mapped[str] = mapped_column(ForeignKey("parts.id"), primary_key=True)
    diff: Mapped[str | None] = mapped_column(String(500), nullable=True)
    allowed_for_toxic_gas: Mapped[bool] = mapped_column(Boolean, default=False)
