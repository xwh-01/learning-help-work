from sqlalchemy.orm import Session

from app.llm.client import LLMClient
from app.models.entities import PracticeTask
from app.repositories.answer_repository import AnswerRepository
from app.repositories.generation_repository import GenerationRepository
from app.repositories.learning_session_repository import LearningSessionRepository
from app.repositories.practice_repository import PracticeRepository
from app.schemas.llm import PracticeTaskSchema


class PracticeTaskError(ValueError):
    pass


class PracticeTaskService:
    def __init__(self, db: Session, *, llm_client: LLMClient | None = None) -> None:
        self.db = db
        self.llm_client = llm_client or LLMClient()
        self.session_repository = LearningSessionRepository(db)
        self.generation_repository = GenerationRepository(db)
        self.answer_repository = AnswerRepository(db)
        self.practice_repository = PracticeRepository(db)

    async def generate(self, session_id: int) -> PracticeTask:
        existing = self.practice_repository.get_by_session_id(session_id)
        if existing is not None:
            return existing

        learning_session = self.session_repository.get(session_id)
        if learning_session is None:
            raise PracticeTaskError(f"learning_session not found: {session_id}")

        must_learn_points = [
            point
            for point in self.generation_repository.list_knowledge_points(session_id)
            if point.category == "must_learn"
        ]
        if not must_learn_points:
            raise PracticeTaskError("No must_learn knowledge points found.")

        if not self._all_must_learn_levels_passed(session_id):
            raise PracticeTaskError("Practice task can be generated only after all must_learn levels are passed.")

        comparison = self.practice_repository.latest_comparison(session_id)
        if comparison is None:
            raise PracticeTaskError("No comparison result found for this session.")

        examples = self.practice_repository.key_examples(session_id)
        task = await self._generate_with_llm(
            target_tech=learning_session.tech_name,
            completed_knowledge_points=[point.title for point in must_learn_points],
            comparison_result=comparison.result_json or {},
            key_examples=[
                {
                    "knowledge_point_id": example.knowledge_point_id,
                    "baseline_example": example.baseline_example,
                    "target_example": example.target_example,
                }
                for example in examples
            ],
        )
        task = self._enforce_boundaries(task, [point.title for point in must_learn_points])
        return self.practice_repository.create(session_id=session_id, task=task)

    def get_by_session(self, session_id: int) -> PracticeTask | None:
        return self.practice_repository.get_by_session_id(session_id)

    async def _generate_with_llm(
        self,
        *,
        target_tech: str,
        completed_knowledge_points: list[str],
        comparison_result: dict | list,
        key_examples: list[dict],
    ) -> PracticeTaskSchema:
        return await self.llm_client.structured_chat_completion(
            [
                {
                    "role": "user",
                    "content": (
                        "Generate one practical Boss task for a learner who has completed the listed knowledge points. "
                        "The task must require comparing an ordinary baseline solution with the target technology solution. "
                        "Do not introduce any knowledge point that is not in completed_knowledge_points. "
                        "Keep the task small enough for a focused learning exercise.\n\n"
                        "Language and format requirements:\n"
                        "- Write title, background, required_points, task_requirements, comparison_requirement, acceptance_criteria, and review_questions in Chinese.\n"
                        "- Use a Chinese technical exercise format: 背景, 任务, 要求, 提交内容, 验收标准.\n"
                        "- Keep technology names, API names, class names, function names, commands, and code keywords in English.\n\n"
                        f"target_tech: {target_tech}\n"
                        f"completed_knowledge_points: {completed_knowledge_points}\n"
                        f"comparison_result: {comparison_result}\n"
                        f"key_examples: {key_examples}\n"
                    ),
                }
            ],
            PracticeTaskSchema,
            temperature=0.1,
            max_tokens=2000,
        )

    def _all_must_learn_levels_passed(self, session_id: int) -> bool:
        must_learn_point_ids = {
            point.id
            for point in self.generation_repository.list_knowledge_points(session_id)
            if point.category == "must_learn"
        }
        levels = [
            level
            for point_id in must_learn_point_ids
            for level in self.generation_repository.list_levels_by_knowledge_point(point_id)
        ]
        if not levels:
            return False

        for level in levels:
            if not self.answer_repository.level_has_pass_feedback(level.id):
                return False
        return True

    def _enforce_boundaries(
        self,
        task: PracticeTaskSchema,
        completed_knowledge_points: list[str],
    ) -> PracticeTaskSchema:
        if not task.comparison_requirement.strip():
            raise PracticeTaskError("Practice task must include comparison_requirement.")
        return task.model_copy(update={"required_points": completed_knowledge_points})
