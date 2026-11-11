"""
Servicio de Registro en Bitácora Inmutable (AuditLog)
"""
import uuid
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.audit import AuditLog


class AuditService:
    @staticmethod
    async def log_event(
        db: AsyncSession,
        action: str,
        entity_type: str,
        entity_id: str,
        actor_role: str,
        actor_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        election_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """
        Registra una entrada inmutable en la bitácora append-only.
        Nunca almacenar votos directos ni identidades vinculadas a opciones de sufragio.
        """
        entry = AuditLog(
            organization_id=organization_id,
            election_id=election_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            payload=payload or {},
            ip_address=ip_address,
        )
        db.add(entry)
        await db.flush()
        return entry

    @staticmethod
    async def list_logs(
        db: AsyncSession,
        organization_id: uuid.UUID | None = None,
        election_id: uuid.UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        stmt = select(AuditLog)
        if organization_id:
            stmt = stmt.where(AuditLog.organization_id == organization_id)
        if election_id:
            stmt = stmt.where(AuditLog.election_id == election_id)
        stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return list(result.scalars().all())
