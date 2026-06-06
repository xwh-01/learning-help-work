from datetime import datetime

from app.schemas.llm import PracticeTaskSchema


class PracticeTaskRead(PracticeTaskSchema):
    id: int
    session_id: int
    created_at: datetime
    updated_at: datetime
