import logging
from dataclasses import dataclass
from pathlib import Path

import httpx
import trafilatura
import yaml
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.config import get_settings
from app.llm.client import LLMClient
from app.models.entities import OfficialMaterial
from app.repositories.material_repository import MaterialRepository
from app.schemas.llm import OfficialMaterialSchema


logger = logging.getLogger(__name__)


class OfficialSourceNotFoundError(ValueError):
    pass


class OfficialDocsFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class OfficialSource:
    tech_name: str
    source_url: str
    aliases: list[str]


class OfficialDocsService:
    def __init__(
        self,
        db: Session,
        *,
        llm_client: LLMClient | None = None,
        sources_path: Path | None = None,
    ) -> None:
        self.db = db
        self.settings = get_settings()
        self.repository = MaterialRepository(db)
        self.llm_client = llm_client or LLMClient()
        self.sources_path = sources_path or Path(__file__).resolve().parents[1] / "data" / "official_sources.yaml"

    async def fetch_material(
        self,
        tech_name: str,
        *,
        force_refresh: bool = False,
        session_id: int | None = None,
    ) -> tuple[OfficialMaterial, bool]:
        source = self.get_source(tech_name)
        if not force_refresh:
            cached = self.repository.get_fresh_by_tech_name(
                source.tech_name,
                self.settings.official_material_cache_ttl_hours,
            )
            if cached is not None:
                return cached, True

        html = await self._fetch_html(source.source_url)
        extracted_text = self._extract_text(html, source.source_url)
        code_blocks = self._extract_code_blocks(html)
        material = await self._summarize_with_llm(source, extracted_text, code_blocks)

        raw_json = {
            "source_url": source.source_url,
            "extracted_text": extracted_text[:20000],
            "code_blocks": code_blocks,
        }
        entity = self.repository.create(material=material, raw_json=raw_json, session_id=session_id)
        return entity, False

    def get_latest_material(self, tech_name: str) -> OfficialMaterial | None:
        source = self.get_source(tech_name)
        return self.repository.get_latest_by_tech_name(source.tech_name)

    def get_source(self, tech_name: str) -> OfficialSource:
        normalized = self._normalize(tech_name)
        payload = self._load_sources()
        for item in payload.get("sources", {}).values():
            aliases = [item.get("tech_name", ""), *item.get("aliases", [])]
            if normalized in {self._normalize(alias) for alias in aliases}:
                return OfficialSource(
                    tech_name=item["tech_name"],
                    source_url=item["source_url"],
                    aliases=item.get("aliases", []),
                )
        raise OfficialSourceNotFoundError(f"No official source configured for tech_name: {tech_name}")

    def _load_sources(self) -> dict:
        with self.sources_path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}

    async def _fetch_html(self, source_url: str) -> str:
        headers = {"User-Agent": "TechLeveler/0.1 official-doc-fetcher"}
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
                response = await client.get(source_url)
                response.raise_for_status()
                return response.text
        except httpx.HTTPError as exc:
            logger.exception("Failed to fetch official docs from %s", source_url)
            raise OfficialDocsFetchError(f"Failed to fetch official docs: {source_url}") from exc

    def _extract_text(self, html: str, source_url: str) -> str:
        extracted = trafilatura.extract(
            html,
            url=source_url,
            include_comments=False,
            include_tables=True,
        )
        if extracted and extracted.strip():
            return extracted.strip()

        soup = BeautifulSoup(html, "html.parser")
        for element in soup(["script", "style", "nav", "footer"]):
            element.decompose()
        text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
        if not text:
            raise OfficialDocsFetchError("Official docs page did not contain extractable text.")
        return text

    def _extract_code_blocks(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        blocks: list[str] = []
        seen: set[str] = set()
        for element in soup.find_all(["pre", "code"]):
            text = element.get_text("\n").strip()
            if len(text) < 12 or text in seen:
                continue
            seen.add(text)
            blocks.append(text[:2000])
            if len(blocks) >= 12:
                break
        return blocks

    async def _summarize_with_llm(
        self,
        source: OfficialSource,
        extracted_text: str,
        code_blocks: list[str],
    ) -> OfficialMaterialSchema:
        messages = [
            {
                "role": "user",
                "content": (
                    "Summarize the official documentation excerpt for a learning system. "
                    "Use only the provided official source text and code blocks. "
                    "Do not invent official links. Keep the official_example concise and grounded in the code blocks "
                    "or the source text.\n\n"
                    f"tech_name: {source.tech_name}\n"
                    f"official_source_url: {source.source_url}\n\n"
                    f"official_text_excerpt:\n{extracted_text[:18000]}\n\n"
                    f"extracted_code_blocks:\n{code_blocks[:8]}"
                ),
            }
        ]
        material = await self.llm_client.structured_chat_completion(
            messages,
            OfficialMaterialSchema,
            temperature=0,
            max_tokens=1400,
        )
        return material.model_copy(update={"tech_name": source.tech_name, "source_url": source.source_url})

    def _normalize(self, value: str) -> str:
        return value.strip().lower().replace(" ", "").replace("-", "").replace("_", "")
