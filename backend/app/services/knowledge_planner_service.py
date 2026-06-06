from sqlalchemy.orm import Session

from app.llm.client import LLMClient
from app.models.entities import ComparisonResult, KnowledgePoint, OfficialMaterial
from app.repositories.generation_repository import GenerationRepository
from app.schemas.generation import KnowledgePointListSchema
from app.schemas.llm import KnowledgePointSchema


class KnowledgePlanValidationError(ValueError):
    pass


class KnowledgePlannerService:
    ALLOWED_CATEGORIES = {"must_learn", "advanced_later", "skip_now"}

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
        user_level: str | None = None,
        learning_goal: str | None = None,
    ) -> list[KnowledgePoint]:
        existing = self.repository.list_knowledge_points(session_id)
        if existing:
            return existing

        result = await self.llm_client.structured_chat_completion(
            [
                {
                    "role": "user",
                    "content": (
                        "Break the target technology into a controlled learning plan. "
                        "Every item must include title, goal, depends_on, difficulty, reason, and category. "
                        "The category must be one of: must_learn, advanced_later, skip_now. "
                        "Create exactly 5 to 7 must_learn items for the first learning pass. "
                        "Add a small number of advanced_later and skip_now items to make the boundary explicit. "
                        "depends_on must reference titles that exist in your returned list, or be empty. "
                        "Do not add unrelated technologies beyond the comparison boundary.\n\n"
                        f"tech_name: {tech_name}\n"
                        f"user_level: {user_level or 'unspecified'}\n"
                        f"learning_goal: {learning_goal or 'unspecified'}\n\n"
                        f"official_summary:\n{(material.official_summary or '')[:4000]}\n\n"
                        f"official_example:\n{(material.official_example or '')[:2500]}\n\n"
                        f"comparison_task:\n{comparison.comparison_task or ''}\n"
                        f"baseline_solution:\n{comparison.baseline_solution or ''}\n"
                        f"when_to_use:\n{comparison.when_to_use or []}\n"
                        f"when_not_to_use:\n{comparison.when_not_to_use or []}\n"
                    ),
                }
            ],
            KnowledgePointListSchema,
            temperature=0.1,
            max_tokens=4000,
        )
        points = self._normalize_points(result)
        return self.repository.create_knowledge_points(session_id=session_id, tech_name=tech_name, points=points)

    def list_by_session(self, session_id: int) -> list[KnowledgePoint]:
        return self.repository.list_knowledge_points(session_id)

    def _normalize_points(self, result: KnowledgePointListSchema) -> list[KnowledgePointSchema]:
        categorized = [self._normalize_category(point) for point in result.knowledge_points]
        must_learn = [point for point in categorized if point.category == "must_learn"]
        advanced_later = [point for point in categorized if point.category == "advanced_later"]
        skip_now = [point for point in categorized if point.category == "skip_now"]

        if len(must_learn) < 5:
            raise KnowledgePlanValidationError("Knowledge plan must include at least 5 must_learn points.")
        if not advanced_later:
            raise KnowledgePlanValidationError("Knowledge plan must include at least one advanced_later point.")
        if not skip_now:
            raise KnowledgePlanValidationError("Knowledge plan must include at least one skip_now point.")
        must_learn = must_learn[:7]

        ordered = [*must_learn, *advanced_later, *skip_now]
        known_titles = {point.title for point in ordered}
        normalized: list[KnowledgePointSchema] = []
        for point in ordered:
            depends_on = [title for title in point.depends_on if title in known_titles and title != point.title]
            normalized_point = point.model_copy(update={"depends_on": depends_on})
            normalized.append(normalized_point)
        return normalized

    def _normalize_category(self, point: KnowledgePointSchema) -> KnowledgePointSchema:
        category = point.category.strip().lower()
        if category not in self.ALLOWED_CATEGORIES:
            category = "advanced_later"
        return point.model_copy(update={"category": category})
