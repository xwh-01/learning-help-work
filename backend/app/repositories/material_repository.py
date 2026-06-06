from datetime import datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.entities import OfficialMaterial
from app.schemas.llm import OfficialMaterialSchema


class MaterialRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_latest_by_tech_name(self, tech_name: str) -> OfficialMaterial | None:
        stmt = (
            select(OfficialMaterial)
            .where(OfficialMaterial.tech_name == tech_name)
            .order_by(desc(OfficialMaterial.created_at), desc(OfficialMaterial.id))
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_fresh_by_tech_name(self, tech_name: str, ttl_hours: int) -> OfficialMaterial | None:
        cutoff = datetime.utcnow() - timedelta(hours=ttl_hours)
        stmt = (
            select(OfficialMaterial)
            .where(OfficialMaterial.tech_name == tech_name)
            .where(OfficialMaterial.created_at >= cutoff)
            .order_by(desc(OfficialMaterial.created_at), desc(OfficialMaterial.id))
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(
        self,
        *,
        material: OfficialMaterialSchema,
        raw_json: dict,
        session_id: int | None = None,
    ) -> OfficialMaterial:
        entity = OfficialMaterial(
            session_id=session_id,
            tech_name=material.tech_name,
            source_url=material.source_url,
            official_summary=material.official_summary,
            official_example=material.official_example,
            chunks_json=material.chunks,
            raw_json=raw_json,
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
