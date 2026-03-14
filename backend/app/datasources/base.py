"""
Generic DataSource abstraction.
Implementation: Part C.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas import RegionSpec


class SourceFeatureSet:
    """Canonical result returned by any DataSource provider."""


class DataSource(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str: ...

    @abstractmethod
    async def fetch(self, region: RegionSpec) -> SourceFeatureSet: ...
