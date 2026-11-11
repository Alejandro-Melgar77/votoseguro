"""
Modelos ORM: Bitácora Inmutable (AuditLog) y Registro de Llamadas de IA (AiCallLog)
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AuditLog(Base):
    """
    Bitácora de auditoría inmutable (Append-Only).
    Protegida en PostgreSQL mediante un Trigger que prohíbe UPDATE y DELETE.
    """
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chain_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    election_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_role: Mapped[str] = mapped_column(String(40), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )


class AiCallLog(Base):
    """
    Registro trazable de interacciones de IA (asistida y desvinculada del voto).
    """
    __tablename__ = "ai_call_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    election_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    function_name: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="SUCCESS")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
