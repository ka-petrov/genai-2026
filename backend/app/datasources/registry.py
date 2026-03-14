"""DataSource registry — discovers and orchestrates all registered providers."""

from __future__ import annotations

import asyncio
import logging

from app.datasources.base import DataSource, SourceFeatureSet
from app.schemas import RegionSpec

logger = logging.getLogger(__name__)


class DataSourceRegistry:
    def __init__(self) -> None:
        self._sources: list[DataSource] = []

    def register(self, source: DataSource) -> None:
        self._sources.append(source)
        logger.info("Registered data source: %s", source.source_name)

    @property
    def sources(self) -> list[DataSource]:
        return list(self._sources)

    @property
    def source_names(self) -> list[str]:
        return [s.source_name for s in self._sources]

    async def fetch_all(self, region: RegionSpec) -> list[SourceFeatureSet]:
        """Fetch from all registered sources concurrently.
        Individual source failures are captured in quality_notes rather than
        propagated, so one failing provider doesn't block the others."""
        if not self._sources:
            logger.warning("No data sources registered")
            return []

        tasks = [source.fetch(region) for source in self._sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        feature_sets: list[SourceFeatureSet] = []
        for source, result in zip(self._sources, results):
            if isinstance(result, Exception):
                logger.error(
                    "Data source %s raised %s: %s",
                    source.source_name,
                    type(result).__name__,
                    result,
                )
                feature_sets.append(
                    SourceFeatureSet(
                        source_name=source.source_name,
                        quality_notes=[
                            f"Provider error: {type(result).__name__}: {result}"
                        ],
                    )
                )
            else:
                feature_sets.append(result)

        return feature_sets
