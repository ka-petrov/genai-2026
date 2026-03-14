"""Integration tests for the FastAPI routes.

All external dependencies (Redis, data sources, LLM) are replaced with
in-process fakes via FastAPI dependency overrides and unittest.mock.patch.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.cache.context_store import ContextStore
from app.datasources.base import (
    DataSource,
    NormalizedFeature,
    SourceFeatureSet,
)
from app.datasources.registry import DataSourceRegistry
from app.dependencies import get_context_store, get_data_registry
from app.main import app
from app.schemas import AssistantTurnStructured, RegionSpec


# ── Fakes ──────────────────────────────────────────────────────


class FakeRedis:
    def __init__(self, data: dict[str, str] | None = None) -> None:
        self._store: dict[str, str] = dict(data) if data else {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, *, ex: int | None = None) -> None:
        self._store[key] = value

    async def ping(self) -> bool:
        return True


class FakeDataSource(DataSource):
    @property
    def source_name(self) -> str:
        return "fake"

    async def fetch(self, region: RegionSpec) -> SourceFeatureSet:
        return SourceFeatureSet(
            source_name="fake",
            features=[
                NormalizedFeature(
                    feature_id="fake:1",
                    source="fake",
                    category="amenity",
                    subcategory="cafe",
                    name="Test Cafe",
                    lat=region.lat + 0.001,
                    lon=region.lon + 0.001,
                ),
                NormalizedFeature(
                    feature_id="fake:2",
                    source="fake",
                    category="mobility",
                    subcategory="bus_stop",
                    name="Test Stop",
                    lat=region.lat - 0.001,
                    lon=region.lon - 0.001,
                ),
            ],
        )


STUB_STRUCTURED = AssistantTurnStructured(
    answer="Mock answer",
    reasoning_summary="Mock reasoning",
    evidence=["mock evidence"],
    limitations=["mock limitation"],
    confidence="medium",
)


async def _mock_llm_stream(**_kwargs) -> AsyncGenerator[str, None]:
    text = STUB_STRUCTURED.model_dump_json()
    chunk_size = 40
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]


# ── Fixtures ───────────────────────────────────────────────────


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def _override_deps(fake_redis: FakeRedis):
    registry = DataSourceRegistry()
    registry.register(FakeDataSource())
    store = ContextStore(fake_redis)

    app.dependency_overrides[get_context_store] = lambda: store
    app.dependency_overrides[get_data_registry] = lambda: registry
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client(_override_deps) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


def _parse_sse_events(text: str) -> list[dict]:
    """Parse raw SSE text into a list of {event, data} dicts."""
    events: list[dict] = []
    current: dict[str, str] = {}
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.startswith("event:"):
            current["event"] = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current["data"] = line[len("data:"):].strip()
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events


# ── Health ─────────────────────────────────────────────────────


class TestHealth:
    @patch("app.main.redis_health_check", return_value=True)
    async def test_healthy(self, _mock, client: AsyncClient):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["redis"] is True
        assert "data_sources" in body

    @patch("app.main.redis_health_check", return_value=False)
    async def test_degraded_without_redis(self, _mock, client: AsyncClient):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["redis"] is False


# ── POST /api/contexts ─────────────────────────────────────────


class TestCreateContext:
    async def test_creates_context(self, client: AsyncClient, fake_redis: FakeRedis):
        resp = await client.post(
            "/api/contexts",
            json={"region": {"lat": 52.52, "lon": 13.405, "radius_m": 800}},
        )
        assert resp.status_code == 200
        body = resp.json()

        assert body["context_id"].startswith("ctx_")
        assert "region_profile" in body
        assert "map_features" in body
        assert body["meta"]["cache_hit"] is False
        assert body["meta"]["data_sources"] == ["fake"]
        assert "request_id" in body["meta"]

    async def test_region_profile_structure(self, client: AsyncClient):
        resp = await client.post(
            "/api/contexts",
            json={"region": {"lat": 52.52, "lon": 13.405, "radius_m": 800}},
        )
        profile = resp.json()["region_profile"]
        assert profile["center"] == {"lat": 52.52, "lon": 13.405}
        assert profile["radius_m"] == 800
        for key in ("counts", "nearest", "mobility", "land_use", "poi_examples"):
            assert key in profile

    async def test_map_features_are_geojson(self, client: AsyncClient):
        resp = await client.post(
            "/api/contexts",
            json={"region": {"lat": 52.52, "lon": 13.405, "radius_m": 800}},
        )
        features = resp.json()["map_features"]
        assert len(features) == 2
        for f in features:
            assert f["type"] == "Feature"
            assert "geometry" in f
            assert "properties" in f

    async def test_second_request_hits_cache(
        self, client: AsyncClient, fake_redis: FakeRedis,
    ):
        resp1 = await client.post(
            "/api/contexts",
            json={"region": {"lat": 52.52, "lon": 13.405, "radius_m": 800}},
        )
        resp2 = await client.post(
            "/api/contexts",
            json={"region": {"lat": 52.52, "lon": 13.405, "radius_m": 800}},
        )
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp2.json()["meta"]["cache_hit"] is True

    async def test_validation_error(self, client: AsyncClient):
        resp = await client.post("/api/contexts", json={"region": {"lat": "bad"}})
        assert resp.status_code == 422


# ── POST /api/chat/stream ─────────────────────────────────────


class TestChatStream:
    async def _create_context(self, client: AsyncClient) -> str:
        resp = await client.post(
            "/api/contexts",
            json={"region": {"lat": 52.52, "lon": 13.405, "radius_m": 800}},
        )
        return resp.json()["context_id"]

    @patch("app.main.stream_chat_completion", side_effect=_mock_llm_stream)
    async def test_sse_lifecycle(self, _mock, client: AsyncClient):
        ctx_id = await self._create_context(client)
        resp = await client.post(
            "/api/chat/stream",
            json={
                "context_id": ctx_id,
                "messages": [{"role": "user", "content": "Is this walkable?"}],
            },
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        events = _parse_sse_events(resp.text)
        types = [e["event"] for e in events]
        assert types[0] == "response.started"
        assert types[-1] == "response.completed"
        assert all(t == "response.delta" for t in types[1:-1])

    @patch("app.main.stream_chat_completion", side_effect=_mock_llm_stream)
    async def test_completed_contains_structured_payload(
        self, _mock, client: AsyncClient,
    ):
        ctx_id = await self._create_context(client)
        resp = await client.post(
            "/api/chat/stream",
            json={
                "context_id": ctx_id,
                "messages": [{"role": "user", "content": "test"}],
            },
        )
        events = _parse_sse_events(resp.text)
        completed = [e for e in events if e["event"] == "response.completed"][0]
        parsed = json.loads(completed["data"])
        assert parsed["answer"] == "Mock answer"
        assert parsed["confidence"] == "medium"

    @patch("app.main.stream_chat_completion", side_effect=_mock_llm_stream)
    async def test_started_contains_metadata(self, _mock, client: AsyncClient):
        ctx_id = await self._create_context(client)
        resp = await client.post(
            "/api/chat/stream",
            json={
                "context_id": ctx_id,
                "messages": [{"role": "user", "content": "test"}],
            },
        )
        events = _parse_sse_events(resp.text)
        started = json.loads(events[0]["data"])
        assert started["context_id"] == ctx_id
        assert "request_id" in started
        assert "model_id" in started

    async def test_missing_context_returns_404(self, client: AsyncClient):
        resp = await client.post(
            "/api/chat/stream",
            json={
                "context_id": "ctx_doesnotexist",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "CONTEXT_NOT_FOUND"
        assert body["error"]["retryable"] is True

    async def test_validation_error_no_messages(self, client: AsyncClient):
        resp = await client.post(
            "/api/chat/stream",
            json={"context_id": "ctx_x"},
        )
        assert resp.status_code == 422

    @patch("app.main.stream_chat_completion", side_effect=_mock_llm_stream)
    async def test_default_model_id(self, _mock, client: AsyncClient):
        ctx_id = await self._create_context(client)
        resp = await client.post(
            "/api/chat/stream",
            json={
                "context_id": ctx_id,
                "messages": [{"role": "user", "content": "test"}],
            },
        )
        events = _parse_sse_events(resp.text)
        started = json.loads(events[0]["data"])
        assert started["model_id"] == "google/gemini-2.5-flash-preview"

    @patch("app.main.stream_chat_completion", side_effect=_mock_llm_stream)
    async def test_custom_model_id(self, _mock, client: AsyncClient):
        ctx_id = await self._create_context(client)
        resp = await client.post(
            "/api/chat/stream",
            json={
                "context_id": ctx_id,
                "messages": [{"role": "user", "content": "test"}],
                "model_id": "custom/model",
            },
        )
        events = _parse_sse_events(resp.text)
        started = json.loads(events[0]["data"])
        assert started["model_id"] == "custom/model"
