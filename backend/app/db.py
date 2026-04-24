from supabase._async.client import AsyncClient, create_client
from app.config import get_settings
from functools import lru_cache

_client: AsyncClient | None = None


async def init_supabase() -> None:
    global _client
    settings = get_settings()
    _client = await create_client(settings.supabase_url, settings.supabase_key)


def get_supabase() -> AsyncClient:
    if _client is None:
        raise RuntimeError("Supabase client not initialized. Call init_supabase() first.")
    return _client
