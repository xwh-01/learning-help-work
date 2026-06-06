from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.llm.client import LLMConfigurationError, LLMError
from app.models.entities import OfficialMaterial
from app.schemas.materials import MaterialFetchRequest, OfficialMaterialRead
from app.services.official_docs_service import (
    OfficialDocsFetchError,
    OfficialDocsService,
    OfficialSourceNotFoundError,
)


router = APIRouter(prefix="/api/materials", tags=["materials"])


@router.post("/fetch", response_model=OfficialMaterialRead)
async def fetch_material(payload: MaterialFetchRequest, db: Session = Depends(get_db)) -> OfficialMaterialRead:
    service = OfficialDocsService(db)
    try:
        material, cached = await service.fetch_material(payload.tech_name, force_refresh=payload.force_refresh)
    except OfficialSourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (OfficialDocsFetchError, LLMError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _to_read_model(material, cached=cached)


@router.get("/{tech_name}", response_model=OfficialMaterialRead)
def get_material(tech_name: str, db: Session = Depends(get_db)) -> OfficialMaterialRead:
    service = OfficialDocsService(db)
    try:
        material = service.get_latest_material(tech_name)
    except OfficialSourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if material is None:
        raise HTTPException(status_code=404, detail=f"No official material found for tech_name: {tech_name}")
    return _to_read_model(material, cached=True)


def _to_read_model(material: OfficialMaterial, *, cached: bool) -> OfficialMaterialRead:
    return OfficialMaterialRead(
        id=material.id,
        tech_name=material.tech_name,
        official_summary=material.official_summary or "",
        official_example=material.official_example or "",
        source_url=material.source_url,
        chunks=material.chunks_json or [],
        raw_json=material.raw_json,
        cached=cached,
        created_at=material.created_at,
    )
