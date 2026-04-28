from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )

    environment: Literal["local", "supabase", "production"] = "local"
    database_url: str = "postgresql://postgres:postgres@database:5432/postgres"

    supabase_url: str = ""
    supabase_key: str = ""
    supabase_jwt_secret: str = ""

    savings_rate: float = 10.0
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache()
def get_settings() -> Settings:
    return Settings()