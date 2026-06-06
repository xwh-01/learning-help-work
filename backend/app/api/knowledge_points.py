from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.examples import LearningExampleRead
from app.schemas.levels import LearningLevelRead
from app.services.example_generator_service import ExampleGeneratorService
from app.services.level_generator_service import LevelGeneratorService


router = APIRouter(prefix="/api/knowledge-points", tags=["knowledge-points"])


@router.get("/{knowledge_point_id}/examples", response_model=list[LearningExampleRead])
def get_examples_by_knowledge_point(
    knowledge_point_id: int,
    db: Session = Depends(get_db),
) -> list[LearningExampleRead]:
    examples = ExampleGeneratorService(db).list_by_knowledge_point(knowledge_point_id)
    return [
        LearningExampleRead(
            id=example.id,
            session_id=example.session_id,
            knowledge_point_id=example.knowledge_point_id,
            official_example=example.official_example,
            beginner_example=example.beginner_example,
            baseline_example=example.baseline_example,
            target_example=example.target_example,
            observe_questions=example.observe_questions or [],
            created_at=example.created_at,
            updated_at=example.updated_at,
        )
        for example in examples
    ]


@router.get("/{knowledge_point_id}/levels", response_model=list[LearningLevelRead])
def get_levels_by_knowledge_point(
    knowledge_point_id: int,
    db: Session = Depends(get_db),
) -> list[LearningLevelRead]:
    levels = LevelGeneratorService(db).list_by_knowledge_point(knowledge_point_id)
    return [_to_level_read(level) for level in levels]


def _to_level_read(level) -> LearningLevelRead:
    return LearningLevelRead(
        id=level.id,
        session_id=level.session_id,
        knowledge_point_id=level.knowledge_point_id,
        type=level.level_type,
        title=level.title,
        task=level.task,
        hint=level.hint,
        acceptance_criteria=level.acceptance_criteria or [],
        common_mistakes=level.common_mistakes or [],
        sort_order=level.sort_order,
        created_at=level.created_at,
        updated_at=level.updated_at,
    )
