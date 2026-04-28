from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
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
    supabase_anon_key: str = ""
    supabase_jwt_secret: str = ""

    savings_rate: float = 10.0
    cors_origins: list[str] = ["http://localhost:5173"]

    @model_validator(mode="after")
    def resolve_supabase_key(self):
        if not self.supabase_key and self.supabase_anon_key:
            self.supabase_key = self.supabase_anon_key
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()