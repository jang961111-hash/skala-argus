from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import AiConfig, Equipment, LawIndex, Part, PartCompatibility, Tenant, User


class MasterRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- equipments / parts -------------------------------------------------
    def list_equipments(self) -> list[Equipment]:
        return list(self.db.scalars(select(Equipment).order_by(Equipment.id)).all())

    def get_equipment(self, eq_id: str) -> Equipment | None:
        return self.db.get(Equipment, eq_id)

    def list_parts(self) -> list[Part]:
        return list(self.db.scalars(select(Part).order_by(Part.id)).all())

    def get_part(self, part_id: str) -> Part | None:
        return self.db.get(Part, part_id)

    def alternatives(self, part_id: str) -> list[tuple[PartCompatibility, Part]]:
        rows = self.db.execute(
            select(PartCompatibility, Part)
            .join(Part, Part.id == PartCompatibility.alt_part_id)
            .where(PartCompatibility.part_id == part_id)
        ).all()
        return [(pc, p) for pc, p in rows]

    # --- users / tenants ----------------------------------------------------
    def get_user(self, user_id: str) -> User | None:
        return self.db.get(User, user_id)

    def get_tenant(self, tenant_id: str) -> Tenant | None:
        return self.db.get(Tenant, tenant_id)

    # --- law_index ----------------------------------------------------------
    def search_laws(self, q: str | None, equipment_type: str | None, substance: str | None) -> list[LawIndex]:
        stmt = select(LawIndex)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                or_(LawIndex.law.like(like), LawIndex.article.like(like), LawIndex.title.like(like), LawIndex.text.like(like))
            )
        rows = list(self.db.scalars(stmt.order_by(LawIndex.id)).all())
        # JSON containment done in Python for SQLite/PG portability (small index)
        if equipment_type:
            rows = [r for r in rows if not r.equipment_types or equipment_type in r.equipment_types]
        if substance:
            rows = [r for r in rows if not r.substances or substance in r.substances]
        return rows

    # --- ai_configs ---------------------------------------------------------
    def list_ai_configs(self, tenant_id: str) -> list[AiConfig]:
        return list(
            self.db.scalars(select(AiConfig).where(AiConfig.tenant_id == tenant_id).order_by(AiConfig.agent_type)).all()
        )

    def get_ai_config(self, tenant_id: str, agent_type: str) -> AiConfig | None:
        return self.db.get(AiConfig, (tenant_id, agent_type))

    def upsert_ai_config(self, tenant_id: str, agent_type: str, **values) -> AiConfig:
        cfg = self.db.get(AiConfig, (tenant_id, agent_type))
        if cfg is None:
            cfg = AiConfig(tenant_id=tenant_id, agent_type=agent_type)
            self.db.add(cfg)
        for k, v in values.items():
            setattr(cfg, k, v)
        self.db.flush()
        return cfg
