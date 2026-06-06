from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.entities import LearningCard
from app.schemas.llm import LearningCardSchema


class CardRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_session_id(self, session_id: int) -> LearningCard | None:
        stmt = (
            select(LearningCard)
            .where(LearningCard.session_id == session_id)
            .order_by(desc(LearningCard.created_at), desc(LearningCard.id))
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, *, session_id: int, card: LearningCardSchema) -> LearningCard:
        entity = LearningCard(
            session_id=session_id,
            tech_name=card.tech_name,
            pain_point=card.pain_point,
            baseline_solution=card.baseline_solution,
            target_advantage=card.target_advantage,
            when_to_use=card.when_to_use,
            when_not_to_use=card.when_not_to_use,
            minimal_example=card.minimal_example,
            my_understanding=card.my_understanding,
            weak_points=card.weak_points,
            card_markdown=self._to_markdown(card),
            result_json=card.model_dump(),
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def _to_markdown(self, card: LearningCardSchema) -> str:
        return "\n\n".join(
            [
                f"# {card.tech_name}",
                f"## Pain Point\n{card.pain_point}",
                f"## Baseline Solution\n{card.baseline_solution}",
                f"## Target Advantage\n{card.target_advantage}",
                "## When To Use\n" + "\n".join(f"- {item}" for item in card.when_to_use),
                "## When Not To Use\n" + "\n".join(f"- {item}" for item in card.when_not_to_use),
                f"## Minimal Example\n{card.minimal_example}",
                f"## My Understanding\n{card.my_understanding}",
                "## Weak Points\n" + "\n".join(f"- {item}" for item in card.weak_points),
            ]
        )
