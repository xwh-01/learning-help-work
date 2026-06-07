from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.llm.client import LLMConfigurationError, LLMError
from app.repositories.answer_repository import AnswerRepository
from app.repositories.generation_repository import GenerationRepository
from app.repositories.learning_session_repository import LearningSessionRepository
from app.schemas.answers import UserAnswerCreate, UserAnswerSubmitResponse
from app.schemas.levels import LearningLevelRead
from app.services.feedback_service import FeedbackService, FeedbackValidationError
from app.services.level_generator_service import LevelGeneratorService


router = APIRouter(prefix="/api/levels", tags=["levels"])


@router.get("/{level_id}", response_model=LearningLevelRead)
def get_level(level_id: int, db: Session = Depends(get_db)) -> LearningLevelRead:
    level = LevelGeneratorService(db).get_level(level_id)
    if level is None:
        raise HTTPException(status_code=404, detail=f"level not found: {level_id}")
    return LearningLevelRead(
        id=level.id,
        session_id=level.session_id,
        knowledge_point_id=level.knowledge_point_id,
        type=level.level_type,
        title=level.title,
        scenario=level.scenario,
        question=level.question,
        answer_requirements=level.answer_requirements or [],
        task=level.task,
        hint=level.hint,
        rubric=level.rubric or [],
        acceptance_criteria=level.acceptance_criteria or [],
        common_mistakes=level.common_mistakes or [],
        reference_answer=level.reference_answer,
        sort_order=level.sort_order,
        created_at=level.created_at,
        updated_at=level.updated_at,
    )


@router.post("/{level_id}/answers", response_model=UserAnswerSubmitResponse)
async def submit_level_answer(
    level_id: int,
    payload: UserAnswerCreate,
    db: Session = Depends(get_db),
) -> UserAnswerSubmitResponse:
    generation_repository = GenerationRepository(db)
    level = generation_repository.get_level(level_id)
    if level is None:
        raise HTTPException(status_code=404, detail=f"level not found: {level_id}")

    knowledge_point = generation_repository.get_knowledge_point(level.knowledge_point_id)
    if knowledge_point is None:
        raise HTTPException(status_code=404, detail=f"knowledge point not found: {level.knowledge_point_id}")

    answer_repository = AnswerRepository(db)
    user_answer = answer_repository.create_answer(
        session_id=level.session_id,
        knowledge_point_id=level.knowledge_point_id,
        level_id=level.id,
        answer_type=payload.answer_type,
        answer_text=payload.answer_text,
        answer_json=payload.answer_json,
    )

    try:
        feedback = await FeedbackService(db).evaluate(
            level=level,
            knowledge_point=knowledge_point,
            user_answer=user_answer,
        )
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (FeedbackValidationError, LLMError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    next_level_id = _apply_progress_rule(db, level, feedback.result)
    return UserAnswerSubmitResponse(
        answer_id=user_answer.id,
        feedback_id=feedback.id,
        result=feedback.result,
        next_level_id=next_level_id,
        current_level_id=level.id if feedback.result != "pass" else next_level_id,
        message=_progress_message(feedback.result),
    )


def _apply_progress_rule(db: Session, level, result: str) -> int | None:
    session_repository = LearningSessionRepository(db)
    generation_repository = GenerationRepository(db)

    if result == "pass":
        next_level = generation_repository.get_next_level(level)
        if next_level is None:
            session_repository.set_current_position(
                level.session_id,
                knowledge_point_id=level.knowledge_point_id,
                level_id=None,
            )
            session_repository.set_status(level.session_id, "levels_completed")
            return None
        session_repository.set_current_position(
            level.session_id,
            knowledge_point_id=next_level.knowledge_point_id,
            level_id=next_level.id,
        )
        return next_level.id

    session_repository.set_current_position(
        level.session_id,
        knowledge_point_id=level.knowledge_point_id,
        level_id=level.id,
    )
    return level.id


def _progress_message(result: str) -> str:
    if result == "pass":
        return "Passed. Move to the next level."
    if result == "partial":
        return "Partial. Retry the current level."
    return "Failed. Review the current knowledge point examples before retrying."
