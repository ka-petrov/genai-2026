# Technical Implementation Handoff: LLM-Powered Geospatial Neighborhood Analyst (GenGeo)

## 1) Purpose and Scope

This document decomposes implementation into loosely coupled parts so specialized agents (frontend, backend, data, LLM, infra) can work in parallel with minimal blocking.

Core product behavior:
1. User navigates to root URL and sees a landing page with product information.
2. At the top of the landing page, user enters a question (required) and optionally an address (autocompleted via Google Geocoding API).
3. On submit, user is routed to the main map page with the side chat panel.
   - If an address was provided, the map centers on the geocoded coordinates and auto-creates a region context.
   - If no address was provided, the map opens at a default view and the user drops a pin manually.
4. User drops/adjusts map pin + sets radius (or accepts auto-placed pin from geocoded address).
5. System builds a region context from geospatial data sources.
6. User starts a chat (pre-populated with the landing page question if applicable) and can ask follow-up questions about the same region.
7. Assistant responses are streamed continuously to the UI.
8. Each assistant turn is still constrained to structured output at completion.
9. Chat history is persisted in browser `sessionStorage` (no auth, no DB).

## 2) Product Boundaries (MVP)

### In scope
- Landing page at root URL with product info, question input, and optional address autocomplete.
- Google Geocoding / Places Autocomplete API integration for the landing page address field.
- Client-side routing: landing page (`/`) and map page (`/map`).
- Single-page app with MapLibre GL (map page).
- OSM vector tile map rendering (explicitly configured style/source).
- Pin + radius + region context creation (manual pin drop or auto-placed from geocoded address).
- Multi-turn chat for follow-up questions on initial query context.
- Streaming assistant output to frontend (incremental text/tokens).
- Final structured assistant payload (`answer`, `reasoning_summary`, `evidence`, `limitations`, `confidence`).
- Browser-side chat history persistence via `sessionStorage`.
- Redis-backed ephemeral cache/context store for backend state.
- Containerized deployment via Docker Compose + Nginx.

### Out of scope (MVP)
- Authentication/authorization.
- Persistent product database (beyond ephemeral Redis cache).
- Background jobs/queues.
- Vector DB/RAG over external docs.

## 3) Target Stack

- Frontend: React + TypeScript + Vite + React Router + MapLibre GL JS + Tailwind CSS.
- Google APIs (server-side): Google Places API proxied through backend endpoints (`/api/geocode/autocomplete`, `/api/geocode/place`) to keep the API key off the client.
- Backend: Python + FastAPI + Pydantic + `uv` for dependency/runtime management.
- Cache/state: Redis for ephemeral context and request-level caching.
- Data source layer: pluggable provider abstraction (`DataSource` base class), with Overpass as first implementation.
- LLM: OpenRouter API with model ID from app config; structured outputs enforced for compatible models.
- Deployment: Docker + Docker Compose + Nginx on one VM (e.g., DigitalOcean droplet).

## 4) System Architecture (Contract-First)

```text
Browser SPA (React Router)
  /             -> Landing page (hero + question input + address autocomplete)
  /map          -> Map page (MapLibre + chat panel)

  -> Nginx
      -> / (frontend static files, client-side routing)
      -> /api/* (FastAPI)
              -> Redis (context snapshots + TTL cache)
              -> DataSourceRegistry
                    -> OverpassDataSource (now)
                    -> GooglePlacesDataSource (future)
              -> OpenRouter Chat/Responses

Landing page address field -> Google Geocoding/Places Autocomplete API (client-side, API key restricted)
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

Context lifecycle notes:
- Backend persists `context_id -> region_profile + map_features + metadata` in Redis with TTL.
- `POST /api/chat/stream` resolves `context_id` from Redis and injects that context into the LLM prompt.
- If the key is missing/expired, backend returns typed `CONTEXT_NOT_FOUND` and frontend recreates context.

### Redis Key Schema (Ephemeral/Cache Contract)

Use versioned keys (`v1`) so schema changes are explicit.

Key patterns:
- `v1:ctx:{context_id}`
  - Purpose: canonical chat context for a selected region.
  - Value (JSON): `{ region_spec, region_profile, map_features, data_sources, created_at }`
  - TTL: `REDIS_CONTEXT_TTL_SECONDS` (recommended default: 3600).
- `v1:region:{region_hash}`
  - Purpose: reusable region snapshot cache for repeated same `(lat, lon, radius)` requests.
  - `region_hash`: stable hash of normalized `RegionSpec` (rounded coordinates + radius).
  - Value (JSON): `{ region_profile, map_features, data_sources, generated_at }`
  - TTL: `REDIS_REGION_TTL_SECONDS` (recommended default: 900).
- `v1:chat:last_model:{context_id}` (optional)
  - Purpose: store last effective model ID used in thread for analytics/debug.
  - Value: string model id.
  - TTL: same as context TTL.

Operational rules:
- `POST /api/contexts`:
  - compute `region_hash`, try `v1:region:{region_hash}` first;
  - on hit, mint new `context_id` and write `v1:ctx:{context_id}` from cached snapshot;
  - on miss, fetch providers, write both `v1:region:{region_hash}` and `v1:ctx:{context_id}`.
- `POST /api/chat/stream`:
  - read `v1:ctx:{context_id}` only (single source of truth for LLM grounding context).
- Never trust client-provided region profile for prompt grounding.
- Expired/missing context key -> `CONTEXT_NOT_FOUND`.
- Redis connectivity failure -> `CACHE_UNAVAILABLE` (retryable).
- Include key prefix and TTLs in config for environment-level tuning.

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
- Implement Redis-backed ephemeral storage:
  - context snapshots by `context_id` with TTL
  - optional request/result cache keys for repeated region queries

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
- Context retrieval for chat is Redis-backed (no process-local state dependency).

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
- Add `redis` service for ephemeral/cache storage.
- Nginx routing:
  - `/` -> frontend static assets
  - `/api/` -> backend (including SSE streaming support)
- Ensure proxy config does not buffer SSE in a way that breaks streaming.
- Support backend `uv` workflow inside Docker image.
- Define env/config strategy:
  - `OPENROUTER_API_KEY`
  - `LLM_MODEL_ID`
  - `MAP_STYLE_URL`
  - `REDIS_URL`
  - `REDIS_TTL_SECONDS`
  - `GOOGLE_MAPS_API_KEY` (backend-only, for server-side Google Places API proxy)
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
- Redis connectivity/TTL behavior is validated end-to-end.

## Part F: Landing Page + Entry Flow

Owner profile: frontend/UI agent.

Responsibilities:
- Build a landing page served at `/` inspired by the Google Maps Platform AI page (https://mapsplatform.google.com/ai/).
- Implement client-side routing (`/` landing page, `/map` map page) using React Router.
- Landing page layout (top-to-bottom):
  1. **Hero prompt section** (top of page, visually prominent):
     - Headline (e.g., "Ask anything about a neighborhood").
     - **Question input field** (required) — text input or textarea. Placeholder examples to guide the user (e.g., "How walkable is this area?", "Is this good for families?").
     - **Address input field** (optional) — uses server-side Google Places Autocomplete proxy (`/api/geocode/autocomplete`) for type-ahead suggestions. When the user selects a suggestion, the geocoded `lat`/`lon` is fetched via `/api/geocode/place`.
     - Submit button / Enter key triggers navigation to `/map`.
  2. **Product info / feature sections** below the hero — concise marketing-style content explaining what GenGeo does (can be static content for MVP).
- On submit, navigate to `/map` passing state via URL search params or React Router state:
  - `q` — the user's question text (required).
  - `lat`, `lon` — geocoded coordinates from address selection (present only if address was provided).
- Map page behavior on arrival from landing page:
  - If `lat`/`lon` are present: center map on those coordinates, auto-place pin, auto-create region context (`POST /api/contexts`), and pre-populate the chat input with the question from `q`.
  - If only `q` is present (no address): open map at default view, prompt user to drop a pin, keep question in chat input ready to send once context exists.
- Nginx must be configured to serve `index.html` for all client-side routes (SPA fallback).

Google Places Autocomplete integration (server-side proxy):
- Backend exposes `GET /api/geocode/autocomplete?input=...` and `GET /api/geocode/place?place_id=...` that proxy to Google Places API.
- API key (`GOOGLE_MAPS_API_KEY`) stored server-side only — never exposed to the browser.
- Restrict API key to `Places API` with IP restrictions (backend server IP).
- Frontend calls these endpoints with a debounced input and renders a custom dropdown.
- On place selection, frontend calls `/api/geocode/place` to retrieve `lat`/`lon` for routing to map page.
- Graceful fallback if API key is missing or backend is unavailable: address field remains a plain text input (no autocomplete), and no geocoded coordinates are passed.

Independence strategy:
- Fully buildable with a placeholder map page; only requires Google API key for autocomplete testing.
- Landing page content and styling are independent of backend services.

Deliverables:
- `frontend/src/pages/LandingPage.tsx` — landing page component.
- `frontend/src/pages/MapPage.tsx` — refactored map + chat page (existing functionality moved here).
- `frontend/src/components/landing/HeroPrompt.tsx` — hero section with question + address inputs.
- `frontend/src/components/landing/AddressAutocomplete.tsx` — Google Places Autocomplete wrapper.
- `frontend/src/router.tsx` — React Router configuration.
- Updated Nginx config for SPA fallback routing.

Acceptance criteria:
- Navigating to `/` shows the landing page with hero prompt section and product info.
- Question field is required; form cannot be submitted without it.
- Address field shows Google Places autocomplete suggestions when typing (when API key is configured).
- Submitting the form navigates to `/map` with the correct query params / router state.
- Map page correctly consumes landing page params: auto-centers if coordinates provided, pre-fills chat with question.
- Direct navigation to `/map` (without landing page) still works as before (existing behavior preserved).
- Landing page is responsive and visually polished (modern, clean design with Tailwind CSS).

## 7) Integration Points and Ordering (No Time Mapping)

Recommended dependency graph:
1. Part B defines API + SSE + schemas first.
2. Part A builds UI/chat state against mocks.
3. Part F builds landing page + routing in parallel with Part A (shared routing layer).
4. Part C builds data abstraction and Overpass provider in parallel.
5. Part D builds OpenRouter streaming + structured output in parallel.
6. Part B integrates C and D.
7. Part F integrates with Part A (landing page passes params to map page).
8. Part E wraps full stack and validates runtime behavior (including SPA routing).

Integration checkpoints:
- Checkpoint 0: F standalone (landing page renders, form submits, navigates to /map route).
- Checkpoint 1: A + F (landing page navigates to map page, params consumed correctly).
- Checkpoint 2: A + B (mock contexts and mock SSE stream).
- Checkpoint 3: B + C (real region context generation, mock LLM stream).
- Checkpoint 4: B + D (real LLM stream using fixture context).
- Checkpoint 5: A + B + C + D full multi-turn streaming chat with landing page entry.
- Checkpoint 6: Full stack via E on target VM (including SPA fallback routing through Nginx).

## 8) Cross-Cutting Non-Functional Requirements

- Streaming UX: first token latency should feel immediate in demo conditions.
- Reliability: explicit fallbacks for data provider failures and LLM output parse failures.
- Explainability: each completed assistant turn includes evidence + limitations + confidence.
- Security: API keys server-side only; model/provider keys never exposed to frontend.
- Observability: request IDs and basic structured logs for context creation and chat turns.
- Compatibility: SSE behavior validated behind Nginx proxy.
- State handling: backend context/chat cache must be externalized in Redis, not process memory.

## 9) Risks and Mitigations

- Overpass latency/rate limits:
  - keep query scope narrow, cache context snapshots in Redis, allow stale fallback for same region.
- Redis unavailable or evicted keys:
  - typed `CONTEXT_NOT_FOUND`/`CACHE_UNAVAILABLE` responses + FE re-create context flow + health checks.
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
      router.tsx
      pages/
        LandingPage.tsx
        MapPage.tsx
      components/
        landing/
          HeroPrompt.tsx
          AddressAutocomplete.tsx
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
      cache/
        redis_client.py
        context_store.py
        cache_keys.py
  redis/
    redis.conf
  nginx/
    default.conf
```

## 11) Handoff Summary by Agent Type

- Frontend agent: owns landing page, client-side routing, Google Places Autocomplete integration, map + multi-turn streaming UI + `sessionStorage` thread persistence.
- Backend agent: owns FastAPI contracts, SSE orchestration, schema enforcement, `uv` dependency management, and Redis context/cache integration.
- Data/geospatial agent: owns `DataSource` abstraction, Overpass provider, and profile aggregation.
- LLM agent: owns OpenRouter integration, model config, and structured-output-compliant streamed turns.
- Infra agent: owns Compose/Nginx/Redis runtime, SPA fallback routing, SSE-safe proxy behavior, and deployment reproducibility.

Each part is intentionally decoupled by typed contracts so teams can develop in parallel and merge with low rework risk.
