"""
Overpass API data source implementation.
Implementation: Part C.
"""

from app.datasources.base import DataSource, SourceFeatureSet
from app.schemas import RegionSpec


class OverpassDataSource(DataSource):
    @property
    def source_name(self) -> str:
        return "overpass"

    async def fetch(self, region: RegionSpec) -> SourceFeatureSet:
        raise NotImplementedError
