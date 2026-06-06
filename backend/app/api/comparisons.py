from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.llm.client import LLMConfigurationError, LLMError
from app.models.entities import ComparisonResult
from app.schemas.comparisons import ComparisonGenerateRequest, ComparisonResultRead
from app.services.comparison_service import ComparisonInputError, ComparisonService
from app.services.tech_relation_service import TechRelationNotFoundError


router = APIRouter(prefix="/api/comparisons", tags=["comparisons"])


@router.post("/generate", response_model=ComparisonResultRead)
async def generate_comparison(
    payload: ComparisonGenerateRequest,
    db: Session = Depends(get_db),
) -> ComparisonResultRead:
    service = ComparisonService(db)
    try:
        comparison = await service.generate(session_id=payload.session_id, tech_name=payload.tech_name)
    except TechRelationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ComparisonInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _to_read_model(comparison)


@router.get("/session/{session_id}", response_model=list[ComparisonResultRead])
def list_session_comparisons(session_id: int, db: Session = Depends(get_db)) -> list[ComparisonResultRead]:
    service = ComparisonService(db)
    return [_to_read_model(item) for item in service.list_by_session(session_id)]


def _to_read_model(comparison: ComparisonResult) -> ComparisonResultRead:
    result_json = comparison.result_json or {}
    return ComparisonResultRead(
        id=comparison.id,
        session_id=comparison.session_id,
        tech_name=comparison.tech_name,
        target_tech=result_json.get("target_tech", comparison.tech_name),
        selected_for_comparison=comparison.selected_for_comparison or [],
        baseline_solution=comparison.baseline_solution or "",
        comparison_task=comparison.comparison_task or "",
        comparison_table=comparison.comparison_table or [],
        when_to_use=comparison.when_to_use or [],
        when_not_to_use=comparison.when_not_to_use or [],
        skipped_candidates=result_json.get("skipped_candidates", []),
        created_at=comparison.created_at,
    )
