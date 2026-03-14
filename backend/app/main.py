"""GenGeo FastAPI application."""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from app.cache.context_store import ContextStore
from app.cache.redis_client import close_pool, redis_health_check
from app.chat_stream import generate_chat_events
from app.config import settings
from app.datasources.registry import DataSourceRegistry
from app.dependencies import get_context_store, get_data_registry
from app.llm_client import stream_chat_completion
from app.profile_aggregator import aggregate
from app.schemas import (
    ChatStreamRequest,
    ContextMeta,
    CreateContextRequest,
    CreateContextResponse,
    ErrorDetail,
    ErrorResponse,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    logger.info("GenGeo API starting")
    yield
    await close_pool()
    logger.info("GenGeo API shut down")


app = FastAPI(title="GenGeo API", version="0.1.0", lifespan=lifespan)


def _error_response(
    status: int,
    code: str,
    message: str,
    *,
    retryable: bool,
    request_id: str,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorDetail(code=code, message=message, retryable=retryable),
        meta={"request_id": request_id},
    )
    return JSONResponse(status_code=status, content=body.model_dump())


# ── Health ──────────────────────────────────────────────────────


@app.get("/api/health")
async def health(registry: DataSourceRegistry = Depends(get_data_registry)):
    redis_ok = await redis_health_check()
    return {
        "status": "ok" if redis_ok else "degraded",
        "redis": redis_ok,
        "data_sources": registry.source_names,
    }


# ── Context creation ───────────────────────────────────────────


@app.post("/api/contexts", response_model=CreateContextResponse)
async def create_context(
    body: CreateContextRequest,
    store: ContextStore = Depends(get_context_store),
    registry: DataSourceRegistry = Depends(get_data_registry),
):
    request_id = uuid.uuid4().hex

    try:
        cached = await store.get_cached_region(body.region)
    except Exception:
        logger.warning("Redis read failed during region cache lookup", exc_info=True)
        cached = None

    if cached is not None:
        region_profile = cached["region_profile"]
        map_features = cached["map_features"]
        data_sources = cached["data_sources"]
        cache_hit = True
    else:
        feature_sets = await registry.fetch_all(body.region)
        region_profile, map_features = aggregate(body.region, feature_sets)
        data_sources = registry.source_names
        cache_hit = False

        try:
            await store.store_region_cache(
                body.region, region_profile, map_features, data_sources,
            )
        except Exception:
            logger.warning("Failed to write region cache", exc_info=True)

    try:
        context_id = await store.create_context(
            body.region, region_profile, map_features, data_sources,
        )
    except Exception as exc:
        logger.error("Failed to persist context: %s", exc)
        return _error_response(
            503, "CACHE_UNAVAILABLE", "Could not persist context",
            retryable=True, request_id=request_id,
        )

    return CreateContextResponse(
        context_id=context_id,
        region_profile=region_profile,
        map_features=map_features,
        meta=ContextMeta(
            cache_hit=cache_hit,
            data_sources=data_sources,
            request_id=request_id,
        ),
    )


# ── Chat streaming ─────────────────────────────────────────────


@app.post("/api/chat/stream")
async def chat_stream(
    body: ChatStreamRequest,
    store: ContextStore = Depends(get_context_store),
):
    request_id = uuid.uuid4().hex
    model_id = body.model_id or settings.llm_model_id

    try:
        ctx = await store.get_context(body.context_id)
    except Exception:
        return _error_response(
            503, "CACHE_UNAVAILABLE", "Redis unavailable",
            retryable=True, request_id=request_id,
        )

    if ctx is None:
        return _error_response(
            404, "CONTEXT_NOT_FOUND", "Context expired or missing",
            retryable=True, request_id=request_id,
        )

    llm_stream = stream_chat_completion(
        messages=body.messages,
        region_profile=ctx["region_profile"],
        model_id=model_id,
    )

    event_gen = generate_chat_events(
        request_id=request_id,
        context_id=body.context_id,
        model_id=model_id,
        llm_stream=llm_stream,
    )

    return EventSourceResponse(event_gen)
