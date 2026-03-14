"""Overpass API data source — fetches OSM features within a circular region."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.datasources.base import DataSource, SourceFeatureSet
from app.datasources.feature_extractors import extract_features_from_overpass
from app.schemas import RegionSpec

logger = logging.getLogger(__name__)

_OVERPASS_QUERY_TEMPLATE = """\
[out:json][timeout:{timeout}];
(
  node["amenity"](around:{radius},{lat},{lon});
  way["amenity"](around:{radius},{lat},{lon});
  node["shop"](around:{radius},{lat},{lon});
  way["shop"](around:{radius},{lat},{lon});
  node["leisure"](around:{radius},{lat},{lon});
  way["leisure"](around:{radius},{lat},{lon});
  node["tourism"](around:{radius},{lat},{lon});
  way["tourism"](around:{radius},{lat},{lon});
  node["public_transport"](around:{radius},{lat},{lon});
  node["railway"~"station|halt|tram_stop|subway_entrance"](around:{radius},{lat},{lon});
  node["highway"="bus_stop"](around:{radius},{lat},{lon});
  way["landuse"](around:{radius},{lat},{lon});
  way["highway"]["name"](around:{radius},{lat},{lon});
  node["place"](around:{radius},{lat},{lon});
  node["natural"]["name"](around:{radius},{lat},{lon});
  way["natural"]["name"](around:{radius},{lat},{lon});
  way["waterway"]["name"](around:{radius},{lat},{lon});
);
out center body;
"""


def build_overpass_query(region: RegionSpec, timeout: int = 25) -> str:
    return _OVERPASS_QUERY_TEMPLATE.format(
        lat=region.lat,
        lon=region.lon,
        radius=region.radius_m,
        timeout=timeout,
    )


class OverpassDataSource(DataSource):
    def __init__(
        self,
        *,
        overpass_url: str | None = None,
        timeout: float | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._url = overpass_url or settings.overpass_url
        self._timeout = timeout or settings.overpass_timeout
        self._external_client = client

    @property
    def source_name(self) -> str:
        return "overpass"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client
        return httpx.AsyncClient(timeout=self._timeout)

    async def fetch(self, region: RegionSpec) -> SourceFeatureSet:
        query = build_overpass_query(region, timeout=int(self._timeout) - 5)
        quality_notes: list[str] = []
        client = await self._get_client()
        owns_client = self._external_client is None

        try:
            response = await client.post(
                self._url,
                data={"data": query},
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException:
            logger.warning("Overpass request timed out for region %s", region)
            quality_notes.append("Overpass API timed out; results may be incomplete")
            return SourceFeatureSet(
                source_name=self.source_name,
                quality_notes=quality_notes,
            )
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Overpass returned HTTP %s for region %s",
                exc.response.status_code,
                region,
            )
            quality_notes.append(
                f"Overpass API returned HTTP {exc.response.status_code}"
            )
            return SourceFeatureSet(
                source_name=self.source_name,
                quality_notes=quality_notes,
            )
        except Exception:
            logger.exception("Unexpected error fetching from Overpass")
            quality_notes.append("Unexpected error contacting Overpass API")
            return SourceFeatureSet(
                source_name=self.source_name,
                quality_notes=quality_notes,
            )
        finally:
            if owns_client:
                await client.aclose()

        elements = payload.get("elements", [])
        logger.info(
            "Overpass returned %d raw elements for (%.4f, %.4f, %dm)",
            len(elements),
            region.lat,
            region.lon,
            region.radius_m,
        )

        features = extract_features_from_overpass(elements)

        if not features:
            quality_notes.append(
                "No features matched the domain taxonomy in this region"
            )

        return SourceFeatureSet(
            source_name=self.source_name,
            features=features,
            quality_notes=quality_notes,
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )

    async def health_check(self) -> bool:
        client = await self._get_client()
        owns_client = self._external_client is None
        try:
            resp = await client.get(
                self._url.replace("/interpreter", "/status"),
                timeout=5.0,
            )
            return resp.status_code == 200
        except Exception:
            return False
        finally:
            if owns_client:
                await client.aclose()
