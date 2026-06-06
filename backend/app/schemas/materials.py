from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.llm import OfficialMaterialSchema


class MaterialFetchRequest(BaseModel):
    tech_name: str = Field(min_length=1, max_length=128)
    force_refresh: bool = False


class OfficialMaterialRead(OfficialMaterialSchema):
    id: int
    cached: bool = False
    created_at: datetime
    raw_json: dict | list | None = None
