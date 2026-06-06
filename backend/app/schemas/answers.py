from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.llm import FeedbackResultSchema


class UserAnswerCreate(BaseModel):
    answer_text: str = Field(min_length=1)
    answer_type: str = Field(default="text", max_length=32)
    answer_json: dict | list | None = None


class UserAnswerSubmitResponse(BaseModel):
    answer_id: int
    feedback_id: int
    result: str
    next_level_id: int | None = None
    current_level_id: int | None = None
    message: str


class UserAnswerRead(BaseModel):
    id: int
    session_id: int
    knowledge_point_id: int | None = None
    level_id: int
    answer_type: str
    answer_text: str | None = None
    answer_json: dict | list | None = None
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime


class FeedbackResultRead(FeedbackResultSchema):
    id: int
    session_id: int
    answer_id: int
    level_id: int | None = None
    created_at: datetime
    updated_at: datetime
