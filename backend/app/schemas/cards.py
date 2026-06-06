from datetime import datetime

from app.schemas.llm import LearningCardSchema


class LearningCardRead(LearningCardSchema):
    id: int
    session_id: int
    card_markdown: str | None = None
    created_at: datetime
    updated_at: datetime
