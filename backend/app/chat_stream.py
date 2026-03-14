"""SSE streaming adapter for assistant turn output.

Wraps an LLM text stream into the SSE event lifecycle:
  response.started  -> metadata
  response.delta    -> incremental text chunk
  response.completed -> final AssistantTurnStructured JSON
  response.error    -> typed error shape
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

from app.schemas import AssistantTurnStructured

logger = logging.getLogger(__name__)


async def generate_chat_events(
    *,
    request_id: str,
    context_id: str,
    model_id: str,
    llm_stream: AsyncGenerator[str, None],
) -> AsyncGenerator[dict, None]:
    """Yield SSE event dicts consumable by ``sse-starlette``."""

    yield {
        "event": "response.started",
        "data": json.dumps({
            "request_id": request_id,
            "context_id": context_id,
            "model_id": model_id,
        }),
    }

    accumulated = ""

    try:
        async for chunk in llm_stream:
            accumulated += chunk
            yield {
                "event": "response.delta",
                "data": json.dumps({"delta": chunk}),
            }
    except Exception as exc:
        logger.exception("LLM stream error")
        yield {
            "event": "response.error",
            "data": json.dumps({
                "error": {
                    "code": "LLM_STREAM_ERROR",
                    "message": str(exc),
                    "retryable": True,
                },
                "meta": {"request_id": request_id},
            }),
        }
        return

    try:
        structured = AssistantTurnStructured.model_validate_json(accumulated)
        yield {
            "event": "response.completed",
            "data": structured.model_dump_json(),
        }
    except Exception:
        logger.warning("LLM output is not valid structured JSON; wrapping as fallback")
        fallback = AssistantTurnStructured(
            answer=accumulated,
            reasoning_summary="",
            evidence=[],
            limitations=["LLM output was not in expected structured format"],
            confidence="low",
        )
        yield {
            "event": "response.completed",
            "data": fallback.model_dump_json(),
        }
