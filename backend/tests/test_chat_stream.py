"""Tests for the SSE chat-stream event generator."""

from __future__ import annotations

import json

import pytest

from app.chat_stream import generate_chat_events
from app.schemas import AssistantTurnStructured


VALID_STRUCTURED = AssistantTurnStructured(
    answer="Test answer",
    reasoning_summary="Test reasoning",
    evidence=["fact A"],
    limitations=["limit X"],
    confidence="high",
)


async def _collect_events(gen) -> list[dict]:
    events = []
    async for ev in gen:
        events.append(ev)
    return events


def _make_structured_stream():
    """Async generator yielding valid AssistantTurnStructured JSON in chunks."""
    text = VALID_STRUCTURED.model_dump_json()
    chunk_size = 30

    async def gen():
        for i in range(0, len(text), chunk_size):
            yield text[i : i + chunk_size]

    return gen()


def _make_plain_text_stream():
    """Async generator yielding plain prose (not JSON)."""
    async def gen():
        yield "This is just "
        yield "plain text."

    return gen()


def _make_failing_stream():
    """Async generator that raises mid-stream."""
    async def gen():
        yield "partial "
        raise RuntimeError("boom")

    return gen()


class TestChatStreamLifecycle:
    async def test_started_event_is_first(self):
        events = await _collect_events(generate_chat_events(
            request_id="r1",
            context_id="ctx_test",
            model_id="m1",
            llm_stream=_make_structured_stream(),
        ))
        assert events[0]["event"] == "response.started"
        meta = json.loads(events[0]["data"])
        assert meta["request_id"] == "r1"
        assert meta["context_id"] == "ctx_test"
        assert meta["model_id"] == "m1"

    async def test_delta_events_emitted(self):
        events = await _collect_events(generate_chat_events(
            request_id="r1",
            context_id="ctx_test",
            model_id="m1",
            llm_stream=_make_structured_stream(),
        ))
        deltas = [e for e in events if e["event"] == "response.delta"]
        assert len(deltas) >= 1
        for d in deltas:
            payload = json.loads(d["data"])
            assert "delta" in payload

    async def test_completed_event_with_valid_json(self):
        events = await _collect_events(generate_chat_events(
            request_id="r1",
            context_id="ctx_test",
            model_id="m1",
            llm_stream=_make_structured_stream(),
        ))
        completed = [e for e in events if e["event"] == "response.completed"]
        assert len(completed) == 1
        parsed = json.loads(completed[0]["data"])
        assert parsed["answer"] == "Test answer"
        assert parsed["confidence"] == "high"

    async def test_event_order(self):
        events = await _collect_events(generate_chat_events(
            request_id="r1",
            context_id="ctx_test",
            model_id="m1",
            llm_stream=_make_structured_stream(),
        ))
        types = [e["event"] for e in events]
        assert types[0] == "response.started"
        assert types[-1] == "response.completed"
        assert all(t == "response.delta" for t in types[1:-1])


class TestChatStreamFallback:
    async def test_plain_text_triggers_fallback(self):
        events = await _collect_events(generate_chat_events(
            request_id="r1",
            context_id="ctx_test",
            model_id="m1",
            llm_stream=_make_plain_text_stream(),
        ))
        completed = [e for e in events if e["event"] == "response.completed"]
        assert len(completed) == 1
        parsed = json.loads(completed[0]["data"])
        assert parsed["answer"] == "This is just plain text."
        assert parsed["confidence"] == "low"
        assert any("not in expected structured format" in l for l in parsed["limitations"])


class TestChatStreamError:
    async def test_stream_error_emits_error_event(self):
        events = await _collect_events(generate_chat_events(
            request_id="r1",
            context_id="ctx_test",
            model_id="m1",
            llm_stream=_make_failing_stream(),
        ))
        error_events = [e for e in events if e["event"] == "response.error"]
        assert len(error_events) == 1
        payload = json.loads(error_events[0]["data"])
        assert payload["error"]["code"] == "LLM_STREAM_ERROR"
        assert payload["error"]["retryable"] is True
        assert payload["meta"]["request_id"] == "r1"

    async def test_no_completed_event_after_error(self):
        events = await _collect_events(generate_chat_events(
            request_id="r1",
            context_id="ctx_test",
            model_id="m1",
            llm_stream=_make_failing_stream(),
        ))
        completed = [e for e in events if e["event"] == "response.completed"]
        assert len(completed) == 0
