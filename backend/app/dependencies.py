from fastapi import Request, HTTPException, Depends
from supabase._async.client import AsyncClient as SupabaseClient
from app.db import get_supabase


async def get_user_id(request: Request) -> str:
    """Extract validated user_id from request state (set by auth middleware)."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="unauthorized")
    return user_id


async def get_db() -> SupabaseClient:
    """Yield Supabase async client."""
    return get_supabase()
