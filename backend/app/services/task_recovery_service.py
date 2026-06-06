import json
import logging

from sqlalchemy.orm import Session

from app.repositories.async_task_repository import AsyncTaskRepository
from app.repositories.generation_repository import GenerationRepository
from app.repositories.learning_session_repository import LearningSessionRepository

logger = logging.getLogger(__name__)

LEVEL_TYPES = {"observe", "hands_on", "summary"}


class TaskRecoveryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.task_repository = AsyncTaskRepository(db)
        self.session_repository = LearningSessionRepository(db)
        self.generation_repository = GenerationRepository(db)

    def recover_stale_tasks(self, *, older_than_minutes: int = 30, dry_run: bool = False) -> list[dict]:
        stale_tasks = self.task_repository.list_stale_running(older_than_minutes)
        results: list[dict] = []

        for task in stale_tasks:
            result = self._recover_one(task, dry_run=dry_run)
            results.append(result)

        return results

    def _recover_one(self, task, *, dry_run: bool) -> dict:
        task_id = task.task_id
        session_id = task.session_id

        if session_id is None:
            self._mark(task, "failed", "stale task has no session_id", dry_run)
            return {
                "task_id": task_id,
                "session_id": None,
                "action": "failed",
                "reason": "no session_id",
            }

        learning_session = self.session_repository.get(session_id)
        if learning_session is None:
            self._mark(task, "failed", f"session {session_id} not found", dry_run)
            return {
                "task_id": task_id,
                "session_id": session_id,
                "action": "failed",
                "reason": f"session {session_id} not found",
            }

        products = self._check_products(session_id)

        if products["sufficient"]:
            self._mark(task, "completed", "recovered (products sufficient)", dry_run)
            if not dry_run:
                self.session_repository.set_status(session_id, "ready")
            return {
                "task_id": task_id,
                "session_id": session_id,
                "action": "recovered",
                "details": products,
            }
        else:
            reason = f"products insufficient: {json.dumps(products)}"
            self._mark(task, "failed", reason, dry_run)
            if not dry_run:
                self.session_repository.set_status(session_id, "failed")
            return {
                "task_id": task_id,
                "session_id": session_id,
                "action": "failed",
                "reason": reason,
                "details": products,
            }

    def _check_products(self, session_id: int) -> dict:
        knowledge_points = self.generation_repository.list_knowledge_points(session_id)
        must_learn = [p for p in knowledge_points if p.category == "must_learn"]

        if not must_learn:
            return {
                "sufficient": False,
                "knowledge_point_count": len(knowledge_points),
                "must_learn_count": 0,
                "reason": "no must_learn knowledge points",
            }

        missing_examples: list[str] = []
        missing_levels: list[dict] = []

        for point in must_learn:
            examples = self.generation_repository.list_examples_by_knowledge_point(point.id)
            if not examples:
                missing_examples.append(point.title)

            levels = self.generation_repository.list_levels_by_knowledge_point(point.id)
            existing_types = {level.level_type for level in levels}
            for level_type in LEVEL_TYPES:
                if level_type not in existing_types:
                    missing_levels.append({"knowledge_point": point.title, "missing_type": level_type})

        sufficient = len(missing_examples) == 0 and len(missing_levels) == 0

        return {
            "sufficient": sufficient,
            "must_learn_count": len(must_learn),
            "missing_example_count": len(missing_examples),
            "missing_examples": missing_examples,
            "missing_level_count": len(missing_levels),
            "missing_levels": missing_levels,
        }

    def _mark(self, task, status: str, error_message: str, dry_run: bool) -> None:
        if dry_run:
            return
        self.task_repository.update(
            task_id=task.task_id,
            status=status,
            error_message=error_message,
        )
