"""Tests for OverpassDataSource with mocked HTTP transport."""

from __future__ import annotations

import json

import httpx
import pytest

from app.datasources.overpass import OverpassDataSource, build_overpass_query
from app.schemas import RegionSpec
from tests.conftest import SAMPLE_OVERPASS_RESPONSE


class TestBuildOverpassQuery:
    def test_contains_coordinates(self, berlin_region: RegionSpec):
        q = build_overpass_query(berlin_region)
        assert "52.52" in q
        assert "13.405" in q
        assert "800" in q

    def test_contains_tag_selectors(self, berlin_region: RegionSpec):
        q = build_overpass_query(berlin_region)
        for tag in ["amenity", "shop", "leisure", "tourism", "public_transport", "railway", "highway", "landuse"]:
            assert f'"{tag}"' in q

    def test_requests_center_output(self, berlin_region: RegionSpec):
        q = build_overpass_query(berlin_region)
        assert "out center body" in q

    def test_json_output_format(self, berlin_region: RegionSpec):
        q = build_overpass_query(berlin_region)
        assert "[out:json]" in q


def _mock_transport(response_json: dict, status_code: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=response_json)
    return httpx.MockTransport(handler)


def _timeout_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("simulated timeout")
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
class TestOverpassDataSourceFetch:
    async def test_successful_fetch(self, berlin_region: RegionSpec):
        client = httpx.AsyncClient(transport=_mock_transport(SAMPLE_OVERPASS_RESPONSE))
        ds = OverpassDataSource(client=client)

        result = await ds.fetch(berlin_region)

        assert result.source_name == "overpass"
        assert len(result.features) == 10
        assert not result.quality_notes

    async def test_source_name(self):
        ds = OverpassDataSource()
        assert ds.source_name == "overpass"

    async def test_timeout_returns_empty_with_note(self, berlin_region: RegionSpec):
        client = httpx.AsyncClient(transport=_timeout_transport())
        ds = OverpassDataSource(client=client)

        result = await ds.fetch(berlin_region)

        assert result.source_name == "overpass"
        assert len(result.features) == 0
        assert any("timed out" in n for n in result.quality_notes)

    async def test_http_error_returns_empty_with_note(self, berlin_region: RegionSpec):
        client = httpx.AsyncClient(transport=_mock_transport({"error": "rate limited"}, status_code=429))
        ds = OverpassDataSource(client=client)

        result = await ds.fetch(berlin_region)

        assert len(result.features) == 0
        assert any("429" in n for n in result.quality_notes)

    async def test_server_error_returns_empty_with_note(self, berlin_region: RegionSpec):
        client = httpx.AsyncClient(transport=_mock_transport({"error": "internal"}, status_code=500))
        ds = OverpassDataSource(client=client)

        result = await ds.fetch(berlin_region)

        assert len(result.features) == 0
        assert any("500" in n for n in result.quality_notes)

    async def test_empty_response(self, berlin_region: RegionSpec):
        client = httpx.AsyncClient(
            transport=_mock_transport({"elements": []})
        )
        ds = OverpassDataSource(client=client)

        result = await ds.fetch(berlin_region)

        assert len(result.features) == 0
        assert any("No features" in n for n in result.quality_notes)

    async def test_features_are_normalized(self, berlin_region: RegionSpec):
        client = httpx.AsyncClient(transport=_mock_transport(SAMPLE_OVERPASS_RESPONSE))
        ds = OverpassDataSource(client=client)

        result = await ds.fetch(berlin_region)

        categories = {f.category for f in result.features}
        assert "amenity" in categories
        assert "mobility" in categories
        assert "healthcare" in categories

    async def test_fetched_at_populated(self, berlin_region: RegionSpec):
        client = httpx.AsyncClient(transport=_mock_transport(SAMPLE_OVERPASS_RESPONSE))
        ds = OverpassDataSource(client=client)

        result = await ds.fetch(berlin_region)

        assert result.fetched_at is not None
        assert len(result.fetched_at) > 0
