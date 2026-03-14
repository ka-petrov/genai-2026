"""Tests for cache key helpers and region hash computation."""

from app.cache.cache_keys import (
    compute_region_hash,
    context_key,
    last_model_key,
    region_key,
)


class TestKeyFormatting:
    def test_context_key(self):
        assert context_key("ctx_abc123") == "v1:ctx:ctx_abc123"

    def test_region_key(self):
        assert region_key("deadbeef") == "v1:region:deadbeef"

    def test_last_model_key(self):
        assert last_model_key("ctx_abc123") == "v1:chat:last_model:ctx_abc123"


class TestComputeRegionHash:
    def test_deterministic(self):
        h1 = compute_region_hash(52.52, 13.405, 800)
        h2 = compute_region_hash(52.52, 13.405, 800)
        assert h1 == h2

    def test_different_inputs(self):
        h1 = compute_region_hash(52.52, 13.405, 800)
        h2 = compute_region_hash(48.8566, 2.3522, 800)
        assert h1 != h2

    def test_different_radius(self):
        h1 = compute_region_hash(52.52, 13.405, 800)
        h2 = compute_region_hash(52.52, 13.405, 500)
        assert h1 != h2

    def test_rounds_coordinates(self):
        """Coords within the rounding window (4 d.p.) should hash identically."""
        h1 = compute_region_hash(52.52001, 13.40501, 800)
        h2 = compute_region_hash(52.52004, 13.40504, 800)
        assert h1 == h2

    def test_returns_hex_string(self):
        h = compute_region_hash(52.52, 13.405, 800)
        assert len(h) == 16
        int(h, 16)  # should not raise
