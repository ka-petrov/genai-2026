from __future__ import annotations

import pytest

from app.datasources.base import NormalizedFeature, SourceFeatureSet
from app.schemas import RegionSpec

BERLIN_CENTER = RegionSpec(lat=52.52, lon=13.405, radius_m=800)


@pytest.fixture
def berlin_region() -> RegionSpec:
    return BERLIN_CENTER


SAMPLE_OVERPASS_RESPONSE: dict = {
    "version": 0.6,
    "generator": "Overpass API",
    "osm3s": {"timestamp_osm_base": "2024-01-01T00:00:00Z"},
    "elements": [
        {
            "type": "node",
            "id": 100,
            "lat": 52.521,
            "lon": 13.406,
            "tags": {"amenity": "cafe", "name": "Café Berlin"},
        },
        {
            "type": "node",
            "id": 101,
            "lat": 52.519,
            "lon": 13.404,
            "tags": {"amenity": "restaurant", "name": "Zum Goldenen Bären"},
        },
        {
            "type": "node",
            "id": 102,
            "lat": 52.522,
            "lon": 13.408,
            "tags": {"amenity": "pharmacy", "name": "Apotheke am Platz"},
        },
        {
            "type": "node",
            "id": 103,
            "lat": 52.518,
            "lon": 13.401,
            "tags": {"amenity": "school", "name": "Grundschule Mitte"},
        },
        {
            "type": "node",
            "id": 104,
            "lat": 52.5205,
            "lon": 13.4035,
            "tags": {"highway": "bus_stop", "name": "Alexanderplatz"},
        },
        {
            "type": "node",
            "id": 105,
            "lat": 52.5215,
            "lon": 13.4115,
            "tags": {"railway": "tram_stop", "name": "Hackescher Markt"},
        },
        {
            "type": "node",
            "id": 106,
            "lat": 52.5225,
            "lon": 13.4125,
            "tags": {"shop": "supermarket", "name": "REWE"},
        },
        {
            "type": "way",
            "id": 200,
            "center": {"lat": 52.519, "lon": 13.407},
            "tags": {"leisure": "park", "name": "Monbijoupark"},
        },
        {
            "type": "way",
            "id": 201,
            "center": {"lat": 52.517, "lon": 13.402},
            "tags": {"landuse": "residential"},
        },
        {
            "type": "node",
            "id": 107,
            "lat": 52.520,
            "lon": 13.405,
            "tags": {"tourism": "museum", "name": "Altes Museum"},
        },
        {
            "type": "way",
            "id": 202,
            "center": {"lat": 52.5195, "lon": 13.4060},
            "tags": {"highway": "residential", "name": "Karl-Liebknecht-Straße"},
        },
        {
            "type": "node",
            "id": 108,
            "lat": 52.5200,
            "lon": 13.4050,
            "tags": {"place": "suburb", "name": "Mitte"},
        },
        {
            "type": "way",
            "id": 203,
            "center": {"lat": 52.5130, "lon": 13.3990},
            "tags": {"waterway": "river", "name": "Spree"},
        },
        {
            "type": "way",
            "id": 204,
            "center": {"lat": 52.5180, "lon": 13.4100},
            "tags": {"natural": "water", "name": "Spreekanal"},
        },
        # Element with no matching tags — should be skipped
        {
            "type": "node",
            "id": 999,
            "lat": 52.520,
            "lon": 13.405,
            "tags": {"barrier": "fence"},
        },
        # Element with no coords — should be skipped
        {
            "type": "way",
            "id": 998,
            "tags": {"amenity": "cafe", "name": "Ghost Cafe"},
        },
    ],
}


@pytest.fixture
def sample_overpass_elements() -> list[dict]:
    return SAMPLE_OVERPASS_RESPONSE["elements"]


@pytest.fixture
def sample_feature_set() -> SourceFeatureSet:
    """Pre-built feature set matching the sample Overpass response."""
    features = [
        NormalizedFeature(
            feature_id="osm:node:100", source="overpass",
            category="amenity", subcategory="cafe",
            name="Café Berlin", lat=52.521, lon=13.406,
        ),
        NormalizedFeature(
            feature_id="osm:node:101", source="overpass",
            category="amenity", subcategory="restaurant",
            name="Zum Goldenen Bären", lat=52.519, lon=13.404,
        ),
        NormalizedFeature(
            feature_id="osm:node:102", source="overpass",
            category="healthcare", subcategory="pharmacy",
            name="Apotheke am Platz", lat=52.522, lon=13.408,
        ),
        NormalizedFeature(
            feature_id="osm:node:103", source="overpass",
            category="education", subcategory="school",
            name="Grundschule Mitte", lat=52.518, lon=13.401,
        ),
        NormalizedFeature(
            feature_id="osm:node:104", source="overpass",
            category="mobility", subcategory="bus_stop",
            name="Alexanderplatz", lat=52.5205, lon=13.4035,
        ),
        NormalizedFeature(
            feature_id="osm:node:105", source="overpass",
            category="mobility", subcategory="tram_stop",
            name="Hackescher Markt", lat=52.5215, lon=13.4115,
        ),
        NormalizedFeature(
            feature_id="osm:node:106", source="overpass",
            category="shopping", subcategory="supermarket",
            name="REWE", lat=52.5225, lon=13.4125,
        ),
        NormalizedFeature(
            feature_id="osm:way:200", source="overpass",
            category="leisure", subcategory="park",
            name="Monbijoupark", lat=52.519, lon=13.407,
        ),
        NormalizedFeature(
            feature_id="osm:way:202", source="overpass",
            category="street", subcategory="residential",
            name="Karl-Liebknecht-Straße", lat=52.5195, lon=13.4060,
        ),
        NormalizedFeature(
            feature_id="osm:node:108", source="overpass",
            category="place", subcategory="suburb",
            name="Mitte", lat=52.5200, lon=13.4050,
        ),
        NormalizedFeature(
            feature_id="osm:way:203", source="overpass",
            category="waterway", subcategory="river",
            name="Spree", lat=52.5130, lon=13.3990,
        ),
        NormalizedFeature(
            feature_id="osm:way:204", source="overpass",
            category="natural", subcategory="water",
            name="Spreekanal", lat=52.5180, lon=13.4100,
        ),
    ]
    return SourceFeatureSet(
        source_name="overpass",
        features=features,
        fetched_at="2024-01-01T00:00:00+00:00",
    )
