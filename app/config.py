from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ContextPilot"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"
    temperature: float = 0.2
    top_p: float = 0.9
    max_tokens: int = 700
    rate_limit_per_minute: int = 30
    cache_ttl_seconds: int = 300
    vector_dimensions: int = 384
    allow_mock_provider: bool = True
    agent_max_steps: int = 4
    agent_max_context_chars: int = 5000

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
