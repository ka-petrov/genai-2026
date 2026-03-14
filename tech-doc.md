# Technical Implementation Handoff: LLM-Powered Geospatial Neighborhood Analyst

## 1) Purpose and Scope

This document decomposes implementation into loosely coupled parts so specialized agents (frontend, backend, data, LLM, infra) can work in parallel with minimal blocking.

Core product behavior:
1. User drops map pin + sets radius.
2. System builds a region context from geospatial data sources.
3. User starts a chat and can ask follow-up questions about the same region.
4. Assistant responses are streamed continuously to the UI.
5. Each assistant turn is still constrained to structured output at completion.
6. Chat history is persisted in browser `sessionStorage` (no auth, no DB).

## 2) Product Boundaries (MVP)

### In scope
- Single-page app with MapLibre GL.
- OSM vector tile map rendering (explicitly configured style/source).
- Pin + radius + region context creation.
- Multi-turn chat for follow-up questions on initial query context.
- Streaming assistant output to frontend (incremental text/tokens).
- Final structured assistant payload (`answer`, `reasoning_summary`, `evidence`, `limitations`, `confidence`).
- Browser-side chat history persistence via `sessionStorage`.
- Containerized deployment via Docker Compose + Nginx.

### Out of scope (MVP)
- Authentication/authorization.
- Persistent backend database.
- Background jobs/queues.
- Vector DB/RAG over external docs.
- Full geocoding/search infrastructure.

## 3) Target Stack

- Frontend: React + TypeScript + Vite + MapLibre GL JS + Tailwind CSS.
- Backend: Python + FastAPI + Pydantic + `uv` for dependency/runtime management.
- Data source layer: pluggable provider abstraction (`DataSource` base class), with Overpass as first implementation.
- LLM: OpenRouter API with model ID from app config; structured outputs enforced for compatible models.
- Deployment: Docker + Docker Compose + Nginx on one VM (e.g., DigitalOcean droplet).

## 4) System Architecture (Contract-First)

```text
Browser SPA
  -> Nginx
      -> / (frontend static files + MapLibre app)
      -> /api/* (FastAPI)
              -> DataSourceRegistry
                    -> OverpassDataSource (now)
                    -> GooglePlacesDataSource (future)
              -> OpenRouter Chat/Responses
```

Design rule: components communicate through explicit schemas/interfaces; each part can be built against mocks first.

## 5) Shared Contracts

## 5.1 Core Domain Objects

### RegionSpec
```json
{
  "lat": 52.52,
  "lon": 13.40,
  "radius_m": 800
}
```

### ChatMessage
```json
{
  "role": "user",
  "content": "How walkable is this area?"
}
```

### AssistantTurnStructured
```json
{
  "answer": "This area appears moderately walkable...",
  "reasoning_summary": "Based on transit stops and amenity density...",
  "evidence": [
    "17 bus stops within 800m",
    "34 restaurants and 12 cafes"
  ],
  "limitations": [
    "OSM coverage may be incomplete",
    "No live service frequency data included"
  ],
  "confidence": "medium"
}
```

## 5.2 External API Surface

### `POST /api/contexts`
Creates or fetches a region context snapshot used for chat turns.

Request:
```json
{
  "region": {
    "lat": 52.52,
    "lon": 13.40,
    "radius_m": 800
  }
}
```

Response:
```json
{
  "context_id": "ctx_9f3a...",
  "region_profile": {
    "center": {"lat": 52.52, "lon": 13.40},
    "radius_m": 800,
    "counts": {},
    "nearest": {},
    "mobility": {},
    "land_use": {},
    "poi_examples": {},
    "data_quality_notes": []
  },
  "map_features": [],
  "meta": {
    "cache_hit": false,
    "data_sources": ["overpass"],
    "request_id": "uuid"
  }
}
```

### `POST /api/chat/stream`
Streams one assistant turn for a multi-turn chat.

Request:
```json
{
  "context_id": "ctx_9f3a...",
  "messages": [
    {"role": "user", "content": "Is this good for families?"},
    {"role": "assistant", "content": "It looks moderately suitable..."},
    {"role": "user", "content": "What about without a car?"}
  ],
  "model_id": "openrouter/model-id-from-config"
}
```

Response content type:
- `text/event-stream`

SSE event contract:
- `event: response.started` -> metadata (`request_id`, `context_id`, `model_id`)
- `event: response.delta` -> incremental text chunk for live rendering
- `event: response.completed` -> final `AssistantTurnStructured` JSON payload
- `event: response.error` -> stable typed error shape

Notes:
- Frontend appends `response.delta` continuously to render streaming output.
- Frontend treats `response.completed` as canonical persisted assistant turn.
- Backend validates the final structured object against schema before emitting `response.completed`.

### `GET /api/health`
Basic liveness/readiness endpoint.

## 5.3 Error Shape

```json
{
  "error": {
    "code": "CONTEXT_NOT_FOUND",
    "message": "Context expired or missing",
    "retryable": true
  },
  "meta": {
    "request_id": "uuid"
  }
}
```

## 5.4 Domain Taxonomy (MVP-fixed)

Use a constrained category set for predictable performance and quality:
- Amenities/livability: cafes, restaurants, schools, clinics/hospitals/pharmacies, supermarkets, libraries, parks/playgrounds/sports centers.
- Mobility proxy: bus/tram/rail stops, parking, bike parking, walk/cycle-related ways.
- Family convenience proxy: schools, parks/playgrounds, pharmacies, supermarkets, transit density.

## 6) Workstream Decomposition (Loosely Coupled Parts)

## Part A: Frontend Map + Multi-Turn Chat UX

Owner profile: frontend/UI agent.

Responsibilities:
- Build SPA shell and responsive layout.
- Configure MapLibre GL with an OSM-derived vector tile style source (explicit map style URL in config).
- Implement pin drop + radius selection + context creation call (`POST /api/contexts`).
- Implement multi-turn chat panel with streaming response rendering from SSE.
- Persist query/chat history in browser `sessionStorage`:
  - store threads, selected thread, region context metadata, messages
  - restore on reload within session
- Render map overlays from `map_features`.
- Handle loading/streaming/empty/error states.

Independence strategy:
- Build against mocked `contexts` and mocked SSE stream events.
- No dependency on live Overpass/OpenRouter for initial UI iteration.

Deliverables:
- Typed API client for REST + SSE.
- Chat thread store (`sessionStorage`) and hydration logic.
- Map rendering with vector tile attribution and fallback UI.

Acceptance criteria:
- User can ask follow-up questions in same thread with coherent context.
- Assistant text streams incrementally (not all-at-once).
- Thread history restores from `sessionStorage` in same browser session.

## Part B: Backend API Orchestration + Streaming + `uv`

Owner profile: backend/API agent.

Responsibilities:
- Implement FastAPI routes for `POST /api/contexts`, `POST /api/chat/stream`, `GET /api/health`.
- Validate all requests/responses with Pydantic models.
- Implement SSE streaming adapter for assistant turn output.
- Keep stable error model and request IDs.
- Manage dependencies and runtime with `uv`:
  - `pyproject.toml`
  - `uv.lock`
  - `uv sync`, `uv run ...`
- Add lightweight in-memory cache for context snapshots.

Independence strategy:
- Can integrate mocked `DataSourceRegistry` and mocked `LLMClient` first.
- Stabilizes API contracts before real provider integration.

Deliverables:
- `backend/app/main.py`, `schemas.py`, `chat_stream.py`, `config.py`.
- `pyproject.toml` and `uv.lock`-driven workflow.

Acceptance criteria:
- Streaming endpoint emits valid SSE lifecycle events.
- Schema validation catches malformed input and model output.
- `uv`-based local/dev/container workflow is documented and repeatable.

## Part C: Pluggable Data Source Layer + Region Profiling

Owner profile: geospatial/data agent.

Responsibilities:
- Define generic source abstraction:
  - `DataSource` base class/interface
  - `fetch(region_spec) -> SourceFeatureSet`
  - `source_name`, health/error contract
- Implement `OverpassDataSource` as first concrete provider.
- Add `DataSourceRegistry` + profile aggregation/fusion pipeline.
- Normalize source-specific data into canonical POI/feature schema.
- Produce:
  - `region_profile`
  - `map_features`
  - source provenance in metadata

Future-ready extension:
- Add `GooglePlacesDataSource` (or others) by implementing `DataSource`; no API contract changes required.

Independence strategy:
- Fully testable with fixture data independent of frontend and LLM.

Deliverables:
- `datasources/base.py`, `datasources/overpass.py`, `datasources/registry.py`.
- `osm_normalizer.py`, `feature_extractors.py`, `profile_aggregator.py`.
- Documentation for tag/category mapping and canonical schema.

Acceptance criteria:
- New data source can be added without changing API payload shapes.
- Deterministic output for fixed fixtures.
- Sparse data and provider errors degrade gracefully.

## Part D: OpenRouter LLM Integration + Structured Streaming

Owner profile: LLM/prompting agent.

Responsibilities:
- Implement OpenRouter client integration for configured model ID.
- Make `model_id` configurable via app config/env; enforce default model if not provided.
- Use structured output constraints for compatible models; validate final structured payload.
- Build prompt contract using:
  - chat history
  - user follow-up question
  - region profile
  - grounding policy (facts first, no fabricated specifics)
- Stream response deltas while assembling final validated structured output.

Independence strategy:
- Can run entirely against synthetic `region_profile` fixtures and mocked backend endpoint.

Deliverables:
- `llm_client.py`, `prompt_builder.py`, `structured_output_schema.py`.
- Compatibility matrix note for candidate OpenRouter models that support structured output reliably.

Acceptance criteria:
- Multi-turn turns remain context-aware with follow-up questions.
- Final event always includes schema-valid structured object or typed fallback error.
- Evidence references region facts, not invented entities.

## Part E: Containerized Runtime + Deployment Baseline

Owner profile: infra/devops agent.

Responsibilities:
- Compose services: `frontend`, `backend`, `nginx`.
- Nginx routing:
  - `/` -> frontend static assets
  - `/api/` -> backend (including SSE streaming support)
- Ensure proxy config does not buffer SSE in a way that breaks streaming.
- Support backend `uv` workflow inside Docker image.
- Define env/config strategy:
  - `OPENROUTER_API_KEY`
  - `LLM_MODEL_ID`
  - `MAP_STYLE_URL`
  - provider timeouts/cache TTL
- Provide VM deployment + verification runbook.

Independence strategy:
- Can be built against placeholder frontend/backend containers.

Deliverables:
- `docker-compose.yml`, Dockerfiles, `nginx/default.conf`.
- Runbook for deploy/update/rollback basics.

Acceptance criteria:
- `docker compose up --build` boots complete stack.
- SSE chat streaming works through Nginx in local/prod topology.
- Single-origin setup avoids CORS complexity.

## 7) Integration Points and Ordering (No Time Mapping)

Recommended dependency graph:
1. Part B defines API + SSE + schemas first.
2. Part A builds UI/chat state against mocks.
3. Part C builds data abstraction and Overpass provider in parallel.
4. Part D builds OpenRouter streaming + structured output in parallel.
5. Part B integrates C and D.
6. Part E wraps full stack and validates runtime behavior.

Integration checkpoints:
- Checkpoint 1: A + B (mock contexts and mock SSE stream).
- Checkpoint 2: B + C (real region context generation, mock LLM stream).
- Checkpoint 3: B + D (real LLM stream using fixture context).
- Checkpoint 4: A + B + C + D full multi-turn streaming chat.
- Checkpoint 5: Full stack via E on target VM.

## 8) Cross-Cutting Non-Functional Requirements

- Streaming UX: first token latency should feel immediate in demo conditions.
- Reliability: explicit fallbacks for data provider failures and LLM output parse failures.
- Explainability: each completed assistant turn includes evidence + limitations + confidence.
- Security: API keys server-side only; model/provider keys never exposed to frontend.
- Observability: request IDs and basic structured logs for context creation and chat turns.
- Compatibility: SSE behavior validated behind Nginx proxy.

## 9) Risks and Mitigations

- Overpass latency/rate limits:
  - keep query scope narrow, cache context snapshots, allow stale fallback for same region.
- Structured output support differences across OpenRouter models:
  - maintain allowlist and compatibility checks; fail fast on unsupported model.
- Streaming interruptions:
  - typed `response.error` event + frontend retry affordance.
- `sessionStorage` is session-scoped (tab/session lifetime only):
  - communicate scope clearly in UX; move to `localStorage` or backend persistence later if needed.
- Multi-agent integration drift:
  - fixture-based contract tests for APIs, SSE events, and structured payload schema.

## 10) Suggested Repository Layout

```text
project-root/
  tech-doc.md
  docker-compose.yml
  frontend/
    Dockerfile
    package.json
    src/
      api/
      chat/
      map/
      storage/
  backend/
    Dockerfile
    pyproject.toml
    uv.lock
    app/
      main.py
      schemas.py
      config.py
      chat_stream.py
      datasources/
        base.py
        overpass.py
        registry.py
      profile_aggregator.py
      prompt_builder.py
      llm_client.py
  nginx/
    default.conf
```

## 11) Handoff Summary by Agent Type

- Frontend agent: owns map + multi-turn streaming UI + `sessionStorage` thread persistence.
- Backend agent: owns FastAPI contracts, SSE orchestration, schema enforcement, and `uv` dependency management.
- Data/geospatial agent: owns `DataSource` abstraction, Overpass provider, and profile aggregation.
- LLM agent: owns OpenRouter integration, model config, and structured-output-compliant streamed turns.
- Infra agent: owns Compose/Nginx runtime, SSE-safe proxy behavior, and deployment reproducibility.

Each part is intentionally decoupled by typed contracts so teams can develop in parallel and merge with low rework risk.
