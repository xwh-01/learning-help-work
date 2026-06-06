from datetime import datetime

from pydantic import BaseModel


class LearningExampleRead(BaseModel):
    id: int
    session_id: int
    knowledge_point_id: int
    official_example: str | None = None
    beginner_example: str | None = None
    baseline_example: str | None = None
    target_example: str | None = None
    observe_questions: list[str]
    created_at: datetime
    updated_at: datetime
