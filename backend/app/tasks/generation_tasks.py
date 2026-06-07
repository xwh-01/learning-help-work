import asyncio
import json
import logging

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.repositories.async_task_repository import AsyncTaskRepository
from app.repositories.learning_session_repository import LearningSessionRepository
from app.services.comparison_service import ComparisonService
from app.services.knowledge_planner_service import KnowledgePlannerService
from app.services.official_docs_service import OfficialDocsService
from app.tasks.celery_app import celery_app


logger = logging.getLogger(__name__)


@celery_app.task(name="learning_sessions.generate", bind=True)
def generate_learning_session_task(self, session_id: int) -> dict:
    task_id = self.request.id
    db = SessionLocal()
    try:
        return asyncio.run(_generate_learning_session(db, session_id=session_id, task_id=task_id))
    finally:
        db.close()


async def _generate_learning_session(db: Session, *, session_id: int, task_id: str) -> dict:
    session_repository = LearningSessionRepository(db)
    task_repository = AsyncTaskRepository(db)

    learning_session = session_repository.get(session_id)
    if learning_session is None:
        task_repository.update(
            task_id=task_id,
            status="failed",
            progress=0,
            message="learning session not found",
            error_message=f"learning_session does not exist: {session_id}",
        )
        raise ValueError(f"learning_session does not exist: {session_id}")

    errors: list[dict[str, str]] = []
    material = None
    comparison = None
    knowledge_points: list = []

    try:
        session_repository.set_status(session_id, "generating")
    except Exception as exc:
        logger.exception("Failed to set session status for session_id=%s", session_id)
        task_repository.update(task_id=task_id, status="failed", message="failed", error_message=str(exc))
        raise

    _mark_step(task_repository, task_id, 10, "fetch_official_material")
    try:
        material, _cached = await OfficialDocsService(db).fetch_material(
            learning_session.tech_name, session_id=session_id,
        )
    except Exception as exc:
        logger.exception("fetch_official_material failed for session_id=%s", session_id)
        errors.append({"step": "fetch_official_material", "error": str(exc)})

    _mark_step(task_repository, task_id, 30, "generate_comparison")
    if material is not None:
        try:
            comparison = await ComparisonService(db).generate(
                session_id=session_id, tech_name=learning_session.tech_name,
            )
        except Exception as exc:
            logger.exception("generate_comparison failed for session_id=%s", session_id)
            errors.append({"step": "generate_comparison", "error": str(exc)})

    _mark_step(task_repository, task_id, 50, "generate_knowledge_points")
    if comparison is not None:
        try:
            knowledge_points = await KnowledgePlannerService(db).generate(
                session_id=session_id,
                tech_name=learning_session.tech_name,
                material=material,
                comparison=comparison,
                user_level=learning_session.user_level,
                learning_goal=learning_session.learning_goal,
            )
        except Exception as exc:
            logger.exception("generate_knowledge_points failed for session_id=%s", session_id)
            errors.append({"step": "generate_knowledge_points", "error": str(exc)})

    must_learn_points = [point for point in knowledge_points if point.category == "must_learn"]

    first_point_id = must_learn_points[0].id if must_learn_points else None
    session_repository.set_current_position(
        session_id, knowledge_point_id=first_point_id, level_id=None,
    )

    all_ok = material is not None and comparison is not None and len(must_learn_points) > 0
    final_status = "ready" if all_ok else "partial"
    session_repository.set_status(session_id, final_status)

    result = {
        "session_id": session_id,
        "official_material_id": material.id if material else None,
        "comparison_result_id": comparison.id if comparison else None,
        "knowledge_point_count": len(knowledge_points),
        "example_count": 0,
        "level_count": 0,
        "on_demand_generation": True,
        "errors": errors if errors else None,
    }
    task_repository.update(
        task_id=task_id,
        status="completed",
        progress=100,
        message=final_status,
        result_json=result,
        error_message=json.dumps(errors) if errors else None,
    )
    return result


def _mark_step(task_repository: AsyncTaskRepository, task_id: str, progress: int, message: str) -> None:
    task_repository.update(
        task_id=task_id,
        status="running",
        progress=progress,
        message=message,
    )
