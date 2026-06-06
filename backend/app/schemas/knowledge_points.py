from datetime import datetime

from pydantic import BaseModel


class KnowledgePointRead(BaseModel):
    id: int
    session_id: int
    tech_name: str
    title: str
    goal: str | None = None
    depends_on: list[str]
    difficulty: str | None = None
    reason: str | None = None
    category: str | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime
