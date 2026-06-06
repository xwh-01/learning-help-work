from pydantic import Field

from app.schemas.llm import KnowledgePointSchema, LearningExampleSchema, LearningLevelSchema, StrictBaseModel


class KnowledgePointListSchema(StrictBaseModel):
    knowledge_points: list[KnowledgePointSchema] = Field(min_length=1)


class LearningExampleListSchema(StrictBaseModel):
    examples: list[LearningExampleSchema] = Field(min_length=1)


class LearningLevelListSchema(StrictBaseModel):
    levels: list[LearningLevelSchema] = Field(min_length=1)
