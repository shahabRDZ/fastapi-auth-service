"""FastAPI application factory with lifespan, middleware, and router registration."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.dependencies import set_redis_client
from app.middleware import RateLimitMiddleware
from app.routers import auth, users


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage startup and shutdown of shared resources."""
    # Startup
    redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    app.state.redis = redis_client
    set_redis_client(redis_client)

    yield

    # Shutdown
    await redis_client.aclose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="FastAPI Auth Service",
        description=(
            "Production-ready authentication microservice with JWT, "
            "PostgreSQL, Redis, and role-based access control."
        ),
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Rate limiting ──────────────────────────────────────────────────────────
    app.add_middleware(RateLimitMiddleware)

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")

    # ── Health check ───────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "version": app.version})

    return app


app = create_app()
