from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.entities import LearningSession


class LearningSessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, tech_name: str, user_level: str | None, learning_goal: str | None) -> LearningSession:
        entity = LearningSession(
            tech_name=tech_name,
            user_level=user_level,
            learning_goal=learning_goal,
            status="generating",
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def get(self, session_id: int) -> LearningSession | None:
        stmt = select(LearningSession).where(LearningSession.id == session_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_recent(self, *, limit: int = 20) -> list[LearningSession]:
        stmt = select(LearningSession).order_by(desc(LearningSession.created_at), desc(LearningSession.id)).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def set_status(self, session_id: int, status: str) -> None:
        session = self.get(session_id)
        if session is None:
            return
        session.status = status
        self.db.commit()

    def set_current_position(
        self,
        session_id: int,
        *,
        knowledge_point_id: int | None,
        level_id: int | None,
    ) -> None:
        session = self.get(session_id)
        if session is None:
            return
        session.current_knowledge_point_id = knowledge_point_id
        session.current_level_id = level_id
        self.db.commit()

    def latest_by_tech_name(self, tech_name: str) -> LearningSession | None:
        stmt = (
            select(LearningSession)
            .where(LearningSession.tech_name == tech_name)
            .order_by(desc(LearningSession.created_at), desc(LearningSession.id))
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()
