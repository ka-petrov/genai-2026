"""Redis connection factory (async)."""

from __future__ import annotations

import logging

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

_pool: aioredis.ConnectionPool | None = None


def get_pool() -> aioredis.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _pool


def get_redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=get_pool())


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


async def redis_health_check() -> bool:
    try:
        r = get_redis()
        return await r.ping()
    except Exception:
        logger.warning("Redis health check failed", exc_info=True)
        return False
