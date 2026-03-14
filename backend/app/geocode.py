"""Thin server-side proxy for Google Places APIs.

Keeps the GOOGLE_MAPS_API_KEY on the backend so it is never exposed to the
browser.  The frontend calls these endpoints instead of loading the Google
Maps JavaScript SDK directly.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Query

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/geocode", tags=["geocode"])

PLACES_AUTOCOMPLETE_URL = (
    "https://maps.googleapis.com/maps/api/place/autocomplete/json"
)
PLACES_DETAILS_URL = (
    "https://maps.googleapis.com/maps/api/place/details/json"
)


@router.get("/autocomplete")
async def autocomplete(
    input: str = Query(..., min_length=1, description="Search text"),
    session_token: str | None = Query(None, description="Optional session token for billing"),
):
    """Return place predictions for the given input string."""
    if not settings.google_maps_api_key:
        return {"predictions": [], "status": "API_KEY_MISSING"}

    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.get(
            PLACES_AUTOCOMPLETE_URL,
            params={
                "input": input,
                "types": "geocode",
                "key": settings.google_maps_api_key,
                **({"sessiontoken": session_token} if session_token else {}),
            },
        )
        resp.raise_for_status()
        data = resp.json()

    predictions = [
        {
            "place_id": p["place_id"],
            "description": p.get("description", ""),
            "structured_formatting": p.get("structured_formatting"),
        }
        for p in data.get("predictions", [])
    ]
    return {"predictions": predictions, "status": data.get("status", "OK")}


@router.get("/place")
async def place_details(
    place_id: str = Query(..., description="Google Place ID"),
    session_token: str | None = Query(None, description="Optional session token for billing"),
):
    """Return geometry (lat/lon) and formatted address for a place."""
    if not settings.google_maps_api_key:
        return {"result": None, "status": "API_KEY_MISSING"}

    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.get(
            PLACES_DETAILS_URL,
            params={
                "place_id": place_id,
                "fields": "geometry,formatted_address,name",
                "key": settings.google_maps_api_key,
                **({"sessiontoken": session_token} if session_token else {}),
            },
        )
        resp.raise_for_status()
        data = resp.json()

    result_raw = data.get("result")
    if not result_raw:
        return {"result": None, "status": data.get("status", "NOT_FOUND")}

    location = result_raw.get("geometry", {}).get("location", {})
    return {
        "result": {
            "lat": location.get("lat"),
            "lon": location.get("lng"),
            "formatted_address": result_raw.get("formatted_address"),
            "name": result_raw.get("name"),
        },
        "status": data.get("status", "OK"),
    }
