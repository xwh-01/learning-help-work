from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.answers import FeedbackResultRead
from app.services.feedback_service import FeedbackService


router = APIRouter(prefix="/api/answers", tags=["answers"])


@router.get("/{answer_id}/feedback", response_model=FeedbackResultRead)
def get_answer_feedback(answer_id: int, db: Session = Depends(get_db)) -> FeedbackResultRead:
    feedback = FeedbackService(db).get_by_answer_id(answer_id)
    if feedback is None:
        raise HTTPException(status_code=404, detail=f"feedback not found for answer_id: {answer_id}")
    return FeedbackResultRead(
        id=feedback.id,
        session_id=feedback.session_id,
        answer_id=feedback.answer_id,
        level_id=feedback.level_id,
        result=feedback.result,
        score=(feedback.result_json or {}).get("score", 0) if isinstance(feedback.result_json, dict) else 0,
        passed=(feedback.result_json or {}).get("passed", feedback.result == "pass") if isinstance(feedback.result_json, dict) else feedback.result == "pass",
        strengths=(feedback.result_json or {}).get("strengths", feedback.correct_points or []) if isinstance(feedback.result_json, dict) else feedback.correct_points or [],
        correct_points=feedback.correct_points or [],
        missing_points=feedback.missing_points or [],
        misconception=(feedback.result_json or {}).get("misconception", "") if isinstance(feedback.result_json, dict) else "",
        feedback=feedback.feedback or "",
        improved_answer=(feedback.result_json or {}).get("improved_answer", "") if isinstance(feedback.result_json, dict) else "",
        next_hint=(feedback.result_json or {}).get("next_hint", "") if isinstance(feedback.result_json, dict) else "",
        suggested_review_points=feedback.suggested_review_points or [],
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
    )
