"""
DataSource registry — discovers and orchestrates all registered providers.
Implementation: Part C.
"""

from __future__ import annotations

from app.datasources.base import DataSource


class DataSourceRegistry:
    def __init__(self) -> None:
        self._sources: list[DataSource] = []

    def register(self, source: DataSource) -> None:
        self._sources.append(source)

    @property
    def sources(self) -> list[DataSource]:
        return list(self._sources)
