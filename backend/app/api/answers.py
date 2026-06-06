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
        correct_points=feedback.correct_points or [],
        missing_points=feedback.missing_points or [],
        feedback=feedback.feedback or "",
        suggested_review_points=feedback.suggested_review_points or [],
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
    )
