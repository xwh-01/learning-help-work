from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import SessionLocal


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/db")
def database_health() -> dict[str, str]:
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
    return {"status": "ok"}
