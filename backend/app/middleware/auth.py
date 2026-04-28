import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
import jwt
from fastapi import Request
from fastapi.responses import JSONResponse

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"

PUBLIC_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/health",
    "/debug/env",
    "/openapi.json",
    "/docs",
    "/redoc",
}

_jwks_cache: Dict[str, Any] = {}
_jwks_expiry: Optional[datetime] = None


async def _get_jwks() -> Dict[str, Any]:
    global _jwks_cache, _jwks_expiry
    now = datetime.utcnow()
    if _jwks_cache and _jwks_expiry and _jwks_expiry > now:
        return _jwks_cache
    async with httpx.AsyncClient() as client:
        response = await client.get(SUPABASE_JWKS_URL, timeout=5.0)
        response.raise_for_status()
        _jwks_cache = response.json()
        _jwks_expiry = now + timedelta(hours=24)
    return _jwks_cache


async def auth_middleware(request: Request, call_next):
    path = request.url.path

    if request.method == "OPTIONS":
        return await call_next(request)

    if path in PUBLIC_PATHS or path.startswith("/openapi") or path.startswith("/docs"):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "missing_token"})

    token = auth_header.split(" ", 1)[1]

    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        alg = unverified_header.get("alg", "ES256")

        jwks = await _get_jwks()
        key_data = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)

        if not key_data:
            return JSONResponse(status_code=401, content={"detail": "invalid_token"})

        if alg.startswith("RS"):
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key_data))
            algo = "RS256"
        else:
            public_key = jwt.algorithms.ECAlgorithm.from_jwk(json.dumps(key_data))
            algo = "ES256"

        payload = jwt.decode(
            token,
            public_key,
            algorithms=[algo],
            audience="authenticated",
            issuer=f"{SUPABASE_URL}/auth/v1",
        )

        user_id = payload.get("sub")
        if not user_id:
            return JSONResponse(status_code=401, content={"detail": "invalid_token"})

        request.state.user_id = user_id

    except jwt.ExpiredSignatureError:
        return JSONResponse(status_code=401, content={"detail": "token_expired"})
    except jwt.InvalidSignatureError:
        return JSONResponse(status_code=401, content={"detail": "invalid_signature"})
    except Exception:
        return JSONResponse(status_code=401, content={"detail": "invalid_token"})

    return await call_next(request)
