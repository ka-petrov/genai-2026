from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openrouter_api_key: str = ""
    llm_model_id: str = "google/gemini-2.5-flash-preview"

    overpass_url: str = "https://overpass-api.de/api/interpreter"
    overpass_timeout: float = 30.0

    redis_url: str = "redis://localhost:6379/0"
    redis_context_ttl_seconds: int = 3600
    redis_region_ttl_seconds: int = 900

    log_level: str = "info"

    model_config = {"env_file": ".env"}


settings = Settings()
