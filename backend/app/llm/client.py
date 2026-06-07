import asyncio
import json
import logging
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.llm.json_parser import LLMJsonParseError, parse_llm_json_with_repair


logger = logging.getLogger(__name__)
SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMError(RuntimeError):
    pass


class LLMConfigurationError(LLMError):
    pass


class LLMResponseValidationError(LLMError):
    pass


class LLMClient:
    def __init__(self, timeout_seconds: float = 60.0, max_retries: int = 2) -> None:
        self.settings = get_settings()
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def is_configured(self) -> bool:
        return bool(self.settings.llm_base_url and self.settings.llm_api_key and self.settings.llm_model)

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        require_json: bool = False,
    ) -> str:
        if not self.is_configured():
            raise LLMConfigurationError("LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL must be configured.")

        payload: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if require_json:
            payload["response_format"] = {"type": "json_object"}

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(
                        self._chat_completions_url(),
                        headers=self._headers(),
                        json=payload,
                    )
                    response.raise_for_status()
                    body = response.json()
                    return self._extract_message_content(body)
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
                last_error = exc
                detail = str(exc)
                if isinstance(exc, httpx.HTTPStatusError):
                    try:
                        detail = f"{exc.response.status_code} {exc.response.text[:1000]}"
                    except Exception:
                        pass
                logger.warning(
                    "LLM chat completion failed on attempt %s/%s: %s",
                    attempt + 1,
                    self.max_retries + 1,
                    detail,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(1)

        logger.error("LLM chat completion failed after retries: %s", last_error)
        raise LLMError(f"LLM chat completion failed after {self.max_retries + 1} attempts: {last_error}") from last_error

    async def structured_chat_completion(
        self,
        messages: list[dict[str, str]],
        schema: type[SchemaT],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> SchemaT:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            schema_instruction = {
                "role": "system",
                "content": (
                    "Return only a valid JSON object. Do not wrap it in Markdown. "
                    f"The JSON must match this schema: {json.dumps(schema.model_json_schema(), ensure_ascii=False)}"
                ),
            }
            if attempt > 0:
                schema_instruction["content"] += (
                    " The previous response failed validation. Be strict about required fields and types."
                )

            content = await self.chat_completion(
                [schema_instruction, *messages],
                temperature=temperature,
                max_tokens=max_tokens,
                require_json=True,
            )

            try:
                return parse_llm_json_with_repair(content, schema)
            except (LLMJsonParseError, ValidationError, ValueError) as exc:
                last_error = exc
                preview = content[:800] if len(content) > 800 else content
                logger.warning(
                    "LLM JSON parsing failed for %s on attempt %s/%s. "
                    "Raw response (first 800 chars): %s | Error: %s",
                    schema.__name__,
                    attempt + 1,
                    self.max_retries + 1,
                    preview,
                    exc,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(1)

        logger.error("LLM JSON failed validation after retries for %s.", schema.__name__)
        preview = content[:500] if 'content' in dir() else "(no content)"
        raise LLMResponseValidationError(
            f"LLM response did not match {schema.__name__} after {self.max_retries + 1} attempts. "
            f"Last raw response: {preview}"
        ) from last_error

    def _chat_completions_url(self) -> str:
        return f"{self.settings.llm_base_url.rstrip('/')}/chat/completions"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }

    def _extract_message_content(self, body: dict[str, Any]) -> str:
        content = body["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("LLM response content is empty.")
        return content.strip()
