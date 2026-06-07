from datetime import datetime

from pydantic import BaseModel


class LearningLevelRead(BaseModel):
    id: int
    session_id: int
    knowledge_point_id: int
    type: str
    title: str
    scenario: str | None = None
    question: str | None = None
    answer_requirements: list[str]
    task: str | None = None
    hint: str | None = None
    rubric: list[str]
    acceptance_criteria: list[str]
    common_mistakes: list[str]
    reference_answer: str | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime
