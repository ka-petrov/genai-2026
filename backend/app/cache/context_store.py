"""Context and region cache operations backed by Redis."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis

from app.cache.cache_keys import (
    compute_region_hash,
    context_key,
    last_model_key,
    region_key,
)
from app.config import settings
from app.schemas import RegionSpec

logger = logging.getLogger(__name__)


class ContextStore:
    def __init__(self, redis: aioredis.Redis) -> None:
        self._r = redis

    @staticmethod
    def new_context_id() -> str:
        return f"ctx_{uuid.uuid4().hex[:12]}"

    # ── Region cache ────────────────────────────────────────────

    async def get_cached_region(self, region: RegionSpec) -> dict | None:
        rh = compute_region_hash(region.lat, region.lon, region.radius_m)
        raw = await self._r.get(region_key(rh))
        if raw is None:
            return None
        return json.loads(raw)

    async def store_region_cache(
        self,
        region: RegionSpec,
        region_profile: dict,
        map_features: list[dict],
        data_sources: list[str],
    ) -> None:
        rh = compute_region_hash(region.lat, region.lon, region.radius_m)
        payload = json.dumps({
            "region_profile": region_profile,
            "map_features": map_features,
            "data_sources": data_sources,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })
        await self._r.set(
            region_key(rh), payload, ex=settings.redis_region_ttl_seconds,
        )

    # ── Context lifecycle ───────────────────────────────────────

    async def create_context(
        self,
        region: RegionSpec,
        region_profile: dict,
        map_features: list[dict],
        data_sources: list[str],
    ) -> str:
        ctx_id = self.new_context_id()
        payload = json.dumps({
            "region_spec": region.model_dump(),
            "region_profile": region_profile,
            "map_features": map_features,
            "data_sources": data_sources,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        await self._r.set(
            context_key(ctx_id), payload, ex=settings.redis_context_ttl_seconds,
        )
        return ctx_id

    async def get_context(self, context_id: str) -> dict | None:
        raw = await self._r.get(context_key(context_id))
        if raw is None:
            return None
        return json.loads(raw)

    # ── Auxiliary ───────────────────────────────────────────────

    async def store_last_model(self, context_id: str, model_id: str) -> None:
        await self._r.set(
            last_model_key(context_id),
            model_id,
            ex=settings.redis_context_ttl_seconds,
        )
