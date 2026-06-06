from sqlalchemy.orm import Session

from app.llm.client import LLMClient
from app.models.entities import LearningCard
from app.repositories.answer_repository import AnswerRepository
from app.repositories.card_repository import CardRepository
from app.repositories.generation_repository import GenerationRepository
from app.repositories.learning_session_repository import LearningSessionRepository
from app.repositories.material_repository import MaterialRepository
from app.repositories.practice_repository import PracticeRepository
from app.schemas.llm import LearningCardSchema


class LearningCardError(ValueError):
    pass


class LearningCardService:
    def __init__(self, db: Session, *, llm_client: LLMClient | None = None) -> None:
        self.db = db
        self.llm_client = llm_client or LLMClient()
        self.session_repository = LearningSessionRepository(db)
        self.material_repository = MaterialRepository(db)
        self.practice_repository = PracticeRepository(db)
        self.generation_repository = GenerationRepository(db)
        self.answer_repository = AnswerRepository(db)
        self.card_repository = CardRepository(db)

    async def generate(self, session_id: int) -> LearningCard:
        existing = self.card_repository.get_by_session_id(session_id)
        if existing is not None:
            return existing

        learning_session = self.session_repository.get(session_id)
        if learning_session is None:
            raise LearningCardError(f"learning_session not found: {session_id}")

        material = self.material_repository.get_latest_by_tech_name(learning_session.tech_name)
        comparison = self.practice_repository.latest_comparison(session_id)
        practice_task = self.practice_repository.get_by_session_id(session_id)
        if material is None:
            raise LearningCardError("Official material is required before generating a learning card.")
        if comparison is None:
            raise LearningCardError("Comparison result is required before generating a learning card.")
        if practice_task is None:
            raise LearningCardError("Practice task is required before generating a learning card.")

        completed_points = [
            point
            for point in self.generation_repository.list_knowledge_points(session_id)
            if point.category == "must_learn"
        ]
        answers = self.answer_repository.list_answers_by_session(session_id)
        feedback_results = self.answer_repository.list_feedback_by_session(session_id)

        card = await self._generate_with_llm(
            tech_name=learning_session.tech_name,
            official_material={
                "summary": material.official_summary,
                "example": material.official_example,
                "source_url": material.source_url,
            },
            comparison_result=comparison.result_json or {},
            completed_knowledge_points=[
                {
                    "title": point.title,
                    "goal": point.goal,
                    "difficulty": point.difficulty,
                }
                for point in completed_points
            ],
            user_answers=[
                {
                    "level_id": answer.level_id,
                    "knowledge_point_id": answer.knowledge_point_id,
                    "answer_text": answer.answer_text,
                }
                for answer in answers[-20:]
            ],
            feedback_results=[
                {
                    "result": feedback.result,
                    "missing_points": feedback.missing_points,
                    "suggested_review_points": feedback.suggested_review_points,
                    "feedback": feedback.feedback,
                }
                for feedback in feedback_results[-20:]
            ],
            practice_task_result=practice_task.result_json or {},
        )
        card = card.model_copy(update={"tech_name": learning_session.tech_name})
        return self.card_repository.create(session_id=session_id, card=card)

    def get_by_session(self, session_id: int) -> LearningCard | None:
        return self.card_repository.get_by_session_id(session_id)

    async def _generate_with_llm(
        self,
        *,
        tech_name: str,
        official_material: dict,
        comparison_result: dict | list,
        completed_knowledge_points: list[dict],
        user_answers: list[dict],
        feedback_results: list[dict],
        practice_task_result: dict | list,
    ) -> LearningCardSchema:
        return await self.llm_client.structured_chat_completion(
            [
                {
                    "role": "user",
                    "content": (
                        "Generate a concise personal learning card for the target technology. "
                        "Ground the card in the official material, comparison, completed knowledge points, "
                        "user answers, feedback, and practice task. "
                        "Do not introduce new unlearned topics. "
                        "weak_points should reflect missing_points, suggested_review_points, and repeated partial/fail feedback.\n\n"
                        f"tech_name: {tech_name}\n"
                        f"official_material: {official_material}\n"
                        f"comparison_result: {comparison_result}\n"
                        f"completed_knowledge_points: {completed_knowledge_points}\n"
                        f"user_answers: {user_answers}\n"
                        f"feedback_results: {feedback_results}\n"
                        f"practice_task_result: {practice_task_result}\n"
                    ),
                }
            ],
            LearningCardSchema,
            temperature=0.1,
            max_tokens=2200,
        )
