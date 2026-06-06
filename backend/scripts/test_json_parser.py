"""Smoke tests for LLM JSON parser."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import BaseModel
from app.llm.json_parser import parse_llm_json_with_repair, LLMJsonParseError, LLMJsonTruncatedError


class TestSchema(BaseModel):
    name: str
    value: int


def run():
    passed = 0
    total = 7

    # 1. pure JSON
    r = parse_llm_json_with_repair('{"name": "test", "value": 42}', TestSchema)
    assert r.name == "test"
    assert r.value == 42
    passed += 1
    print(f"  PASS 1/7: pure JSON -> {r.model_dump()}")

    # 2. markdown ```json block
    r = parse_llm_json_with_repair('```json\n{"name": "x", "value": 1}\n```', TestSchema)
    assert r.name == "x"
    assert r.value == 1
    passed += 1
    print(f"  PASS 2/7: markdown code block -> {r.model_dump()}")

    # 3. JSON with surrounding text
    r = parse_llm_json_with_repair('The result: {"name": "y", "value": 2}. End.', TestSchema)
    assert r.name == "y"
    assert r.value == 2
    passed += 1
    print(f"  PASS 3/7: surrounding text -> {r.model_dump()}")

    # 4. extra fields (extra=ignore by Pydantic)
    r = parse_llm_json_with_repair('{"name": "z", "value": 3, "bonus": true}', TestSchema)
    assert r.name == "z"
    assert r.value == 3
    passed += 1
    print(f"  PASS 4/7: extra fields ignored -> {r.model_dump()}")

    # 5. invalid JSON
    try:
        parse_llm_json_with_repair("not json at all", TestSchema)
        raise AssertionError("should have raised")
    except LLMJsonParseError as e:
        passed += 1
        print(f"  PASS 5/7: invalid JSON raises LLMJsonParseError -> {str(e)[:80]}")

    # 6. truncated JSON
    try:
        parse_llm_json_with_repair('{"name": "t", "value": 42', TestSchema)
        raise AssertionError("should have raised")
    except (LLMJsonParseError, LLMJsonTruncatedError) as e:
        passed += 1
        print(f"  PASS 6/7: truncated JSON raises error -> {str(e)[:80]}")

    # 7. empty string
    try:
        parse_llm_json_with_repair("", TestSchema)
        raise AssertionError("should have raised")
    except LLMJsonParseError as e:
        passed += 1
        print(f"  PASS 7/7: empty string raises LLMJsonParseError -> {str(e)[:80]}")

    print(f"\n  Result: {passed}/{total} passed")
    return passed == total


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
