"""Aggregates and fuses data from multiple DataSource providers
into a canonical region_profile + map_features."""

from __future__ import annotations

import math
from collections import defaultdict

from app.datasources.base import NormalizedFeature, SourceFeatureSet
from app.schemas import RegionSpec

MAX_POI_EXAMPLES = 5


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two WGS-84 points."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _merge_features(feature_sets: list[SourceFeatureSet]) -> list[NormalizedFeature]:
    seen: set[str] = set()
    merged: list[NormalizedFeature] = []
    for fs in feature_sets:
        for f in fs.features:
            if f.feature_id not in seen:
                seen.add(f.feature_id)
                merged.append(f)
    return merged


def _build_counts(features: list[NormalizedFeature]) -> dict[str, dict[str, int]]:
    """category -> subcategory -> count"""
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for f in features:
        counts[f.category][f.subcategory] += 1
    return {cat: dict(subs) for cat, subs in counts.items()}


def _build_nearest(
    features: list[NormalizedFeature],
    center_lat: float,
    center_lon: float,
) -> dict[str, dict]:
    """For each subcategory, find the closest feature to the center."""
    best: dict[str, tuple[float, NormalizedFeature]] = {}
    for f in features:
        d = _haversine_m(center_lat, center_lon, f.lat, f.lon)
        key = f"{f.category}/{f.subcategory}"
        if key not in best or d < best[key][0]:
            best[key] = (d, f)

    return {
        key: {
            "name": feat.name,
            "distance_m": round(dist, 1),
            "lat": feat.lat,
            "lon": feat.lon,
        }
        for key, (dist, feat) in best.items()
    }


_MOBILITY_SUBCATS = frozenset({
    "bus_stop", "transit_stop", "transit_station",
    "rail_station", "rail_halt", "tram_stop",
    "subway_entrance", "parking", "bike_parking",
    "crossing", "cycleway",
})


def _build_mobility(features: list[NormalizedFeature]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for f in features:
        if f.subcategory in _MOBILITY_SUBCATS:
            counts[f.subcategory] += 1
    return dict(counts)


def _build_land_use(features: list[NormalizedFeature]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for f in features:
        if f.category == "land_use":
            counts[f.subcategory] += 1
    return dict(counts)


def _build_poi_examples(
    features: list[NormalizedFeature],
) -> dict[str, list[str]]:
    """Up to MAX_POI_EXAMPLES named POIs per subcategory, for LLM grounding."""
    buckets: dict[str, list[str]] = defaultdict(list)
    for f in features:
        if f.name and len(buckets[f.subcategory]) < MAX_POI_EXAMPLES:
            buckets[f.subcategory].append(f.name)
    return dict(buckets)


def _collect_quality_notes(feature_sets: list[SourceFeatureSet]) -> list[str]:
    notes: list[str] = []
    for fs in feature_sets:
        for note in fs.quality_notes:
            notes.append(f"[{fs.source_name}] {note}")
    return notes


def _feature_to_geojson(f: NormalizedFeature) -> dict:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [f.lon, f.lat],
        },
        "properties": {
            "id": f.feature_id,
            "source": f.source,
            "category": f.category,
            "subcategory": f.subcategory,
            "name": f.name,
        },
    }


def aggregate(
    region: RegionSpec,
    feature_sets: list[SourceFeatureSet],
) -> tuple[dict, list[dict]]:
    """Produce (region_profile, map_features) from source feature sets.

    Returns:
        region_profile: compact JSON structure consumed by the LLM prompt.
        map_features: list of GeoJSON Feature dicts for map overlay rendering.
    """
    all_features = _merge_features(feature_sets)

    region_profile = {
        "center": {"lat": region.lat, "lon": region.lon},
        "radius_m": region.radius_m,
        "counts": _build_counts(all_features),
        "nearest": _build_nearest(all_features, region.lat, region.lon),
        "mobility": _build_mobility(all_features),
        "land_use": _build_land_use(all_features),
        "poi_examples": _build_poi_examples(all_features),
        "data_quality_notes": _collect_quality_notes(feature_sets),
    }

    map_features = [_feature_to_geojson(f) for f in all_features]

    return region_profile, map_features
