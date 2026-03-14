"""FastAPI dependency providers.

Centralises object creation so routes stay thin and tests can override
via ``app.dependency_overrides``.
"""

from __future__ import annotations

from app.cache.context_store import ContextStore
from app.cache.redis_client import get_redis
from app.datasources.overpass import OverpassDataSource
from app.datasources.registry import DataSourceRegistry

_registry: DataSourceRegistry | None = None


def get_data_registry() -> DataSourceRegistry:
    global _registry
    if _registry is None:
        _registry = DataSourceRegistry()
        _registry.register(OverpassDataSource())
    return _registry


def get_context_store() -> ContextStore:
    return ContextStore(get_redis())
