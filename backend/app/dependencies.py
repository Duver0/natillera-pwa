from fastapi import Request, HTTPException, Depends
from app.db import DatabaseInterface, get_database, is_supabase
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from supabase._async.client import AsyncClient as SupabaseClient


async def get_user_id(request: Request) -> str:
    """Extract validated user_id from request state (set by auth middleware)."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="unauthorized")
    return user_id


async def get_db() -> DatabaseInterface:
    """Yield database interface."""
    return get_database()