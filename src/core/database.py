"""Configuracao do banco de dados com SQLAlchemy para ViralForge."""

from collections.abc import AsyncGenerator
from typing import Tuple

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config.settings import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    """Base class para todos os modelos SQLAlchemy."""

    pass


def _resolve_connection_urls(database_url: str) -> Tuple[str, str]:
    """Retorna URLs sincronas e assincronas adequadas para o driver informado.

    Suporta:
    - postgresql / postgresql+psycopg2 / postgresql+asyncpg
    - sqlite / sqlite+aiosqlite
    """
    url: URL = make_url(database_url)
    driver = url.drivername

    if driver == "postgresql":
        sync_url = url.set(drivername="postgresql+psycopg2")
        async_url = url.set(drivername="postgresql+asyncpg")
    elif driver == "postgresql+psycopg2":
        sync_url = url
        async_url = url.set(drivername="postgresql+asyncpg")
    elif driver == "postgresql+asyncpg":
        sync_url = url.set(drivername="postgresql+psycopg2")
        async_url = url
    elif driver in {"sqlite", "sqlite+pysqlite"}:
        sync_url = url.set(drivername="sqlite")
        async_url = url.set(drivername="sqlite+aiosqlite")
    elif driver == "sqlite+aiosqlite":
        sync_url = url.set(drivername="sqlite")
        async_url = url
    else:
        # Driver nao tratado - usa o mesmo para sync/async
        sync_url = url
        async_url = url

    return (
        sync_url.render_as_string(hide_password=False),
        async_url.render_as_string(hide_password=False),
    )


# Resolve URLs sync e async
sync_url, async_url = _resolve_connection_urls(settings.database_url)

# Engine sincrono (para scripts, migrations e init)
sync_engine = create_engine(
    sync_url,
    echo=settings.is_development,
    pool_pre_ping=True,
)

# Engine assincrono (para a aplicacao FastAPI)
async_engine = create_async_engine(
    async_url,
    echo=settings.is_development,
    pool_pre_ping=True,
)

# Session factories
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False,
    autoflush=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para injetar sessao do banco em endpoints FastAPI."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_sync_db():
    """Retorna sessao sincrona para uso em scripts e Celery tasks."""
    return SyncSessionLocal()


def init_db() -> None:
    """Inicializa o banco de dados (cria tabelas via SQLAlchemy models)."""
    Base.metadata.create_all(bind=sync_engine)
