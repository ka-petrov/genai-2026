"""Convert raw Overpass JSON elements into NormalizedFeature instances."""

from __future__ import annotations

import logging

from app.datasources.base import NormalizedFeature
from app.datasources.osm_normalizer import classify_osm_tags, extract_name

logger = logging.getLogger(__name__)


def _element_coords(element: dict) -> tuple[float, float] | None:
    """Extract (lat, lon) from an Overpass element.
    Nodes have top-level lat/lon; ways/relations use the ``center`` sub-object
    (requires ``out center`` in the query)."""
    if "lat" in element and "lon" in element:
        return element["lat"], element["lon"]
    center = element.get("center")
    if center and "lat" in center and "lon" in center:
        return center["lat"], center["lon"]
    return None


def extract_features_from_overpass(elements: list[dict]) -> list[NormalizedFeature]:
    """Parse a list of raw Overpass ``elements`` into normalized features.
    Elements that lack coordinates or don't match the taxonomy are silently
    skipped (logged at DEBUG)."""
    features: list[NormalizedFeature] = []
    for el in elements:
        coords = _element_coords(el)
        if coords is None:
            logger.debug("Skipping element %s: no coordinates", el.get("id"))
            continue

        tags = el.get("tags", {})
        classification = classify_osm_tags(tags)
        if classification is None:
            continue

        category, subcategory = classification
        lat, lon = coords

        feature = NormalizedFeature(
            feature_id=f"osm:{el.get('type', 'node')}:{el.get('id', 0)}",
            source="overpass",
            category=category,
            subcategory=subcategory,
            name=extract_name(tags),
            lat=lat,
            lon=lon,
            tags=tags,
        )
        features.append(feature)

    logger.info(
        "Extracted %d features from %d Overpass elements",
        len(features),
        len(elements),
    )
    return features
