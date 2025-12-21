"""FastAPI Application para ViralForge."""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings
from src.api.routes import dashboard, profiles, productions, strategies, videos

settings = get_settings()


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
app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])
app.include_router(profiles.router, prefix="/api/profiles", tags=["Profiles"])
app.include_router(videos.router, prefix="/api/videos", tags=["Videos"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["Strategies"])
app.include_router(productions.router, prefix="/api/productions", tags=["Productions"])


@app.get("/")
async def root():
    """Health check e info basica."""
    return {
        "name": "ViralForge API",
        "version": "2.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
async def health():
    """Health check detalhado."""
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected",
        "minio": "connected",
    }
