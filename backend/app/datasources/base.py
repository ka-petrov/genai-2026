from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.schemas import RegionSpec

logger = logging.getLogger(__name__)


class NormalizedFeature(BaseModel):
    """A single geospatial feature normalized to a common schema across all data sources."""

    feature_id: str
    source: str
    category: str
    subcategory: str
    name: str | None = None
    lat: float
    lon: float
    tags: dict[str, str] = Field(default_factory=dict)


class SourceFeatureSet(BaseModel):
    """Canonical result returned by any DataSource provider."""

    source_name: str
    features: list[NormalizedFeature] = Field(default_factory=list)
    quality_notes: list[str] = Field(default_factory=list)
    fetched_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DataSource(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str: ...

    @abstractmethod
    async def fetch(self, region: RegionSpec) -> SourceFeatureSet:
        """Fetch features within the given region. Must not raise on provider
        errors — return an empty SourceFeatureSet with quality_notes instead."""
        ...

    async def health_check(self) -> bool:
        """Optional liveness probe; defaults to True."""
        return True
