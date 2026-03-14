"""Tests for the profile aggregator."""

from __future__ import annotations


from app.datasources.base import NormalizedFeature, SourceFeatureSet
from app.profile_aggregator import (
    _haversine_m,
    aggregate,
)


class TestHaversine:
    def test_same_point_is_zero(self):
        assert _haversine_m(52.52, 13.405, 52.52, 13.405) == 0.0

    def test_known_distance(self):
        d = _haversine_m(52.52, 13.405, 52.53, 13.405)
        assert 1100 < d < 1120

    def test_symmetry(self):
        d1 = _haversine_m(52.52, 13.405, 52.53, 13.41)
        d2 = _haversine_m(52.53, 13.41, 52.52, 13.405)
        assert abs(d1 - d2) < 0.01


class TestAggregate:
    def test_region_profile_structure(self, berlin_region, sample_feature_set):
        profile, _ = aggregate(berlin_region, [sample_feature_set])

        assert profile["center"] == {"lat": 52.52, "lon": 13.405}
        assert profile["radius_m"] == 800
        assert "counts" in profile
        assert "nearest" in profile
        assert "mobility" in profile
        assert "land_use" in profile
        assert "poi_examples" in profile
        assert "data_quality_notes" in profile

    def test_counts(self, berlin_region, sample_feature_set):
        profile, _ = aggregate(berlin_region, [sample_feature_set])
        counts = profile["counts"]

        assert counts["amenity"]["cafe"] == 1
        assert counts["amenity"]["restaurant"] == 1
        assert counts["healthcare"]["pharmacy"] == 1
        assert counts["education"]["school"] == 1
        assert counts["mobility"]["bus_stop"] == 1
        assert counts["mobility"]["tram_stop"] == 1
        assert counts["shopping"]["supermarket"] == 1
        assert counts["leisure"]["park"] == 1

    def test_nearest_contains_distance(self, berlin_region, sample_feature_set):
        profile, _ = aggregate(berlin_region, [sample_feature_set])
        nearest = profile["nearest"]

        for key, value in nearest.items():
            assert "distance_m" in value
            assert value["distance_m"] >= 0
            assert "lat" in value
            assert "lon" in value

    def test_mobility_counts_transit(self, berlin_region, sample_feature_set):
        profile, _ = aggregate(berlin_region, [sample_feature_set])
        mobility = profile["mobility"]

        assert mobility.get("bus_stop", 0) == 1
        assert mobility.get("tram_stop", 0) == 1

    def test_poi_examples_has_names(self, berlin_region, sample_feature_set):
        profile, _ = aggregate(berlin_region, [sample_feature_set])
        examples = profile["poi_examples"]

        assert "cafe" in examples
        assert "Café Berlin" in examples["cafe"]

    def test_map_features_are_geojson(self, berlin_region, sample_feature_set):
        _, map_features = aggregate(berlin_region, [sample_feature_set])

        assert len(map_features) == len(sample_feature_set.features)
        for f in map_features:
            assert f["type"] == "Feature"
            assert f["geometry"]["type"] == "Point"
            assert len(f["geometry"]["coordinates"]) == 2
            assert "category" in f["properties"]
            assert "subcategory" in f["properties"]

    def test_map_features_coordinates_are_lon_lat(self, berlin_region, sample_feature_set):
        _, map_features = aggregate(berlin_region, [sample_feature_set])
        cafe_feat = next(
            f for f in map_features if f["properties"]["id"] == "osm:node:100"
        )
        lon, lat = cafe_feat["geometry"]["coordinates"]
        assert lat == 52.521
        assert lon == 13.406

    def test_empty_feature_sets(self, berlin_region):
        profile, map_features = aggregate(berlin_region, [])
        assert profile["counts"] == {}
        assert profile["nearest"] == {}
        assert profile["mobility"] == {}
        assert map_features == []

    def test_quality_notes_propagated(self, berlin_region):
        fs = SourceFeatureSet(
            source_name="test",
            quality_notes=["Coverage may be sparse"],
        )
        profile, _ = aggregate(berlin_region, [fs])
        assert any("Coverage" in n for n in profile["data_quality_notes"])

    def test_deduplication_across_sources(self, berlin_region):
        feature = NormalizedFeature(
            feature_id="osm:node:1", source="overpass",
            category="amenity", subcategory="cafe",
            name="Dup Cafe", lat=52.52, lon=13.405,
        )
        fs1 = SourceFeatureSet(source_name="source_a", features=[feature])
        fs2 = SourceFeatureSet(source_name="source_b", features=[feature])

        _, map_features = aggregate(berlin_region, [fs1, fs2])
        assert len(map_features) == 1


class TestAggregateWithMultipleSources:
    def test_merges_features_from_multiple_sources(self, berlin_region):
        fs1 = SourceFeatureSet(
            source_name="overpass",
            features=[
                NormalizedFeature(
                    feature_id="osm:node:1", source="overpass",
                    category="amenity", subcategory="cafe",
                    name="Café A", lat=52.521, lon=13.406,
                ),
            ],
        )
        fs2 = SourceFeatureSet(
            source_name="other_provider",
            features=[
                NormalizedFeature(
                    feature_id="other:1", source="other_provider",
                    category="amenity", subcategory="restaurant",
                    name="Restaurant B", lat=52.519, lon=13.404,
                ),
            ],
        )

        profile, map_features = aggregate(berlin_region, [fs1, fs2])

        assert profile["counts"]["amenity"]["cafe"] == 1
        assert profile["counts"]["amenity"]["restaurant"] == 1
        assert len(map_features) == 2
