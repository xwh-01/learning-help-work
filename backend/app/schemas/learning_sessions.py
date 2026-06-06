from datetime import datetime

from pydantic import BaseModel, Field


class LearningSessionCreate(BaseModel):
    tech_name: str = Field(min_length=1, max_length=128)
    user_level: str | None = Field(default=None, max_length=64)
    learning_goal: str | None = None


class LearningSessionCreateResponse(BaseModel):
    session_id: int
    task_id: str
    status: str


class AsyncTaskRead(BaseModel):
    task_id: str
    session_id: int | None = None
    task_type: str
    status: str
    progress: int
    message: str | None = None
    result_json: dict | list | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class LearningSessionRead(BaseModel):
    id: int
    tech_name: str
    user_level: str | None = None
    learning_goal: str | None = None
    status: str
    current_knowledge_point_id: int | None = None
    current_level_id: int | None = None
    created_at: datetime
    updated_at: datetime
    task: AsyncTaskRead | None = None


class LearningSessionStatusRead(BaseModel):
    session_id: int
    status: str
    current_knowledge_point_id: int | None = None
    current_level_id: int | None = None
    task: AsyncTaskRead | None = None
