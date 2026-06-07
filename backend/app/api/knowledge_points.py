from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.llm.client import LLMConfigurationError, LLMError
from app.repositories.generation_repository import GenerationRepository
from app.repositories.material_repository import MaterialRepository
from app.repositories.practice_repository import PracticeRepository
from app.schemas.examples import LearningExampleRead
from app.schemas.levels import LearningLevelRead
from app.services.example_generator_service import ExampleValidationError
from app.services.example_generator_service import ExampleGeneratorService
from app.services.level_generator_service import LevelGeneratorService, LevelValidationError


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


@router.post("/{knowledge_point_id}/ensure-example", response_model=LearningExampleRead)
async def ensure_example_by_knowledge_point(
    knowledge_point_id: int,
    db: Session = Depends(get_db),
) -> LearningExampleRead:
    generation_repository = GenerationRepository(db)
    point = generation_repository.get_knowledge_point(knowledge_point_id)
    if point is None:
        raise HTTPException(status_code=404, detail=f"knowledge point not found: {knowledge_point_id}")

    existing = generation_repository.list_examples_by_knowledge_point(knowledge_point_id)
    if existing:
        return _to_example_read(existing[0])

    material = MaterialRepository(db).get_latest_by_tech_name(point.tech_name)
    comparison = PracticeRepository(db).latest_comparison(point.session_id)
    if material is None:
        raise HTTPException(status_code=400, detail="Official source is not configured for this technology.")
    if comparison is None:
        raise HTTPException(status_code=400, detail="Comparison result is required before generating examples.")

    try:
        example_schema = await ExampleGeneratorService(db).generate_for_point(
            tech_name=point.tech_name,
            knowledge_point=point,
            material=material,
            comparison=comparison,
        )
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (ExampleValidationError, LLMError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    example = generation_repository.create_example(
        session_id=point.session_id,
        knowledge_point_id=point.id,
        example=example_schema,
    )
    return _to_example_read(example)


@router.get("/{knowledge_point_id}/levels", response_model=list[LearningLevelRead])
def get_levels_by_knowledge_point(
    knowledge_point_id: int,
    db: Session = Depends(get_db),
) -> list[LearningLevelRead]:
    levels = LevelGeneratorService(db).list_by_knowledge_point(knowledge_point_id)
    return [_to_level_read(level) for level in levels]


@router.post("/{knowledge_point_id}/levels/{level_type}/ensure", response_model=LearningLevelRead)
async def ensure_level_by_knowledge_point(
    knowledge_point_id: int,
    level_type: str,
    db: Session = Depends(get_db),
) -> LearningLevelRead:
    if level_type not in LevelGeneratorService.LEVEL_TYPES:
        raise HTTPException(status_code=400, detail=f"unsupported level_type: {level_type}")

    generation_repository = GenerationRepository(db)
    point = generation_repository.get_knowledge_point(knowledge_point_id)
    if point is None:
        raise HTTPException(status_code=404, detail=f"knowledge point not found: {knowledge_point_id}")

    existing = generation_repository.get_level_by_knowledge_point_and_type(knowledge_point_id, level_type)
    if existing is not None:
        return _to_level_read(existing)

    try:
        level_schema = await LevelGeneratorService(db).generate_for_point(
            tech_name=point.tech_name,
            knowledge_point=point,
            level_type=level_type,
        )
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (LevelValidationError, LLMError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    sort_order = LevelGeneratorService.LEVEL_TYPES.index(level_type) + 1
    level = generation_repository.create_level(
        session_id=point.session_id,
        knowledge_point_id=point.id,
        level=level_schema,
        sort_order=sort_order,
    )
    return _to_level_read(level)


def _to_example_read(example) -> LearningExampleRead:
    return LearningExampleRead(
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


def _to_level_read(level) -> LearningLevelRead:
    return LearningLevelRead(
        id=level.id,
        session_id=level.session_id,
        knowledge_point_id=level.knowledge_point_id,
        type=level.level_type,
        title=level.title,
        scenario=level.scenario,
        question=level.question,
        answer_requirements=level.answer_requirements or [],
        task=level.task,
        hint=level.hint,
        rubric=level.rubric or [],
        acceptance_criteria=level.acceptance_criteria or [],
        common_mistakes=level.common_mistakes or [],
        reference_answer=level.reference_answer,
        sort_order=level.sort_order,
        created_at=level.created_at,
        updated_at=level.updated_at,
    )
