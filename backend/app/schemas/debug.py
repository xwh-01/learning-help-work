from pydantic import BaseModel, Field

from app.schemas.llm import OfficialMaterialSchema


class LLMJsonDebugRequest(BaseModel):
    tech_name: str = Field(default="FastAPI", min_length=1, max_length=128)


class LLMJsonDebugResponse(BaseModel):
    model: str
    data: OfficialMaterialSchema
