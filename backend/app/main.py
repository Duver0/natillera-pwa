from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.db import init_supabase
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_supabase()
    yield


settings = get_settings()

app = FastAPI(
    title="Natillera PWA API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(auth_middleware)

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
    return {"status": "ok"}
