from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import FeedbackResult, UserAnswer
from app.schemas.llm import FeedbackResultSchema


class AnswerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_answer(
        self,
        *,
        session_id: int,
        knowledge_point_id: int | None,
        level_id: int,
        answer_type: str,
        answer_text: str | None,
        answer_json: dict | list | None,
    ) -> UserAnswer:
        entity = UserAnswer(
            session_id=session_id,
            knowledge_point_id=knowledge_point_id,
            level_id=level_id,
            answer_type=answer_type,
            answer_text=answer_text,
            answer_json=answer_json,
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def create_feedback(
        self,
        *,
        session_id: int,
        answer_id: int,
        level_id: int | None,
        feedback: FeedbackResultSchema,
    ) -> FeedbackResult:
        entity = FeedbackResult(
            session_id=session_id,
            answer_id=answer_id,
            level_id=level_id,
            result=feedback.result,
            correct_points=feedback.correct_points,
            missing_points=feedback.missing_points,
            feedback=feedback.feedback,
            suggested_review_points=feedback.suggested_review_points,
            result_json=feedback.model_dump(),
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def get_feedback_by_answer_id(self, answer_id: int) -> FeedbackResult | None:
        stmt = select(FeedbackResult).where(FeedbackResult.answer_id == answer_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def level_has_pass_feedback(self, level_id: int) -> bool:
        stmt = (
            select(FeedbackResult.id)
            .where(FeedbackResult.level_id == level_id)
            .where(FeedbackResult.result == "pass")
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def list_answers_by_session(self, session_id: int) -> list[UserAnswer]:
        stmt = (
            select(UserAnswer)
            .where(UserAnswer.session_id == session_id)
            .order_by(UserAnswer.created_at, UserAnswer.id)
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_feedback_by_session(self, session_id: int) -> list[FeedbackResult]:
        stmt = (
            select(FeedbackResult)
            .where(FeedbackResult.session_id == session_id)
            .order_by(FeedbackResult.created_at, FeedbackResult.id)
        )
        return list(self.db.execute(stmt).scalars().all())
