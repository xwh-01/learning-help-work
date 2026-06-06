from pathlib import Path

import yaml

from app.schemas.relations import TechRelationRead


class TechRelationNotFoundError(ValueError):
    pass


class TechRelationService:
    def __init__(self, relations_path: Path | None = None) -> None:
        self.relations_path = relations_path or Path(__file__).resolve().parents[1] / "data" / "tech_relations.yaml"

    def get_relation(self, tech_name: str) -> TechRelationRead:
        normalized = self._normalize(tech_name)
        payload = self._load_relations()
        for item in payload.get("relations", {}).values():
            aliases = [item.get("tech_name", ""), *item.get("aliases", [])]
            if normalized in {self._normalize(alias) for alias in aliases}:
                return TechRelationRead(
                    tech_name=item["tech_name"],
                    baseline=item.get("baseline", []),
                    similar=item.get("similar", []),
                    skip_now=item.get("skip_now", []),
                )
        raise TechRelationNotFoundError(f"No technical relation configured for tech_name: {tech_name}")

    def _load_relations(self) -> dict:
        with self.relations_path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}

    def _normalize(self, value: str) -> str:
        return value.strip().lower().replace(" ", "").replace("-", "").replace("_", "")
