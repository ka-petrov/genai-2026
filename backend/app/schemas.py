from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── Domain objects ──────────────────────────────────────────


class RegionSpec(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    radius_m: int = Field(..., ge=50, le=50_000)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., max_length=10_000)


class AssistantTurnStructured(BaseModel):
    answer: str
    reasoning_summary: str
    evidence: list[str]
    limitations: list[str]
    confidence: str


# ── API request / response ──────────────────────────────────


class CreateContextRequest(BaseModel):
    region: RegionSpec


class ContextMeta(BaseModel):
    cache_hit: bool
    data_sources: list[str]
    request_id: str


class CreateContextResponse(BaseModel):
    context_id: str
    region_profile: dict
    map_features: list
    meta: ContextMeta


class ChatStreamRequest(BaseModel):
    context_id: str = Field(..., min_length=1, max_length=128)
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=50)
    model_id: str | None = Field(None, max_length=128)


# ── Error shape ─────────────────────────────────────────────


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool


class ErrorResponse(BaseModel):
    error: ErrorDetail
    meta: dict
