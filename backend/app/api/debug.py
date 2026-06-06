import logging

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.llm.client import LLMClient, LLMConfigurationError, LLMError
from app.schemas.debug import LLMJsonDebugRequest, LLMJsonDebugResponse
from app.schemas.llm import OfficialMaterialSchema


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.post("/llm-json", response_model=LLMJsonDebugResponse)
async def debug_llm_json(payload: LLMJsonDebugRequest) -> LLMJsonDebugResponse:
    settings = get_settings()
    client = LLMClient()

    messages = [
        {
            "role": "user",
            "content": (
                "For a connectivity test, return a concise JSON object describing the requested technology. "
                "Use a short official-style summary, one minimal example, a likely official documentation URL, "
                f"and 2 short chunks. Technology: {payload.tech_name}"
            ),
        }
    ]

    try:
        data = await client.structured_chat_completion(
            messages,
            OfficialMaterialSchema,
            temperature=0,
            max_tokens=800,
        )
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except LLMError as exc:
        logger.exception("Debug LLM JSON call failed.")
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return LLMJsonDebugResponse(model=settings.llm_model, data=data)
