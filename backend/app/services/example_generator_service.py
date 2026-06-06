import logging

from sqlalchemy.orm import Session

from app.llm.client import LLMClient
from app.models.entities import ComparisonResult, KnowledgePoint, LearningExample, OfficialMaterial
from app.repositories.generation_repository import GenerationRepository
from app.schemas.llm import LearningExampleSchema


logger = logging.getLogger(__name__)


class ExampleValidationError(ValueError):
    pass


class ExampleGeneratorService:
    def __init__(self, db: Session, *, llm_client: LLMClient | None = None) -> None:
        self.db = db
        self.llm_client = llm_client or LLMClient()
        self.repository = GenerationRepository(db)

    async def generate(
        self,
        *,
        session_id: int,
        tech_name: str,
        material: OfficialMaterial,
        comparison: ComparisonResult,
        knowledge_points: list[KnowledgePoint],
        user_level: str | None = None,
    ) -> list[LearningExample]:
        all_existing: list[LearningExample] = []
        for point in knowledge_points:
            all_existing.extend(self.repository.list_examples_by_knowledge_point(point.id))
        if all_existing:
            return all_existing

        examples: list[LearningExample] = []
        errors: list[dict] = []
        for point in knowledge_points:
            if point.category != "must_learn":
                continue
            try:
                example = await self.generate_for_point(
                    tech_name=tech_name,
                    knowledge_point=point,
                    material=material,
                    comparison=comparison,
                    user_level=user_level,
                )
                examples.append(
                    self.repository.create_example(
                        session_id=session_id,
                        knowledge_point_id=point.id,
                        example=example,
                    )
                )
            except Exception as exc:
                logger.error("Example generation failed for point %s: %s", point.title, exc)
                errors.append({"knowledge_point": point.title, "error": str(exc)})
        if errors:
            logger.warning("Example generation completed with %s/%s points failed", len(errors), len(knowledge_points))
            if not examples and knowledge_points:
                raise ExampleValidationError(f"All example generations failed: {errors}")
        return examples

    async def generate_for_point(
        self,
        *,
        tech_name: str,
        knowledge_point: KnowledgePoint,
        material: OfficialMaterial,
        comparison: ComparisonResult,
        user_level: str | None = None,
    ) -> LearningExampleSchema:
        example = await self.llm_client.structured_chat_completion(
            [
                {
                    "role": "user",
                    "content": (
                        "Generate one compact body-feel learning example for exactly one must_learn knowledge point. "
                        "Keep code short and focused on the current knowledge point. "
                        "Do not introduce later advanced concepts, extra frameworks, or unrelated tools. "
                        "baseline_example must show the ordinary baseline way. "
                        "target_example must show the target technology way. "
                        "official_example should be grounded in the official material when possible.\n\n"
                        f"tech_name: {tech_name}\n"
                        f"user_level: {user_level or 'unspecified'}\n"
                        f"knowledge_point_title: {knowledge_point.title}\n"
                        f"knowledge_point_goal: {knowledge_point.goal or ''}\n"
                        f"knowledge_point_difficulty: {knowledge_point.difficulty or ''}\n"
                        f"knowledge_point_reason: {knowledge_point.reason or ''}\n\n"
                        f"comparison_task:\n{comparison.comparison_task or ''}\n"
                        f"baseline_solution:\n{comparison.baseline_solution or ''}\n"
                        f"selected_for_comparison:\n{comparison.selected_for_comparison or []}\n\n"
                        f"official_summary:\n{(material.official_summary or '')[:2500]}\n\n"
                        f"official_example:\n{(material.official_example or '')[:2500]}\n"
                    ),
                }
            ],
            LearningExampleSchema,
            temperature=0.1,
            max_tokens=1600,
        )
        return self._validate_example(example, knowledge_point)

    def list_by_knowledge_point(self, knowledge_point_id: int) -> list[LearningExample]:
        return self.repository.list_examples_by_knowledge_point(knowledge_point_id)

    def _validate_example(
        self,
        example: LearningExampleSchema,
        knowledge_point: KnowledgePoint,
    ) -> LearningExampleSchema:
        if example.knowledge_point_title != knowledge_point.title:
            example = example.model_copy(update={"knowledge_point_title": knowledge_point.title})
        required_fields = {
            "official_example": example.official_example,
            "beginner_example": example.beginner_example,
            "baseline_example": example.baseline_example,
            "target_example": example.target_example,
        }
        missing = [name for name, value in required_fields.items() if not value.strip()]
        if missing:
            raise ExampleValidationError(f"Learning example missing fields: {', '.join(missing)}")
        if not example.observe_questions:
            example = example.model_copy(
                update={
                    "observe_questions": [
                        "What concrete difference do you notice between the baseline example and the target technology example?"
                    ]
                }
            )
        return example
