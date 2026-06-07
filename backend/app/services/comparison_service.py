import logging

from sqlalchemy.orm import Session

from app.llm.client import LLMClient
from app.models.entities import ComparisonResult
from app.repositories.comparison_repository import ComparisonRepository
from app.repositories.material_repository import MaterialRepository
from app.schemas.llm import ComparisonResultSchema
from app.services.tech_relation_service import TechRelationService


logger = logging.getLogger(__name__)


class ComparisonInputError(ValueError):
    pass


class ComparisonService:
    def __init__(
        self,
        db: Session,
        *,
        llm_client: LLMClient | None = None,
        relation_service: TechRelationService | None = None,
    ) -> None:
        self.db = db
        self.llm_client = llm_client or LLMClient()
        self.relation_service = relation_service or TechRelationService()
        self.material_repository = MaterialRepository(db)
        self.comparison_repository = ComparisonRepository(db)

    async def generate(self, *, session_id: int, tech_name: str) -> ComparisonResult:
        existing = self.comparison_repository.list_by_session_id(session_id)
        if existing:
            return existing[0]

        relation = self.relation_service.get_relation(tech_name)
        if not relation.baseline:
            raise ComparisonInputError(f"Tech relation for {relation.tech_name} must include a baseline.")
        if not self.comparison_repository.learning_session_exists(session_id):
            raise ComparisonInputError(f"learning_session does not exist: {session_id}")

        material = self.material_repository.get_latest_by_tech_name(relation.tech_name)
        if material is None:
            raise ComparisonInputError(
                f"No official material found for {relation.tech_name}. Fetch official material first."
            )

        baseline = relation.baseline[0]
        selected = [baseline, relation.tech_name]
        if relation.similar:
            selected.append(relation.similar[0])
        selected = selected[:3]

        skipped_candidates = [
            *relation.similar[max(0, len(selected) - 2) :],
            *relation.skip_now,
        ]

        comparison = await self._generate_with_llm(
            tech_name=relation.tech_name,
            baseline=baseline,
            selected=selected,
            skipped_candidates=skipped_candidates,
            official_summary=material.official_summary or "",
            official_example=material.official_example or "",
            source_url=material.source_url or "",
        )
        comparison = self._enforce_boundaries(
            comparison,
            tech_name=relation.tech_name,
            selected=selected,
            skipped_candidates=skipped_candidates,
        )
        return self.comparison_repository.create(
            session_id=session_id,
            tech_name=relation.tech_name,
            comparison=comparison,
        )

    def list_by_session(self, session_id: int) -> list[ComparisonResult]:
        return self.comparison_repository.list_by_session_id(session_id)

    async def _generate_with_llm(
        self,
        *,
        tech_name: str,
        baseline: str,
        selected: list[str],
        skipped_candidates: list[str],
        official_summary: str,
        official_example: str,
        source_url: str,
    ) -> ComparisonResultSchema:
        messages = [
            {
                "role": "user",
                "content": (
                    "Generate a controlled technical boundary comparison for a learning workflow.\n"
                    "Compare around one small practical task, not a broad feature list.\n"
                    "You must include the ordinary baseline solution and the target technology.\n"
                    "You may only compare the technologies in selected_for_comparison. Do not add unrelated tools.\n"
                    "Use skipped_candidates only to explain what is intentionally not expanded now.\n"
                    "Write baseline_solution, comparison_task, comparison_table values, when_to_use, when_not_to_use, "
                    "and skipped_candidates explanations in Chinese. Keep technology names and API names in English.\n\n"
                    f"target_tech: {tech_name}\n"
                    f"ordinary_baseline: {baseline}\n"
                    f"selected_for_comparison: {selected}\n"
                    f"skipped_candidates: {skipped_candidates}\n"
                    f"official_source_url: {source_url}\n\n"
                    f"official_summary:\n{official_summary[:4000]}\n\n"
                    f"official_example:\n{official_example[:3000]}\n\n"
                    "Output fields must include target_tech, selected_for_comparison, baseline_solution, "
                    "comparison_task, comparison_table, when_to_use, when_not_to_use, skipped_candidates."
                ),
            }
        ]
        return await self.llm_client.structured_chat_completion(
            messages,
            ComparisonResultSchema,
            temperature=0.1,
            max_tokens=2200,
        )

    def _enforce_boundaries(
        self,
        comparison: ComparisonResultSchema,
        *,
        tech_name: str,
        selected: list[str],
        skipped_candidates: list[str],
    ) -> ComparisonResultSchema:
        return comparison.model_copy(
            update={
                "target_tech": tech_name,
                "selected_for_comparison": selected,
                "skipped_candidates": skipped_candidates,
            }
        )
