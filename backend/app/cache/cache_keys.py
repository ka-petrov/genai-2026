"""Redis key patterns and helpers."""

from __future__ import annotations

import hashlib
import json

PREFIX = "v1"


def context_key(context_id: str) -> str:
    return f"{PREFIX}:ctx:{context_id}"


def region_key(region_hash: str) -> str:
    return f"{PREFIX}:region:{region_hash}"


def last_model_key(context_id: str) -> str:
    return f"{PREFIX}:chat:last_model:{context_id}"


def compute_region_hash(lat: float, lon: float, radius_m: int) -> str:
    """Stable hash of normalized RegionSpec for cache keying.

    Coordinates are rounded to 4 decimal places (~11 m precision) so that
    nearby pins hit the same cache entry.
    """
    normalized = json.dumps(
        {"lat": round(lat, 4), "lon": round(lon, 4), "radius_m": radius_m},
        sort_keys=True,
    )
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]
