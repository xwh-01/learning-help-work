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
                        "Only judge against the level question, rubric, acceptance criteria, common mistakes, and knowledge point. "
                        "Return result as exactly one of: pass, partial, fail. "
                        "Do not decide navigation or the next level. "
                        "Return score from 0 to 100 and passed as true only when score >= 70. "
                        "Write strengths, missing_points, misconception, improved_answer, next_hint, correct_points, feedback, and suggested_review_points in Chinese. "
                        "For compare levels, score whether the learner understands baseline vs target differences. "
                        "For practice levels, score whether the learner can apply the technology to the scenario. "
                        "For reflect levels, score whether the learner explains pain point, use boundary, and non-use boundary. "
                        "Keep technology names, API names, class names, function names, commands, and code keywords in English.\n\n"
                        f"knowledge_point_title: {knowledge_point.title}\n"
                        f"knowledge_point_goal: {knowledge_point.goal or ''}\n"
                        f"level_type: {level.level_type}\n"
                        f"level_title: {level.title}\n"
                        f"scenario: {level.scenario or ''}\n"
                        f"question: {level.question or ''}\n"
                        f"answer_requirements: {level.answer_requirements or []}\n"
                        f"rubric: {level.rubric or []}\n"
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
        score = max(0, min(100, int(feedback.score)))
        passed = bool(feedback.passed) if feedback.passed is not None else score >= 70
        if result not in self.ALLOWED_RESULTS:
            result = "pass" if passed else "partial" if score >= 45 else "fail"
        if passed and result != "pass":
            result = "pass"
        if not passed and result == "pass":
            result = "partial" if score >= 45 else "fail"
        return feedback.model_copy(update={"result": result, "score": score, "passed": passed})
