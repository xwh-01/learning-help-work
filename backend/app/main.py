from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.answers import router as answers_router
from app.api.debug import router as debug_router
from app.api.comparisons import router as comparisons_router
from app.api.health import router as health_router
from app.api.knowledge_points import router as knowledge_points_router
from app.api.levels import router as levels_router
from app.api.learning_sessions import router as learning_sessions_router
from app.api.materials import router as materials_router
from app.api.relations import router as relations_router
from app.config import get_settings


settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(debug_router)
app.include_router(materials_router)
app.include_router(relations_router)
app.include_router(comparisons_router)
app.include_router(learning_sessions_router)
app.include_router(knowledge_points_router)
app.include_router(levels_router)
app.include_router(answers_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "TechLeveler backend is running"}
