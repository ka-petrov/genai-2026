"""Tests for ContextStore using an in-memory fake Redis."""

from __future__ import annotations

import json

import pytest

from app.cache.context_store import ContextStore
from app.schemas import RegionSpec


class FakeRedis:
    """Minimal async Redis stand-in backed by a plain dict."""

    def __init__(self, data: dict[str, str] | None = None) -> None:
        self._store: dict[str, str] = dict(data) if data else {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, *, ex: int | None = None) -> None:
        self._store[key] = value

    async def ping(self) -> bool:
        return True


BERLIN = RegionSpec(lat=52.52, lon=13.405, radius_m=800)

PROFILE = {"center": {"lat": 52.52, "lon": 13.405}, "radius_m": 800, "counts": {}}
MAP_FEATURES = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [13.405, 52.52]}}]
DATA_SOURCES = ["overpass"]


@pytest.fixture
def store() -> ContextStore:
    return ContextStore(FakeRedis())


class TestNewContextId:
    def test_format(self):
        cid = ContextStore.new_context_id()
        assert cid.startswith("ctx_")
        assert len(cid) == 16  # "ctx_" + 12 hex chars

    def test_unique(self):
        ids = {ContextStore.new_context_id() for _ in range(100)}
        assert len(ids) == 100


class TestContextLifecycle:
    async def test_create_and_retrieve(self, store: ContextStore):
        ctx_id = await store.create_context(BERLIN, PROFILE, MAP_FEATURES, DATA_SOURCES)
        ctx = await store.get_context(ctx_id)

        assert ctx is not None
        assert ctx["region_profile"] == PROFILE
        assert ctx["map_features"] == MAP_FEATURES
        assert ctx["data_sources"] == DATA_SOURCES
        assert ctx["region_spec"] == BERLIN.model_dump()
        assert "created_at" in ctx

    async def test_missing_context_returns_none(self, store: ContextStore):
        assert await store.get_context("ctx_nonexistent") is None


class TestRegionCache:
    async def test_miss_returns_none(self, store: ContextStore):
        assert await store.get_cached_region(BERLIN) is None

    async def test_store_and_hit(self, store: ContextStore):
        await store.store_region_cache(BERLIN, PROFILE, MAP_FEATURES, DATA_SOURCES)
        cached = await store.get_cached_region(BERLIN)

        assert cached is not None
        assert cached["region_profile"] == PROFILE
        assert cached["map_features"] == MAP_FEATURES
        assert cached["data_sources"] == DATA_SOURCES
        assert "generated_at" in cached

    async def test_nearby_coords_share_cache(self, store: ContextStore):
        """Two RegionSpecs within the rounding window should hit the same cache."""
        region_a = RegionSpec(lat=52.52001, lon=13.40501, radius_m=800)
        region_b = RegionSpec(lat=52.52004, lon=13.40504, radius_m=800)

        await store.store_region_cache(region_a, PROFILE, MAP_FEATURES, DATA_SOURCES)
        cached = await store.get_cached_region(region_b)
        assert cached is not None


class TestLastModel:
    async def test_store_last_model(self, store: ContextStore):
        ctx_id = await store.create_context(BERLIN, PROFILE, MAP_FEATURES, DATA_SOURCES)
        await store.store_last_model(ctx_id, "test-model")

        fake_redis: FakeRedis = store._r  # type: ignore[assignment]
        raw = await fake_redis.get(f"v1:chat:last_model:{ctx_id}")
        assert raw == "test-model"
