from pydantic import BaseModel


class TechRelationRead(BaseModel):
    tech_name: str
    baseline: list[str]
    similar: list[str]
    skip_now: list[str]
