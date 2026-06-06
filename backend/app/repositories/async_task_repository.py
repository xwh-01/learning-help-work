from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.entities import AsyncTask


class AsyncTaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        task_id: str,
        session_id: int | None,
        task_type: str,
        status: str = "pending",
        progress: int = 0,
        message: str | None = None,
    ) -> AsyncTask:
        entity = AsyncTask(
            task_id=task_id,
            session_id=session_id,
            task_type=task_type,
            status=status,
            progress=progress,
            message=message,
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def get_by_task_id(self, task_id: str) -> AsyncTask | None:
        stmt = select(AsyncTask).where(AsyncTask.task_id == task_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def latest_by_session_id(self, session_id: int) -> AsyncTask | None:
        stmt = (
            select(AsyncTask)
            .where(AsyncTask.session_id == session_id)
            .order_by(desc(AsyncTask.created_at), desc(AsyncTask.id))
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def update(
        self,
        *,
        task_id: str,
        status: str | None = None,
        progress: int | None = None,
        message: str | None = None,
        result_json: dict | list | None = None,
        error_message: str | None = None,
    ) -> AsyncTask | None:
        entity = self.get_by_task_id(task_id)
        if entity is None:
            return None
        if status is not None:
            entity.status = status
        if progress is not None:
            entity.progress = progress
        if message is not None:
            entity.message = message
        if result_json is not None:
            entity.result_json = result_json
        if error_message is not None:
            entity.error_message = error_message
        self.db.commit()
        self.db.refresh(entity)
        return entity
