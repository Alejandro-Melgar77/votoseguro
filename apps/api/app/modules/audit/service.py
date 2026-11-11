"""
Servicio de Registro y Verificación en Bitácora Inmutable (AuditLog) - S2-05
"""
import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto.hashing import canonical_json, sha256_hex
from app.db.models.audit import AiCallLog, AuditLog


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
        Registra una entrada inmutable en la bitácora append-only encadenada con hashes SHA-256.
        Nunca almacenar votos directos ni identidades vinculadas a opciones de sufragio.
        """
        # S2-05: Encadenamiento por organización o global
        stmt_last = select(AuditLog)
        if organization_id:
            stmt_last = stmt_last.where(AuditLog.organization_id == organization_id)
        stmt_last = stmt_last.order_by(AuditLog.chain_index.desc()).limit(1)
        last_entry = (await db.execute(stmt_last)).scalar_one_or_none()

        if last_entry and last_entry.entry_hash:
            prev_hash = last_entry.entry_hash
            chain_index = last_entry.chain_index + 1
        else:
            prev_hash = sha256_hex(f"VOTOSEGURO:AUDIT_GENESIS:{organization_id or 'GLOBAL'}")
            chain_index = 1

        now_utc = datetime.now(timezone.utc)
        entry_payload = {
            "chain_index": chain_index,
            "prev_hash": prev_hash,
            "organization_id": str(organization_id) if organization_id else None,
            "election_id": str(election_id) if election_id else None,
            "actor_id": str(actor_id) if actor_id else None,
            "actor_role": actor_role,
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "payload": payload or {},
            "created_at_iso": now_utc.isoformat(),
        }
        entry_hash = sha256_hex(canonical_json(entry_payload))

        entry = AuditLog(
            chain_index=chain_index,
            organization_id=organization_id,
            election_id=election_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            payload=payload or {},
            ip_address=ip_address,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
            created_at=now_utc,
        )
        db.add(entry)
        await db.flush()
        return entry

    @staticmethod
    async def log_ai_call(
        db: AsyncSession,
        organization_id: uuid.UUID | None,
        election_id: uuid.UUID | None,
        function_name: str,
        model_name: str,
        duration_ms: int,
        status: str,
        summary: str,
    ) -> AiCallLog:
        """
        S2-05: Registro unificado de eventos de IA en ai_call_log y audit_log.
        """
        ai_entry = AiCallLog(
            organization_id=organization_id,
            election_id=election_id,
            function_name=function_name,
            model=model_name,
            duration_ms=duration_ms,
            status=status,
            summary=summary,
        )
        db.add(ai_entry)
        await db.flush()

        await AuditService.log_event(
            db=db,
            action="AI_EVENT_RECORDED",
            entity_type="ai_call_log",
            entity_id=str(ai_entry.id),
            actor_role="SYSTEM_AI",
            organization_id=organization_id,
            election_id=election_id,
            payload={
                "function_name": function_name,
                "model": model_name,
                "duration_ms": duration_ms,
                "status": status,
                "summary": summary,
            },
        )
        return ai_entry

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
        stmt = stmt.order_by(AuditLog.chain_index.desc(), AuditLog.id.desc()).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return list(result.scalars().all())
