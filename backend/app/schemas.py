from __future__ import annotations

from pydantic import BaseModel


# ── Domain objects ──────────────────────────────────────────


class RegionSpec(BaseModel):
    lat: float
    lon: float
    radius_m: int


class ChatMessage(BaseModel):
    role: str
    content: str


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
    context_id: str
    messages: list[ChatMessage]
    model_id: str | None = None


# ── Error shape ─────────────────────────────────────────────


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool


class ErrorResponse(BaseModel):
    error: ErrorDetail
    meta: dict
