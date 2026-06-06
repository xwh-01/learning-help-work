from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.entities import ComparisonResult, LearningSession
from app.schemas.llm import ComparisonResultSchema


class ComparisonRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def learning_session_exists(self, session_id: int) -> bool:
        stmt = select(LearningSession.id).where(LearningSession.id == session_id)
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def create(
        self,
        *,
        session_id: int,
        tech_name: str,
        comparison: ComparisonResultSchema,
    ) -> ComparisonResult:
        entity = ComparisonResult(
            session_id=session_id,
            tech_name=tech_name,
            selected_for_comparison=comparison.selected_for_comparison,
            baseline_solution=comparison.baseline_solution,
            comparison_task=comparison.comparison_task,
            comparison_table=comparison.comparison_table,
            when_to_use=comparison.when_to_use,
            when_not_to_use=comparison.when_not_to_use,
            result_json=comparison.model_dump(),
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def list_by_session_id(self, session_id: int) -> list[ComparisonResult]:
        stmt = (
            select(ComparisonResult)
            .where(ComparisonResult.session_id == session_id)
            .order_by(desc(ComparisonResult.created_at), desc(ComparisonResult.id))
        )
        return list(self.db.execute(stmt).scalars().all())
