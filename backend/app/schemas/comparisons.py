from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.llm import ComparisonResultSchema


class ComparisonGenerateRequest(BaseModel):
    session_id: int
    tech_name: str = Field(min_length=1, max_length=128)


class ComparisonResultRead(ComparisonResultSchema):
    id: int
    session_id: int
    tech_name: str
    created_at: datetime
