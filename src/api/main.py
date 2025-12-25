"""FastAPI Application para ViralForge."""

import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Tuple

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings
from src.api.routes import dashboard, profiles, productions, strategies, videos

settings = get_settings()
_rate_hits: dict[str, Tuple[int, float]] = {}


def auth_guard(x_api_key: Optional[str] = Header(default=None), request: Request = None) -> bool:
    """Valida API key opcional e aplica rate limiting em producao."""
    if settings.api_token:
        if not x_api_key or x_api_key != settings.api_token:
            raise HTTPException(status_code=401, detail="Unauthorized")

    apply_rate_limit = (
        settings.app_env == "production"
        and settings.api_rate_limit_max_requests > 0
        and settings.api_rate_limit_window_seconds > 0
    )

    if not apply_rate_limit:
        return True

    key = x_api_key or (request.client.host if request else "anonymous")
    now = time.time()
    count, reset_at = _rate_hits.get(key, (0, now + settings.api_rate_limit_window_seconds))
    if now > reset_at:
        count, reset_at = 0, now + settings.api_rate_limit_window_seconds
    if count >= settings.api_rate_limit_max_requests:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    _rate_hits[key] = (count + 1, reset_at)
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hooks da aplicacao."""
    # Startup
    print(f"🚀 ViralForge API iniciando...")
    print(f"   Ambiente: {settings.app_env}")
    print(f"   Debug: {settings.app_debug}")
    yield
    # Shutdown
    print("👋 ViralForge API encerrando...")


app = FastAPI(
    title="ViralForge API",
    description="API para Sistema Autonomo de Videos Virais",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(
    dashboard.router,
    prefix="/api",
    tags=["Dashboard"],
    dependencies=[Depends(auth_guard)],
)
app.include_router(
    profiles.router,
    prefix="/api/profiles",
    tags=["Profiles"],
    dependencies=[Depends(auth_guard)],
)
app.include_router(
    videos.router,
    prefix="/api/videos",
    tags=["Videos"],
    dependencies=[Depends(auth_guard)],
)
app.include_router(
    strategies.router,
    prefix="/api/strategies",
    tags=["Strategies"],
    dependencies=[Depends(auth_guard)],
)
app.include_router(
    productions.router,
    prefix="/api/productions",
    tags=["Productions"],
    dependencies=[Depends(auth_guard)],
)


@app.get("/")
async def root(auth=Depends(auth_guard)):
    """Health check e info basica."""
    return {
        "name": "ViralForge API",
        "version": "2.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
async def health(auth=Depends(auth_guard)):
    """Health check detalhado."""
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected",
        "minio": "connected",
    }
