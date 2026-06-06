from fastapi import APIRouter, HTTPException

from app.schemas.relations import TechRelationRead
from app.services.tech_relation_service import TechRelationNotFoundError, TechRelationService


router = APIRouter(prefix="/api/relations", tags=["relations"])


@router.get("/{tech_name}", response_model=TechRelationRead)
def get_relation(tech_name: str) -> TechRelationRead:
    service = TechRelationService()
    try:
        return service.get_relation(tech_name)
    except TechRelationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
