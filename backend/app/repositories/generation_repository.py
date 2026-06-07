from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import KnowledgePoint, LearningExample, LearningLevel
from app.schemas.llm import KnowledgePointSchema, LearningExampleSchema, LearningLevelSchema


class GenerationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_knowledge_points(
        self,
        *,
        session_id: int,
        tech_name: str,
        points: list[KnowledgePointSchema],
    ) -> list[KnowledgePoint]:
        entities = [
            KnowledgePoint(
                session_id=session_id,
                tech_name=tech_name,
                title=point.title,
                goal=point.goal,
                depends_on=point.depends_on,
                difficulty=point.difficulty,
                reason=point.reason,
                category=point.category,
                sort_order=index,
            )
            for index, point in enumerate(points, start=1)
        ]
        self.db.add_all(entities)
        self.db.commit()
        for entity in entities:
            self.db.refresh(entity)
        return entities

    def list_knowledge_points(self, session_id: int) -> list[KnowledgePoint]:
        stmt = (
            select(KnowledgePoint)
            .where(KnowledgePoint.session_id == session_id)
            .order_by(KnowledgePoint.sort_order, KnowledgePoint.id)
        )
        return list(self.db.execute(stmt).scalars().all())

    def create_examples(
        self,
        *,
        session_id: int,
        point_by_title: dict[str, KnowledgePoint],
        examples: list[LearningExampleSchema],
    ) -> list[LearningExample]:
        entities: list[LearningExample] = []
        for example in examples:
            point = point_by_title.get(example.knowledge_point_title)
            if point is None:
                continue
            entities.append(
                LearningExample(
                    session_id=session_id,
                    knowledge_point_id=point.id,
                    official_example=example.official_example,
                    beginner_example=example.beginner_example,
                    baseline_example=example.baseline_example,
                    target_example=example.target_example,
                    observe_questions=example.observe_questions,
                    result_json=example.model_dump(),
                )
            )
        self.db.add_all(entities)
        self.db.commit()
        for entity in entities:
            self.db.refresh(entity)
        return entities

    def create_example(
        self,
        *,
        session_id: int,
        knowledge_point_id: int,
        example: LearningExampleSchema,
    ) -> LearningExample:
        entity = LearningExample(
            session_id=session_id,
            knowledge_point_id=knowledge_point_id,
            official_example=example.official_example,
            beginner_example=example.beginner_example,
            baseline_example=example.baseline_example,
            target_example=example.target_example,
            observe_questions=example.observe_questions,
            result_json=example.model_dump(),
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def list_examples_by_knowledge_point(self, knowledge_point_id: int) -> list[LearningExample]:
        stmt = (
            select(LearningExample)
            .where(LearningExample.knowledge_point_id == knowledge_point_id)
            .order_by(LearningExample.created_at, LearningExample.id)
        )
        return list(self.db.execute(stmt).scalars().all())

    def create_levels(
        self,
        *,
        session_id: int,
        point_by_title: dict[str, KnowledgePoint],
        levels: list[LearningLevelSchema],
    ) -> list[LearningLevel]:
        per_point_count: dict[str, int] = {}
        entities: list[LearningLevel] = []
        for level in levels:
            point = point_by_title.get(level.knowledge_point_title)
            if point is None:
                continue
            per_point_count[level.knowledge_point_title] = per_point_count.get(level.knowledge_point_title, 0) + 1
            entities.append(
                LearningLevel(
                    session_id=session_id,
                    knowledge_point_id=point.id,
                    level_type=level.type,
                    title=level.title,
                    scenario=level.scenario,
                    question=level.question,
                    answer_requirements=level.answer_requirements,
                    rubric=level.rubric,
                    task=level.task,
                    hint=level.hint,
                    acceptance_criteria=level.acceptance_criteria,
                    common_mistakes=level.common_mistakes,
                    reference_answer=level.reference_answer,
                    sort_order=per_point_count[level.knowledge_point_title],
                )
            )
        self.db.add_all(entities)
        self.db.commit()
        for entity in entities:
            self.db.refresh(entity)
        return entities

    def create_level(
        self,
        *,
        session_id: int,
        knowledge_point_id: int,
        level: LearningLevelSchema,
        sort_order: int,
    ) -> LearningLevel:
        entity = LearningLevel(
            session_id=session_id,
            knowledge_point_id=knowledge_point_id,
            level_type=level.type,
            title=level.title,
            scenario=level.scenario,
            question=level.question,
            answer_requirements=level.answer_requirements,
            rubric=level.rubric,
            task=level.task,
            hint=level.hint,
            acceptance_criteria=level.acceptance_criteria,
            common_mistakes=level.common_mistakes,
            reference_answer=level.reference_answer,
            sort_order=sort_order,
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def list_levels_by_knowledge_point(self, knowledge_point_id: int) -> list[LearningLevel]:
        stmt = (
            select(LearningLevel)
            .where(LearningLevel.knowledge_point_id == knowledge_point_id)
            .order_by(LearningLevel.sort_order, LearningLevel.id)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_level_by_knowledge_point_and_type(self, knowledge_point_id: int, level_type: str) -> LearningLevel | None:
        stmt = (
            select(LearningLevel)
            .where(LearningLevel.knowledge_point_id == knowledge_point_id)
            .where(LearningLevel.level_type == level_type)
            .order_by(LearningLevel.id)
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_level(self, level_id: int) -> LearningLevel | None:
        stmt = select(LearningLevel).where(LearningLevel.id == level_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_knowledge_point(self, knowledge_point_id: int) -> KnowledgePoint | None:
        stmt = select(KnowledgePoint).where(KnowledgePoint.id == knowledge_point_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_next_level(self, level: LearningLevel) -> LearningLevel | None:
        same_point_stmt = (
            select(LearningLevel)
            .where(LearningLevel.knowledge_point_id == level.knowledge_point_id)
            .where(LearningLevel.sort_order > level.sort_order)
            .order_by(LearningLevel.sort_order, LearningLevel.id)
            .limit(1)
        )
        next_same_point = self.db.execute(same_point_stmt).scalar_one_or_none()
        if next_same_point is not None:
            return next_same_point

        current_point = self.get_knowledge_point(level.knowledge_point_id)
        if current_point is None:
            return None

        next_point_stmt = (
            select(KnowledgePoint)
            .where(KnowledgePoint.session_id == level.session_id)
            .where(KnowledgePoint.category == "must_learn")
            .where(KnowledgePoint.sort_order > current_point.sort_order)
            .order_by(KnowledgePoint.sort_order, KnowledgePoint.id)
            .limit(1)
        )
        next_point = self.db.execute(next_point_stmt).scalar_one_or_none()
        if next_point is None:
            return None

        next_level_stmt = (
            select(LearningLevel)
            .where(LearningLevel.knowledge_point_id == next_point.id)
            .order_by(LearningLevel.sort_order, LearningLevel.id)
            .limit(1)
        )
        return self.db.execute(next_level_stmt).scalar_one_or_none()
