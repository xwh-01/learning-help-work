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
                        "Language and format requirements:\n"
                        "- This is a knowledge Q&A lesson, not a code editor exercise.\n"
                        "- Do not require the learner to write a complete runnable program.\n"
                        "- You must output scenario, question, answer_requirements, rubric, reference_answer, hint, and common_mistakes.\n"
                        "- Also output task as a concise Markdown rendering of scenario + question + answer_requirements for backward compatibility.\n"
                        "- Write all learner-facing fields in Chinese.\n"
                        "- You must output reference_answer.\n"
                        "- reference_answer should be concise answer points, not the only standard answer.\n"
                        "- Keep scenario, question, and reference_answer concise.\n"
                        "- Keep hint, reference_answer, and each list item concise.\n"
                        "- Keep technology names, API names, class names, function names, commands, and code keywords in their original English.\n"
                        "- If level_type is observe, make it a Compare question: baseline vs target differences and the problem solved by the target technology.\n"
                        "- If level_type is hands_on, make it a Practice scenario design question: steps/nodes/modules, state/data flow, why this design, and when not to use the target technology. Pseudocode is allowed, but runnable code is not required.\n"
                        "- If level_type is summary, make it a Reflect question: pain point, baseline solution, when to use, when not to use, and a minimal intuition example.\n\n"
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
            max_tokens=4000,
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
        if not level.acceptance_criteria and level.rubric:
            level = level.model_copy(update={"acceptance_criteria": level.rubric})
        if not level.acceptance_criteria and level.answer_requirements:
            level = level.model_copy(update={"acceptance_criteria": level.answer_requirements})
        if not level.task.strip():
            level = level.model_copy(
                update={
                    "task": "\n\n".join(
                        part
                        for part in [
                            f"### 场景\n{level.scenario}" if level.scenario else "",
                            f"### 问题\n{level.question}" if level.question else "",
                            "### 答题要求\n" + "\n".join(f"- {item}" for item in level.answer_requirements)
                            if level.answer_requirements
                            else "",
                        ]
                        if part
                    )
                }
            )
        missing = []
        for field_name in ["title", "scenario", "question", "task", "hint", "reference_answer"]:
            if not getattr(level, field_name).strip():
                missing.append(field_name)
        if not level.answer_requirements:
            missing.append("answer_requirements")
        if not level.rubric:
            missing.append("rubric")
        if not level.acceptance_criteria:
            missing.append("acceptance_criteria")
        if not level.common_mistakes:
            missing.append("common_mistakes")
        if missing:
            raise LevelValidationError(f"Learning level missing fields: {', '.join(missing)}")
        return level
