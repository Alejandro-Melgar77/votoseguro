"""
Configuración de AsyncEngine y AsyncSessionMaker para SQLAlchemy 2.0
"""
from typing import AsyncGenerator
import ssl
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings

def get_async_db_url(url: str) -> str:
    """Asegura que el protocolo sea postgresql+asyncpg://"""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url

async_db_url = get_async_db_url(settings.DATABASE_URL)

def database_connect_args():
    if not settings.DATABASE_SSL_REQUIRED:
        return {}
    return {"ssl": ssl.create_default_context(cafile=settings.DATABASE_SSL_CA_FILE)}

connection_options = {"connect_args": database_connect_args()}
if settings.DATABASE_PASSWORD_SECRET_ARN:
    from app.db.rds import connect_rds
    connection_options = {"async_creator": connect_rds}

engine = create_async_engine(
    async_db_url,
    echo=settings.DEBUG and settings.ENVIRONMENT == "development",
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    **connection_options,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Inyección de dependencias para sesión asíncrona de base de datos"""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
