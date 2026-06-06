from datetime import datetime

from pydantic import BaseModel


class LearningLevelRead(BaseModel):
    id: int
    session_id: int
    knowledge_point_id: int
    type: str
    title: str
    task: str | None = None
    hint: str | None = None
    acceptance_criteria: list[str]
    common_mistakes: list[str]
    sort_order: int
    created_at: datetime
    updated_at: datetime
