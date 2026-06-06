from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.entities import ComparisonResult, LearningExample, PracticeTask
from app.schemas.llm import PracticeTaskSchema


class PracticeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def latest_comparison(self, session_id: int) -> ComparisonResult | None:
        stmt = (
            select(ComparisonResult)
            .where(ComparisonResult.session_id == session_id)
            .order_by(desc(ComparisonResult.created_at), desc(ComparisonResult.id))
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def key_examples(self, session_id: int, limit: int = 7) -> list[LearningExample]:
        stmt = (
            select(LearningExample)
            .where(LearningExample.session_id == session_id)
            .order_by(LearningExample.knowledge_point_id, LearningExample.id)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_session_id(self, session_id: int) -> PracticeTask | None:
        stmt = (
            select(PracticeTask)
            .where(PracticeTask.session_id == session_id)
            .order_by(desc(PracticeTask.created_at), desc(PracticeTask.id))
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, *, session_id: int, task: PracticeTaskSchema) -> PracticeTask:
        entity = PracticeTask(
            session_id=session_id,
            title=task.title,
            background=task.background,
            required_points=task.required_points,
            task_requirements=task.task_requirements,
            comparison_requirement=task.comparison_requirement,
            acceptance_criteria=task.acceptance_criteria,
            review_questions=task.review_questions,
            result_json=task.model_dump(),
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
