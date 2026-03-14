"""OpenRouter API client with streaming support.

Streams chat completions from the OpenRouter API, yielding text deltas
as they arrive. The accumulated text is expected to be a valid
AssistantTurnStructured JSON object (validated downstream by chat_stream.py).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

import httpx

from app.config import settings
from app.prompt_builder import build_messages
from app.schemas import ChatMessage

logger = logging.getLogger(__name__)

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

REQUEST_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.0
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _parse_sse_content(line: str) -> str | None:
    """Extract the content delta from a single OpenRouter SSE data line.

    Returns the text content string, or None if the line contains no
    content (e.g. role-only deltas, empty choices, non-data lines).
    """
    if not line.startswith("data: "):
        return None

    data_str = line[len("data: "):]

    if data_str.strip() == "[DONE]":
        return None

    try:
        chunk = json.loads(data_str)
    except json.JSONDecodeError:
        return None

    choices = chunk.get("choices", [])
    if not choices:
        return None

    delta = choices[0].get("delta", {})
    return delta.get("content")


async def stream_chat_completion(
    *,
    messages: list[ChatMessage],
    region_profile: dict,
    model_id: str,
) -> AsyncGenerator[str, None]:
    """Stream text chunks from OpenRouter that form the assistant response.

    Yields raw text content deltas. The caller (chat_stream.py) accumulates,
    validates, and wraps them into SSE events for the frontend.
    """
    api_key = settings.openrouter_api_key
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured")

    api_messages = build_messages(messages, region_profile)

    payload = {
        "model": model_id,
        "messages": api_messages,
        "stream": True,
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://gengeo.app",
        "X-Title": "GenGeo",
    }

    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                async with client.stream(
                    "POST",
                    OPENROUTER_CHAT_URL,
                    json=payload,
                    headers=headers,
                ) as response:
                    if response.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES - 1:
                        body = await response.aread()
                        error_text = body.decode(errors="replace")[:300]
                        wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                        logger.warning(
                            "OpenRouter %d (attempt %d/%d), retrying in %.1fs: %s",
                            response.status_code, attempt + 1, MAX_RETRIES, wait, error_text,
                        )
                        await asyncio.sleep(wait)
                        continue

                    if response.status_code != 200:
                        body = await response.aread()
                        error_text = body.decode(errors="replace")[:300]
                        logger.error(
                            "OpenRouter error %d: %s", response.status_code, error_text,
                        )
                        raise RuntimeError(
                            f"OpenRouter returned {response.status_code}: {error_text}"
                        )

                    async for line in response.aiter_lines():
                        content = _parse_sse_content(line)
                        if content:
                            yield content
                    return
        except httpx.RequestError as exc:
            last_error = exc
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                logger.warning(
                    "OpenRouter network error (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1, MAX_RETRIES, wait, exc,
                )
                await asyncio.sleep(wait)
            else:
                raise RuntimeError(f"OpenRouter request failed after {MAX_RETRIES} attempts") from last_error
