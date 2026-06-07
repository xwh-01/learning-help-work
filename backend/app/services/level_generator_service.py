from pathlib import Path

import logging
import yaml
from sqlalchemy.orm import Session

from app.llm.client import LLMClient
from app.models.entities import KnowledgePoint, LearningLevel
from app.repositories.generation_repository import GenerationRepository
from app.schemas.llm import LearningLevelSchema


logger = logging.getLogger(__name__)


class LevelValidationError(ValueError):
    pass


class LevelGeneratorService:
    LEVEL_TYPES = ["observe", "hands_on", "summary"]

    def __init__(
        self,
        db: Session,
        *,
        llm_client: LLMClient | None = None,
        templates_path: Path | None = None,
    ) -> None:
        self.db = db
        self.llm_client = llm_client or LLMClient()
        self.repository = GenerationRepository(db)
        self.templates_path = templates_path or Path(__file__).resolve().parents[1] / "data" / "level_templates.yaml"

    async def generate(
        self,
        *,
        session_id: int,
        tech_name: str,
        knowledge_points: list[KnowledgePoint],
    ) -> list[LearningLevel]:
        existing_by_point: dict[int, set[str]] = {}
        for point in knowledge_points:
            existing = self.repository.list_levels_by_knowledge_point(point.id)
            existing_by_point[point.id] = {level.level_type for level in existing}

        all_types = set(self.LEVEL_TYPES)
        all_complete = all(
            existing_by_point.get(point.id, set()) >= all_types
            for point in knowledge_points
        )
        if all_complete:
            all_entities: list[LearningLevel] = []
            for point in knowledge_points:
                all_entities.extend(self.repository.list_levels_by_knowledge_point(point.id))
            return all_entities

        levels: list[LearningLevel] = []
        errors: list[dict] = []
        for point in knowledge_points:
            if point.category != "must_learn":
                continue
            existing_types = existing_by_point.get(point.id, set())
            if existing_types:
                levels.extend(self.repository.list_levels_by_knowledge_point(point.id))
            for sort_order, level_type in enumerate(self.LEVEL_TYPES, start=1):
                if level_type in existing_types:
                    continue
                try:
                    level = await self.generate_for_point(
                        tech_name=tech_name,
                        knowledge_point=point,
                        level_type=level_type,
                    )
                    levels.append(
                        self.repository.create_level(
                            session_id=session_id,
                            knowledge_point_id=point.id,
                            level=level,
                            sort_order=sort_order,
                        )
                    )
                except Exception as exc:
                    logger.error("Level generation failed for point %s type %s: %s", point.title, level_type, exc)
                    errors.append({"knowledge_point": point.title, "level_type": level_type, "error": str(exc)})
        if errors:
            logger.warning("Level generation completed with %s failures", len(errors))
            if not levels and knowledge_points:
                raise LevelValidationError(f"All level generations failed: {errors}")
        return levels

    async def generate_for_point(
        self,
        *,
        tech_name: str,
        knowledge_point: KnowledgePoint,
        level_type: str,
    ) -> LearningLevelSchema:
        templates = self._load_templates()
        template = templates["templates"][level_type]
        level = await self.llm_client.structured_chat_completion(
            [
                {
                    "role": "user",
                    "content": (
                        "Generate one learning level for exactly one must_learn knowledge point. "
                        "The level must test only one core point. "
                        "Do not introduce advanced_later knowledge points or unrelated tools. "
                        "Use the supplied template constraints strictly.\n\n"
                        f"tech_name: {tech_name}\n"
                        f"knowledge_point_title: {knowledge_point.title}\n"
                        f"knowledge_point_goal: {knowledge_point.goal or ''}\n"
                        f"knowledge_point_difficulty: {knowledge_point.difficulty or ''}\n"
                        f"knowledge_point_reason: {knowledge_point.reason or ''}\n"
                        f"level_type: {level_type}\n"
                        f"template:\n{template}\n"
                    ),
                }
            ],
            LearningLevelSchema,
            temperature=0.1,
            max_tokens=2200,
        )
        return self._validate_level(level, knowledge_point, level_type)

    def list_by_knowledge_point(self, knowledge_point_id: int) -> list[LearningLevel]:
        return self.repository.list_levels_by_knowledge_point(knowledge_point_id)

    def get_level(self, level_id: int) -> LearningLevel | None:
        return self.repository.get_level(level_id)

    def _load_templates(self) -> dict:
        with self.templates_path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}

    def _validate_level(
        self,
        level: LearningLevelSchema,
        knowledge_point: KnowledgePoint,
        level_type: str,
    ) -> LearningLevelSchema:
        if level.type != level_type:
            level = level.model_copy(update={"type": level_type})
        if level.knowledge_point_title != knowledge_point.title:
            level = level.model_copy(update={"knowledge_point_title": knowledge_point.title})
        if level.type not in self.LEVEL_TYPES:
            raise LevelValidationError(f"Unsupported level type: {level.type}")
        missing = []
        for field_name in ["title", "task", "hint"]:
            if not getattr(level, field_name).strip():
                missing.append(field_name)
        if not level.acceptance_criteria:
            missing.append("acceptance_criteria")
        if not level.common_mistakes:
            missing.append("common_mistakes")
        if missing:
            raise LevelValidationError(f"Learning level missing fields: {', '.join(missing)}")
        return level
