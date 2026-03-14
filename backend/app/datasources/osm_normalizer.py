"""Maps raw OSM tag key/value pairs to the MVP domain taxonomy.

Taxonomy categories (from tech-doc §5.4):
  amenity    — cafes, restaurants, schools, clinics, hospitals, pharmacies,
               supermarkets, libraries
  leisure    — parks, playgrounds, sports centres
  mobility   — bus/tram/rail stops, parking, bike parking
  education  — schools (also counted under family convenience)
  healthcare — clinics, hospitals, pharmacies
  shopping   — supermarkets, convenience stores
  land_use   — residential, commercial, industrial, etc.
"""

from __future__ import annotations

AMENITY_MAP: dict[str, tuple[str, str]] = {
    "cafe": ("amenity", "cafe"),
    "restaurant": ("amenity", "restaurant"),
    "fast_food": ("amenity", "restaurant"),
    "bar": ("amenity", "bar"),
    "pub": ("amenity", "bar"),
    "school": ("education", "school"),
    "kindergarten": ("education", "kindergarten"),
    "university": ("education", "university"),
    "college": ("education", "college"),
    "library": ("amenity", "library"),
    "hospital": ("healthcare", "hospital"),
    "clinic": ("healthcare", "clinic"),
    "doctors": ("healthcare", "clinic"),
    "dentist": ("healthcare", "clinic"),
    "pharmacy": ("healthcare", "pharmacy"),
    "parking": ("mobility", "parking"),
    "bicycle_parking": ("mobility", "bike_parking"),
    "bus_station": ("mobility", "bus_stop"),
    "bank": ("amenity", "bank"),
    "post_office": ("amenity", "post_office"),
    "place_of_worship": ("amenity", "place_of_worship"),
    "community_centre": ("amenity", "community_centre"),
    "theatre": ("amenity", "theatre"),
    "cinema": ("amenity", "cinema"),
    "marketplace": ("shopping", "marketplace"),
    "fuel": ("amenity", "fuel"),
}

SHOP_MAP: dict[str, tuple[str, str]] = {
    "supermarket": ("shopping", "supermarket"),
    "convenience": ("shopping", "convenience"),
    "bakery": ("shopping", "bakery"),
    "butcher": ("shopping", "butcher"),
    "greengrocer": ("shopping", "greengrocer"),
    "mall": ("shopping", "mall"),
    "department_store": ("shopping", "department_store"),
    "clothes": ("shopping", "clothes"),
    "chemist": ("shopping", "chemist"),
}

LEISURE_MAP: dict[str, tuple[str, str]] = {
    "park": ("leisure", "park"),
    "playground": ("leisure", "playground"),
    "sports_centre": ("leisure", "sports_centre"),
    "swimming_pool": ("leisure", "swimming_pool"),
    "fitness_centre": ("leisure", "fitness_centre"),
    "garden": ("leisure", "garden"),
    "pitch": ("leisure", "pitch"),
    "dog_park": ("leisure", "dog_park"),
    "nature_reserve": ("leisure", "nature_reserve"),
}

TOURISM_MAP: dict[str, tuple[str, str]] = {
    "museum": ("amenity", "museum"),
    "gallery": ("amenity", "gallery"),
    "attraction": ("amenity", "attraction"),
    "viewpoint": ("amenity", "viewpoint"),
    "hotel": ("amenity", "hotel"),
}

PUBLIC_TRANSPORT_MAP: dict[str, tuple[str, str]] = {
    "stop_position": ("mobility", "transit_stop"),
    "platform": ("mobility", "transit_stop"),
    "station": ("mobility", "transit_station"),
}

RAILWAY_MAP: dict[str, tuple[str, str]] = {
    "station": ("mobility", "rail_station"),
    "halt": ("mobility", "rail_halt"),
    "tram_stop": ("mobility", "tram_stop"),
    "subway_entrance": ("mobility", "subway_entrance"),
}

HIGHWAY_MAP: dict[str, tuple[str, str]] = {
    "bus_stop": ("mobility", "bus_stop"),
    "crossing": ("mobility", "crossing"),
    "cycleway": ("mobility", "cycleway"),
}

LANDUSE_MAP: dict[str, tuple[str, str]] = {
    "residential": ("land_use", "residential"),
    "commercial": ("land_use", "commercial"),
    "industrial": ("land_use", "industrial"),
    "retail": ("land_use", "retail"),
    "cemetery": ("land_use", "cemetery"),
    "farmland": ("land_use", "farmland"),
    "forest": ("land_use", "forest"),
    "meadow": ("land_use", "meadow"),
    "recreation_ground": ("land_use", "recreation"),
}

_TAG_DISPATCH: list[tuple[str, dict[str, tuple[str, str]]]] = [
    ("amenity", AMENITY_MAP),
    ("shop", SHOP_MAP),
    ("leisure", LEISURE_MAP),
    ("tourism", TOURISM_MAP),
    ("public_transport", PUBLIC_TRANSPORT_MAP),
    ("railway", RAILWAY_MAP),
    ("highway", HIGHWAY_MAP),
    ("landuse", LANDUSE_MAP),
]


def classify_osm_tags(tags: dict[str, str]) -> tuple[str, str] | None:
    """Return (category, subcategory) for a set of OSM tags, or None if
    the element doesn't match any known taxonomy entry."""
    for tag_key, mapping in _TAG_DISPATCH:
        value = tags.get(tag_key)
        if value is not None and value in mapping:
            return mapping[value]
    return None


def extract_name(tags: dict[str, str]) -> str | None:
    return tags.get("name") or tags.get("name:en")
