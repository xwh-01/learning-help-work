from sqlalchemy.orm import Session

from app.llm.client import LLMClient
from app.models.entities import FeedbackResult, KnowledgePoint, LearningLevel, UserAnswer
from app.repositories.answer_repository import AnswerRepository
from app.schemas.llm import FeedbackResultSchema


class FeedbackValidationError(ValueError):
    pass


class FeedbackService:
    ALLOWED_RESULTS = {"pass", "partial", "fail"}

    def __init__(self, db: Session, *, llm_client: LLMClient | None = None) -> None:
        self.db = db
        self.llm_client = llm_client or LLMClient()
        self.repository = AnswerRepository(db)

    async def evaluate(
        self,
        *,
        level: LearningLevel,
        knowledge_point: KnowledgePoint,
        user_answer: UserAnswer,
    ) -> FeedbackResult:
        feedback = await self.llm_client.structured_chat_completion(
            [
                {
                    "role": "user",
                    "content": (
                        "Evaluate the user's answer for this learning level. "
                        "Only judge against the level task, acceptance criteria, common mistakes, and knowledge point. "
                        "Return result as exactly one of: pass, partial, fail. "
                        "Do not decide navigation or the next level.\n\n"
                        f"knowledge_point_title: {knowledge_point.title}\n"
                        f"knowledge_point_goal: {knowledge_point.goal or ''}\n"
                        f"level_type: {level.level_type}\n"
                        f"level_title: {level.title}\n"
                        f"level_task: {level.task or ''}\n"
                        f"acceptance_criteria: {level.acceptance_criteria or []}\n"
                        f"common_mistakes: {level.common_mistakes or []}\n\n"
                        f"user_answer:\n{user_answer.answer_text or user_answer.answer_json or ''}"
                    ),
                }
            ],
            FeedbackResultSchema,
            temperature=0,
            max_tokens=1300,
        )
        feedback = self._validate_feedback(feedback)
        return self.repository.create_feedback(
            session_id=user_answer.session_id,
            answer_id=user_answer.id,
            level_id=level.id,
            feedback=feedback,
        )

    def get_by_answer_id(self, answer_id: int) -> FeedbackResult | None:
        return self.repository.get_feedback_by_answer_id(answer_id)

    def _validate_feedback(self, feedback: FeedbackResultSchema) -> FeedbackResultSchema:
        result = feedback.result.strip().lower()
        if result not in self.ALLOWED_RESULTS:
            raise FeedbackValidationError(f"Unsupported feedback result: {feedback.result}")
        return feedback.model_copy(update={"result": result})
