from fastapi import FastAPI

app = FastAPI(title="GenGeo API", version="0.0.1")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


# POST /api/contexts       — Part B
# POST /api/chat/stream    — Part B
