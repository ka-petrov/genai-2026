from app.datasources.feature_extractors import extract_features_from_overpass


class TestExtractFeaturesFromOverpass:
    def test_basic_node_extraction(self, sample_overpass_elements):
        features = extract_features_from_overpass(sample_overpass_elements)
        ids = [f.feature_id for f in features]
        assert "osm:node:100" in ids
        assert "osm:node:101" in ids

    def test_way_with_center(self, sample_overpass_elements):
        features = extract_features_from_overpass(sample_overpass_elements)
        park = next(f for f in features if f.feature_id == "osm:way:200")
        assert park.lat == 52.519
        assert park.lon == 13.407
        assert park.category == "leisure"
        assert park.subcategory == "park"
        assert park.name == "Monbijoupark"

    def test_skips_elements_without_coords(self, sample_overpass_elements):
        features = extract_features_from_overpass(sample_overpass_elements)
        ids = [f.feature_id for f in features]
        assert "osm:way:998" not in ids

    def test_skips_elements_with_unknown_tags(self, sample_overpass_elements):
        features = extract_features_from_overpass(sample_overpass_elements)
        ids = [f.feature_id for f in features]
        assert "osm:node:999" not in ids

    def test_expected_feature_count(self, sample_overpass_elements):
        features = extract_features_from_overpass(sample_overpass_elements)
        # 10 valid elements with coords, 2 skipped (no coords / unknown tags),
        # but landuse:residential matches -> 10 features total
        assert len(features) == 10

    def test_cafe_classification(self, sample_overpass_elements):
        features = extract_features_from_overpass(sample_overpass_elements)
        cafe = next(f for f in features if f.feature_id == "osm:node:100")
        assert cafe.category == "amenity"
        assert cafe.subcategory == "cafe"
        assert cafe.name == "Café Berlin"
        assert cafe.source == "overpass"

    def test_bus_stop_classification(self, sample_overpass_elements):
        features = extract_features_from_overpass(sample_overpass_elements)
        stop = next(f for f in features if f.feature_id == "osm:node:104")
        assert stop.category == "mobility"
        assert stop.subcategory == "bus_stop"

    def test_empty_elements_list(self):
        assert extract_features_from_overpass([]) == []

    def test_all_features_have_source_overpass(self, sample_overpass_elements):
        features = extract_features_from_overpass(sample_overpass_elements)
        assert all(f.source == "overpass" for f in features)

    def test_all_features_have_coordinates(self, sample_overpass_elements):
        features = extract_features_from_overpass(sample_overpass_elements)
        for f in features:
            assert -90 <= f.lat <= 90
            assert -180 <= f.lon <= 180
