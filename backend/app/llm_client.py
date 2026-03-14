"""OpenRouter API client with streaming and structured output support.

Full implementation: Part D.
This module currently provides a stub async generator that yields a valid
AssistantTurnStructured JSON payload in small chunks, allowing the streaming
infrastructure (Part B) to be tested end-to-end without a live LLM.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from app.schemas import AssistantTurnStructured, ChatMessage


async def stream_chat_completion(
    *,
    messages: list[ChatMessage],
    region_profile: dict,
    model_id: str,
) -> AsyncGenerator[str, None]:
    """Yield text chunks that form a valid AssistantTurnStructured JSON.

    Part D will replace this with real OpenRouter streaming.
    """
    stub = AssistantTurnStructured(
        answer=(
            "This is a placeholder response. "
            "The LLM integration (Part D) is not yet implemented."
        ),
        reasoning_summary="Stub response for development and testing.",
        evidence=["No real data analysis performed"],
        limitations=["LLM integration pending"],
        confidence="low",
    )
    text = stub.model_dump_json()
    chunk_size = 40
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]
