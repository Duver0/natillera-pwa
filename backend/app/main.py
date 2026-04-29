from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.db import init_database, close_database
from app.middleware.auth import auth_middleware
from app.middleware.error_handler import register_error_handlers
from app.routes import (
    auth_router,
    client_router,
    credit_router,
    installment_router,
    payment_router,
    savings_router,
    history_router,
)

limiter = Limiter(key_func=get_remote_address)

_test_mode = False


def set_test_mode(enabled: bool = True):
    global _test_mode
    _test_mode = enabled


def is_test_mode() -> bool:
    return _test_mode


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db import is_test_mode as _is_test_mode
    
    if _is_test_mode():
        yield
        return
    
    try:
        await init_database()
        print(f"Database initialized. Environment: {get_settings().environment}")
    except Exception as e:
        print(f"ERROR initializing database: {e}")
        import traceback
        traceback.print_exc()
        raise
    yield
    await close_database()


settings = get_settings()

app = FastAPI(
    title="Natillera PWA API",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.middleware("http")(auth_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(client_router.router, prefix="/api/v1/clients", tags=["clients"])
app.include_router(credit_router.router, prefix="/api/v1/credits", tags=["credits"])
app.include_router(installment_router.router, prefix="/api/v1/installments", tags=["installments"])
app.include_router(payment_router.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(savings_router.router, prefix="/api/v1/savings", tags=["savings"])
app.include_router(history_router.router, prefix="/api/v1/history", tags=["history"])


@app.get("/health")
async def health():
    from app.db import get_database
    db_status = "unknown"
    try:
        db = get_database()
        if db:
            db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "ok",
        "version": "1.0.0",
        "database": db_status
    }


@app.get("/debug/env")
async def debug_env():
    s = get_settings()
    return {
        "environment": s.environment,
        "supabase_url": s.supabase_url[:20] + "..." if s.supabase_url else "NOT SET",
        "supabase_key_set": bool(s.supabase_key),
        "supabase_anon_key_set": bool(s.supabase_anon_key),
    }