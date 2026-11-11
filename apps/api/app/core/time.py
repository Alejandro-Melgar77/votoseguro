"""
Autoridad del Tiempo Oficial (Regla Invariante #6)
Nunca confiar en la hora local del proceso de Python ni del cliente.
La base de datos PostgreSQL actúa como árbitro temporal absoluto mediante SELECT now().
"""
from datetime import datetime, timedelta, timezone
from typing import Protocol
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TimeProvider(Protocol):
    async def now(self, db: AsyncSession) -> datetime:
        """Retorna la fecha y hora actual garantizada en UTC."""
        ...


class DatabaseTimeProvider:
    """
    Proveedor de tiempo de producción: consulta directamente a PostgreSQL.
    Garantiza consistencia entre múltiples réplicas y trabajadores del backend.
    """

    async def now(self, db: AsyncSession) -> datetime:
        result = await db.execute(text("SELECT now() AT TIME ZONE 'UTC'"))
        db_now = result.scalar()
        if db_now.tzinfo is None:
            db_now = db_now.replace(tzinfo=timezone.utc)
        return db_now


class FakeTimeProvider:
    """
    Proveedor de tiempo simulado (FrozenClock) para pruebas automatizadas con pytest.
    Permite manipular el avance temporal determinísticamente sin esperas reales.
    """

    def __init__(self, initial_time: datetime | None = None):
        if initial_time is None:
            self._current_time = datetime(2026, 11, 25, 8, 0, 0, tzinfo=timezone.utc)
        else:
            self._current_time = (
                initial_time if initial_time.tzinfo else initial_time.replace(tzinfo=timezone.utc)
            )

    async def now(self, db: AsyncSession | None = None) -> datetime:
        return self._current_time

    def set_time(self, new_time: datetime) -> None:
        self._current_time = new_time if new_time.tzinfo else new_time.replace(tzinfo=timezone.utc)

    def advance(self, **kwargs) -> datetime:
        self._current_time += timedelta(**kwargs)
        return self._current_time


# Instancia por defecto para inyección
default_time_provider: TimeProvider = DatabaseTimeProvider()
