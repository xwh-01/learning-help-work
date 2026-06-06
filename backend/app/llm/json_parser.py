import json
import logging
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMJsonParseError(ValueError):
    pass


class LLMJsonTruncatedError(LLMJsonParseError):
    pass


def parse_llm_json_with_repair(raw_text: str, schema: type[SchemaT]) -> SchemaT:
    if not raw_text or not raw_text.strip():
        _fail(raw_text, "LLM response is empty.", schema)

    content = raw_text.strip()

    content = _extract_json_from_markdown(content)

    extracted = _extract_first_json_object(content)
    if extracted is None:
        _fail(raw_text, "No JSON object found in LLM response.", schema)

    try:
        loaded = json.loads(extracted)
    except json.JSONDecodeError as exc:
        if _is_truncated_json(extracted):
            raise LLMJsonTruncatedError(
                f"LLM response appears to be truncated JSON (incomplete string or unclosed brace). "
                f"Preview (first 500 chars): {raw_text[:500]}"
            ) from exc
        _fail(raw_text, f"Invalid JSON in LLM response: {exc}", schema)

    if not isinstance(loaded, dict):
        _fail(raw_text, f"Expected JSON object, got {type(loaded).__name__}.", schema)

    try:
        return schema.model_validate(loaded)
    except ValidationError as exc:
        raise LLMJsonParseError(
            f"LLM JSON parsed but failed Pydantic validation for {schema.__name__}. "
            f"Preview (first 500 chars): {raw_text[:500]}"
        ) from exc


def _extract_json_from_markdown(content: str) -> str:
    stripped = content.strip()
    markdown_pattern = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)
    match = markdown_pattern.search(stripped)
    if match:
        return match.group(1).strip()
    return stripped


def _extract_first_json_object(content: str) -> str | None:
    bracket_start = content.find("{")
    if bracket_start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for i in range(bracket_start, len(content)):
        char = content[i]
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[bracket_start : i + 1]
    return None


def _is_truncated_json(content: str) -> bool:
    stripped = content.strip()
    if not stripped or stripped[-1] == "}":
        return False
    last_bracket = stripped.rfind("}") if "}" in stripped else -1
    if last_bracket < len(stripped) - 1 and not stripped.rstrip().endswith("}"):
        return True
    if stripped.count("{") > stripped.count("}"):
        return True
    if _ends_in_mid_string(stripped):
        return True
    return False


def _ends_in_mid_string(content: str) -> bool:
    in_string = False
    escape = False
    for char in content:
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
    return in_string


def _fail(raw_text: str, message: str, schema: type[BaseModel]) -> None:
    preview = raw_text[:500] if len(raw_text) > 500 else raw_text
    raise LLMJsonParseError(
        f"{message} Schema: {schema.__name__}. Raw response preview: {preview}"
    )
