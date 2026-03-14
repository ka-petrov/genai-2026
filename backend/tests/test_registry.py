"""Tests for DataSourceRegistry."""

from __future__ import annotations

import pytest

from app.datasources.base import DataSource, SourceFeatureSet, NormalizedFeature
from app.datasources.registry import DataSourceRegistry
from app.schemas import RegionSpec


class FakeDataSource(DataSource):
    def __init__(self, name: str, features: list[NormalizedFeature] | None = None):
        self._name = name
        self._features = features or []

    @property
    def source_name(self) -> str:
        return self._name

    async def fetch(self, region: RegionSpec) -> SourceFeatureSet:
        return SourceFeatureSet(
            source_name=self._name,
            features=self._features,
        )


class FailingDataSource(DataSource):
    @property
    def source_name(self) -> str:
        return "failing"

    async def fetch(self, region: RegionSpec) -> SourceFeatureSet:
        raise RuntimeError("simulated provider failure")


class TestDataSourceRegistry:
    def test_register_and_list(self):
        reg = DataSourceRegistry()
        ds = FakeDataSource("test")
        reg.register(ds)

        assert len(reg.sources) == 1
        assert reg.source_names == ["test"]

    @pytest.mark.asyncio
    async def test_fetch_all_single_source(self, berlin_region):
        reg = DataSourceRegistry()
        reg.register(FakeDataSource("alpha"))
        results = await reg.fetch_all(berlin_region)

        assert len(results) == 1
        assert results[0].source_name == "alpha"

    @pytest.mark.asyncio
    async def test_fetch_all_multiple_sources(self, berlin_region):
        reg = DataSourceRegistry()
        reg.register(FakeDataSource("a"))
        reg.register(FakeDataSource("b"))
        results = await reg.fetch_all(berlin_region)

        assert len(results) == 2
        names = {r.source_name for r in results}
        assert names == {"a", "b"}

    @pytest.mark.asyncio
    async def test_fetch_all_no_sources(self, berlin_region):
        reg = DataSourceRegistry()
        results = await reg.fetch_all(berlin_region)
        assert results == []

    @pytest.mark.asyncio
    async def test_failing_source_does_not_block_others(self, berlin_region):
        reg = DataSourceRegistry()
        reg.register(FakeDataSource("good"))
        reg.register(FailingDataSource())

        results = await reg.fetch_all(berlin_region)

        assert len(results) == 2
        good = next(r for r in results if r.source_name == "good")
        failing = next(r for r in results if r.source_name == "failing")

        assert good.features == []  # empty because FakeDataSource has no features
        assert any("RuntimeError" in n for n in failing.quality_notes)

    @pytest.mark.asyncio
    async def test_sources_list_is_copy(self):
        reg = DataSourceRegistry()
        reg.register(FakeDataSource("x"))
        sources = reg.sources
        sources.clear()
        assert len(reg.sources) == 1
