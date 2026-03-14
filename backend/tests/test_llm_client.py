"""Tests for the OpenRouter LLM client.

Uses mock httpx transports and patched settings to verify streaming
behaviour without making real API calls.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.llm_client import _parse_sse_content, stream_chat_completion
from app.schemas import ChatMessage


# ── _parse_sse_content unit tests ─────────────────────────────


class TestParseSseContent:
    def test_extracts_content_from_valid_data_line(self):
        line = 'data: {"choices":[{"delta":{"content":"hello"}}]}'
        assert _parse_sse_content(line) == "hello"

    def test_returns_none_for_role_only_delta(self):
        line = 'data: {"choices":[{"delta":{"role":"assistant"}}]}'
        assert _parse_sse_content(line) is None

    def test_returns_none_for_done_sentinel(self):
        assert _parse_sse_content("data: [DONE]") is None

    def test_returns_none_for_empty_choices(self):
        assert _parse_sse_content('data: {"choices":[]}') is None

    def test_returns_none_for_non_data_line(self):
        assert _parse_sse_content("event: message") is None
        assert _parse_sse_content("") is None
        assert _parse_sse_content(": comment") is None

    def test_returns_none_for_malformed_json(self):
        assert _parse_sse_content("data: {bad json") is None

    def test_extracts_content_with_special_chars(self):
        content = 'hello "world"'
        line = f'data: {{"choices":[{{"delta":{{"content":{json.dumps(content)}}}}}]}}'
        assert _parse_sse_content(line) == content

    def test_returns_none_for_empty_content(self):
        line = 'data: {"choices":[{"delta":{"content":""}}]}'
        # empty string is falsy but is a valid string; _parse_sse_content
        # returns it as-is (the caller checks truthiness)
        result = _parse_sse_content(line)
        assert result == ""

    def test_returns_none_for_finish_reason_stop(self):
        line = 'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}'
        assert _parse_sse_content(line) is None


# ── Streaming integration tests ───────────────────────────────


class MockAsyncStreamResponse:
    """Simulates an httpx async streaming response."""

    def __init__(self, status_code: int, sse_lines: list[str]) -> None:
        self.status_code = status_code
        self._lines = sse_lines

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    async def aread(self):
        return b"error response body"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class MockAsyncClient:
    """Simulates httpx.AsyncClient with a canned stream response."""

    def __init__(self, stream_response: MockAsyncStreamResponse) -> None:
        self._response = stream_response

    def stream(self, *args, **kwargs):
        return self._response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


SAMPLE_MESSAGES = [ChatMessage(role="user", content="Is this walkable?")]
SAMPLE_PROFILE = {"center": {"lat": 52.52, "lon": 13.4}, "radius_m": 800}


class TestStreamChatCompletion:
    @patch("app.llm_client.settings")
    @patch("app.llm_client.httpx.AsyncClient")
    async def test_yields_content_chunks(self, mock_client_cls, mock_settings):
        mock_settings.openrouter_api_key = "test-key"

        sse_lines = [
            'data: {"choices":[{"delta":{"role":"assistant"}}]}',
            'data: {"choices":[{"delta":{"content":"hello"}}]}',
            'data: {"choices":[{"delta":{"content":" world"}}]}',
            "data: [DONE]",
        ]
        mock_client_cls.return_value = MockAsyncClient(
            MockAsyncStreamResponse(200, sse_lines),
        )

        chunks = []
        async for chunk in stream_chat_completion(
            messages=SAMPLE_MESSAGES,
            region_profile=SAMPLE_PROFILE,
            model_id="test/model",
        ):
            chunks.append(chunk)

        assert chunks == ["hello", " world"]

    @patch("app.llm_client.settings")
    @patch("app.llm_client.httpx.AsyncClient")
    async def test_yields_structured_json(self, mock_client_cls, mock_settings):
        mock_settings.openrouter_api_key = "test-key"

        structured = json.dumps({
            "answer": "Test answer",
            "reasoning_summary": "Test reasoning",
            "evidence": ["fact"],
            "limitations": ["none"],
            "confidence": "high",
        })
        sse_lines = [
            f'data: {{"choices":[{{"delta":{{"content":{json.dumps(structured)}}}}}]}}',
            "data: [DONE]",
        ]
        mock_client_cls.return_value = MockAsyncClient(
            MockAsyncStreamResponse(200, sse_lines),
        )

        accumulated = ""
        async for chunk in stream_chat_completion(
            messages=SAMPLE_MESSAGES,
            region_profile=SAMPLE_PROFILE,
            model_id="test/model",
        ):
            accumulated += chunk

        parsed = json.loads(accumulated)
        assert parsed["answer"] == "Test answer"
        assert parsed["confidence"] == "high"

    @patch("app.llm_client.settings")
    @patch("app.llm_client.httpx.AsyncClient")
    async def test_raises_on_non_200_response(self, mock_client_cls, mock_settings):
        mock_settings.openrouter_api_key = "test-key"

        mock_client_cls.return_value = MockAsyncClient(
            MockAsyncStreamResponse(429, []),
        )

        with pytest.raises(RuntimeError, match="429"):
            async for _ in stream_chat_completion(
                messages=SAMPLE_MESSAGES,
                region_profile=SAMPLE_PROFILE,
                model_id="test/model",
            ):
                pass

    @patch("app.llm_client.settings")
    async def test_raises_when_api_key_missing(self, mock_settings):
        mock_settings.openrouter_api_key = ""

        with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
            async for _ in stream_chat_completion(
                messages=SAMPLE_MESSAGES,
                region_profile=SAMPLE_PROFILE,
                model_id="test/model",
            ):
                pass

    @patch("app.llm_client.settings")
    @patch("app.llm_client.httpx.AsyncClient")
    async def test_skips_non_content_lines(self, mock_client_cls, mock_settings):
        mock_settings.openrouter_api_key = "test-key"

        sse_lines = [
            ": keepalive comment",
            "",
            'data: {"choices":[{"delta":{"role":"assistant"}}]}',
            'data: {"choices":[{"delta":{"content":"only"}}]}',
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        mock_client_cls.return_value = MockAsyncClient(
            MockAsyncStreamResponse(200, sse_lines),
        )

        chunks = []
        async for chunk in stream_chat_completion(
            messages=SAMPLE_MESSAGES,
            region_profile=SAMPLE_PROFILE,
            model_id="test/model",
        ):
            chunks.append(chunk)

        assert chunks == ["only"]

    @patch("app.llm_client.settings")
    @patch("app.llm_client.httpx.AsyncClient")
    async def test_empty_stream_yields_nothing(self, mock_client_cls, mock_settings):
        mock_settings.openrouter_api_key = "test-key"

        mock_client_cls.return_value = MockAsyncClient(
            MockAsyncStreamResponse(200, ["data: [DONE]"]),
        )

        chunks = []
        async for chunk in stream_chat_completion(
            messages=SAMPLE_MESSAGES,
            region_profile=SAMPLE_PROFILE,
            model_id="test/model",
        ):
            chunks.append(chunk)

        assert chunks == []
