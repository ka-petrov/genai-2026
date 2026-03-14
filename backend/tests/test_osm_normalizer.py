from app.datasources.osm_normalizer import classify_osm_tags, extract_name


class TestClassifyOsmTags:
    def test_amenity_cafe(self):
        assert classify_osm_tags({"amenity": "cafe"}) == ("amenity", "cafe")

    def test_amenity_restaurant(self):
        assert classify_osm_tags({"amenity": "restaurant"}) == ("amenity", "restaurant")

    def test_amenity_fast_food_maps_to_restaurant(self):
        assert classify_osm_tags({"amenity": "fast_food"}) == ("amenity", "restaurant")

    def test_amenity_school_maps_to_education(self):
        assert classify_osm_tags({"amenity": "school"}) == ("education", "school")

    def test_amenity_pharmacy_maps_to_healthcare(self):
        assert classify_osm_tags({"amenity": "pharmacy"}) == ("healthcare", "pharmacy")

    def test_amenity_hospital(self):
        assert classify_osm_tags({"amenity": "hospital"}) == ("healthcare", "hospital")

    def test_amenity_library(self):
        assert classify_osm_tags({"amenity": "library"}) == ("amenity", "library")

    def test_shop_supermarket(self):
        assert classify_osm_tags({"shop": "supermarket"}) == ("shopping", "supermarket")

    def test_shop_convenience(self):
        assert classify_osm_tags({"shop": "convenience"}) == ("shopping", "convenience")

    def test_leisure_park(self):
        assert classify_osm_tags({"leisure": "park"}) == ("leisure", "park")

    def test_leisure_playground(self):
        assert classify_osm_tags({"leisure": "playground"}) == ("leisure", "playground")

    def test_leisure_sports_centre(self):
        assert classify_osm_tags({"leisure": "sports_centre"}) == ("leisure", "sports_centre")

    def test_public_transport_station(self):
        assert classify_osm_tags({"public_transport": "station"}) == ("mobility", "transit_station")

    def test_railway_tram_stop(self):
        assert classify_osm_tags({"railway": "tram_stop"}) == ("mobility", "tram_stop")

    def test_railway_station(self):
        assert classify_osm_tags({"railway": "station"}) == ("mobility", "rail_station")

    def test_highway_bus_stop(self):
        assert classify_osm_tags({"highway": "bus_stop"}) == ("mobility", "bus_stop")

    def test_landuse_residential(self):
        assert classify_osm_tags({"landuse": "residential"}) == ("land_use", "residential")

    def test_landuse_commercial(self):
        assert classify_osm_tags({"landuse": "commercial"}) == ("land_use", "commercial")

    def test_tourism_museum(self):
        assert classify_osm_tags({"tourism": "museum"}) == ("amenity", "museum")

    def test_unknown_tag_returns_none(self):
        assert classify_osm_tags({"barrier": "fence"}) is None

    def test_empty_tags_returns_none(self):
        assert classify_osm_tags({}) is None

    def test_unknown_value_returns_none(self):
        assert classify_osm_tags({"amenity": "unknown_type_xyz"}) is None

    def test_first_matching_tag_wins(self):
        """When an element has both amenity and shop tags, amenity wins
        because it appears first in the dispatch table."""
        result = classify_osm_tags({"amenity": "cafe", "shop": "supermarket"})
        assert result == ("amenity", "cafe")


class TestExtractName:
    def test_name_tag(self):
        assert extract_name({"name": "Café Berlin"}) == "Café Berlin"

    def test_name_en_fallback(self):
        assert extract_name({"name:en": "English Name"}) == "English Name"

    def test_name_preferred_over_name_en(self):
        assert extract_name({"name": "Deutsch", "name:en": "English"}) == "Deutsch"

    def test_no_name_returns_none(self):
        assert extract_name({"amenity": "cafe"}) is None
