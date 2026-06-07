from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import AsyncTask, LearningSession
from app.repositories.generation_repository import GenerationRepository
from app.repositories.async_task_repository import AsyncTaskRepository
from app.repositories.learning_session_repository import LearningSessionRepository
from app.schemas.cards import LearningCardRead
from app.schemas.practice import PracticeTaskRead
from app.services.learning_card_service import LearningCardError, LearningCardService
from app.services.practice_task_service import PracticeTaskError, PracticeTaskService
from app.schemas.knowledge_points import KnowledgePointRead
from app.schemas.learning_sessions import (
    AsyncTaskRead,
    LearningSessionCreate,
    LearningSessionCreateResponse,
    LearningSessionRead,
    LearningSessionStatusRead,
)
from app.tasks.generation_tasks import generate_learning_session_task
from app.llm.client import LLMConfigurationError, LLMError


router = APIRouter(prefix="/api/learning-sessions", tags=["learning-sessions"])


@router.post("", response_model=LearningSessionCreateResponse)
def create_learning_session(
    payload: LearningSessionCreate,
    db: Session = Depends(get_db),
) -> LearningSessionCreateResponse:
    session_repository = LearningSessionRepository(db)
    task_repository = AsyncTaskRepository(db)

    learning_session = session_repository.create(
        tech_name=payload.tech_name,
        user_level=payload.user_level,
        learning_goal=payload.learning_goal,
    )
    task_id = str(uuid4())
    task_repository.create(
        task_id=task_id,
        session_id=learning_session.id,
        task_type="generate_learning_session",
        status="pending",
        progress=0,
        message="queued",
    )

    try:
        generate_learning_session_task.apply_async(args=[learning_session.id], task_id=task_id)
    except Exception as exc:
        session_repository.set_status(learning_session.id, "failed")
        task_repository.update(
            task_id=task_id,
            status="failed",
            progress=0,
            message="failed_to_enqueue",
            error_message=str(exc),
        )
        raise HTTPException(status_code=503, detail=f"Failed to enqueue generation task: {exc}") from exc

    return LearningSessionCreateResponse(
        session_id=learning_session.id,
        task_id=task_id,
        status="generating",
    )


@router.post("/{session_id}/resume", response_model=LearningSessionCreateResponse)
def resume_learning_session(session_id: int, db: Session = Depends(get_db)) -> LearningSessionCreateResponse:
    session_repository = LearningSessionRepository(db)
    task_repository = AsyncTaskRepository(db)

    learning_session = session_repository.get(session_id)
    if learning_session is None:
        raise HTTPException(status_code=404, detail=f"learning_session not found: {session_id}")

    task_id = str(uuid4())
    task_repository.create(
        task_id=task_id,
        session_id=session_id,
        task_type="generate_learning_session",
        status="pending",
        progress=0,
        message="resume queued",
    )

    try:
        generate_learning_session_task.apply_async(args=[session_id], task_id=task_id)
    except Exception as exc:
        task_repository.update(
            task_id=task_id,
            status="failed",
            progress=0,
            message="failed_to_enqueue",
            error_message=str(exc),
        )
        raise HTTPException(status_code=503, detail=f"Failed to enqueue resume task: {exc}") from exc

    return LearningSessionCreateResponse(
        session_id=session_id,
        task_id=task_id,
        status="generating",
    )


@router.get("/{session_id}", response_model=LearningSessionRead)
def get_learning_session(session_id: int, db: Session = Depends(get_db)) -> LearningSessionRead:
    session_repository = LearningSessionRepository(db)
    task_repository = AsyncTaskRepository(db)
    learning_session = session_repository.get(session_id)
    if learning_session is None:
        raise HTTPException(status_code=404, detail=f"learning_session not found: {session_id}")
    task = task_repository.latest_by_session_id(session_id)
    return _to_session_read(learning_session, task)


@router.get("/{session_id}/status", response_model=LearningSessionStatusRead)
def get_learning_session_status(session_id: int, db: Session = Depends(get_db)) -> LearningSessionStatusRead:
    session_repository = LearningSessionRepository(db)
    task_repository = AsyncTaskRepository(db)
    learning_session = session_repository.get(session_id)
    if learning_session is None:
        raise HTTPException(status_code=404, detail=f"learning_session not found: {session_id}")
    task = task_repository.latest_by_session_id(session_id)
    return LearningSessionStatusRead(
        session_id=learning_session.id,
        status=learning_session.status,
        current_knowledge_point_id=learning_session.current_knowledge_point_id,
        current_level_id=learning_session.current_level_id,
        task=_to_task_read(task) if task is not None else None,
    )


@router.get("/{session_id}/knowledge-points", response_model=list[KnowledgePointRead])
def get_learning_session_knowledge_points(
    session_id: int,
    db: Session = Depends(get_db),
) -> list[KnowledgePointRead]:
    session_repository = LearningSessionRepository(db)
    if session_repository.get(session_id) is None:
        raise HTTPException(status_code=404, detail=f"learning_session not found: {session_id}")
    points = GenerationRepository(db).list_knowledge_points(session_id)
    return [
        KnowledgePointRead(
            id=point.id,
            session_id=point.session_id,
            tech_name=point.tech_name,
            title=point.title,
            goal=point.goal,
            depends_on=point.depends_on or [],
            difficulty=point.difficulty,
            reason=point.reason,
            category=point.category,
            sort_order=point.sort_order,
            created_at=point.created_at,
            updated_at=point.updated_at,
        )
        for point in points
    ]


@router.post("/{session_id}/practice-task", response_model=PracticeTaskRead)
async def generate_practice_task(session_id: int, db: Session = Depends(get_db)) -> PracticeTaskRead:
    try:
        task = await PracticeTaskService(db).generate(session_id)
    except PracticeTaskError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _to_practice_task_read(task)


@router.get("/{session_id}/practice-task", response_model=PracticeTaskRead)
def get_practice_task(session_id: int, db: Session = Depends(get_db)) -> PracticeTaskRead:
    task = PracticeTaskService(db).get_by_session(session_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"practice task not found for session_id: {session_id}")
    return _to_practice_task_read(task)


@router.post("/{session_id}/learning-card", response_model=LearningCardRead)
async def generate_learning_card(session_id: int, db: Session = Depends(get_db)) -> LearningCardRead:
    try:
        card = await LearningCardService(db).generate(session_id)
    except LearningCardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _to_learning_card_read(card)


@router.get("/{session_id}/learning-card", response_model=LearningCardRead)
def get_learning_card(session_id: int, db: Session = Depends(get_db)) -> LearningCardRead:
    card = LearningCardService(db).get_by_session(session_id)
    if card is None:
        raise HTTPException(status_code=404, detail=f"learning card not found for session_id: {session_id}")
    return _to_learning_card_read(card)


def _to_session_read(learning_session: LearningSession, task: AsyncTask | None) -> LearningSessionRead:
    return LearningSessionRead(
        id=learning_session.id,
        tech_name=learning_session.tech_name,
        user_level=learning_session.user_level,
        learning_goal=learning_session.learning_goal,
        status=learning_session.status,
        current_knowledge_point_id=learning_session.current_knowledge_point_id,
        current_level_id=learning_session.current_level_id,
        created_at=learning_session.created_at,
        updated_at=learning_session.updated_at,
        task=_to_task_read(task) if task is not None else None,
    )


def _to_task_read(task: AsyncTask) -> AsyncTaskRead:
    return AsyncTaskRead(
        task_id=task.task_id,
        session_id=task.session_id,
        task_type=task.task_type,
        status=task.status,
        progress=task.progress,
        message=task.message,
        result_json=task.result_json,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _to_practice_task_read(task) -> PracticeTaskRead:
    return PracticeTaskRead(
        id=task.id,
        session_id=task.session_id,
        title=task.title,
        background=task.background or "",
        required_points=task.required_points or [],
        task_requirements=task.task_requirements or [],
        comparison_requirement=task.comparison_requirement or "",
        acceptance_criteria=task.acceptance_criteria or [],
        review_questions=task.review_questions or [],
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _to_learning_card_read(card) -> LearningCardRead:
    return LearningCardRead(
        id=card.id,
        session_id=card.session_id,
        tech_name=card.tech_name,
        pain_point=card.pain_point or "",
        baseline_solution=card.baseline_solution or "",
        target_advantage=card.target_advantage or "",
        when_to_use=card.when_to_use or [],
        when_not_to_use=card.when_not_to_use or [],
        minimal_example=card.minimal_example or "",
        my_understanding=card.my_understanding or "",
        weak_points=card.weak_points or [],
        card_markdown=card.card_markdown,
        created_at=card.created_at,
        updated_at=card.updated_at,
    )
