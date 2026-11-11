"""
Motor Autónomo de Transiciones de Fase Electoral (APScheduler Worker)
Idempotente, con bloqueo transaccional distribuido en PostgreSQL y reloj de base de datos.
"""
import secrets
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import TimeProvider
from app.crypto.hashing import canonical_json, sha256_hex
from app.db.models.election import Election, ElectionStatus
from app.db.models.voter import LinkStatus, RegistrationLink, Voter, VoterStatus
from app.db.models.voting import VotingCredential
from app.modules.audit.service import AuditService

ADVISORY_LOCK_ID = 849201


def generate_credential_code() -> str:
    """Genera un código legible de credencial de un solo uso con formato VS-XXXX-XXXX-XXXX."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    p1 = "".join(secrets.choice(alphabet) for _ in range(4))
    p2 = "".join(secrets.choice(alphabet) for _ in range(4))
    p3 = "".join(secrets.choice(alphabet) for _ in range(4))
    return f"VS-{p1}-{p2}-{p3}"


async def run_scheduler_tick(session: AsyncSession, time_provider: TimeProvider) -> list[str]:
    """
    Ejecuta un ciclo de verificación y transición de fases electorales.
    Retorna la lista de eventos procesados en este tick.
    """
    events: list[str] = []

    # 1. Adquisición de bloqueo transaccional distribuido (solo si es PostgreSQL)
    bind = session.bind or session.get_bind()
    dialect_name = bind.dialect.name if bind else "postgresql"

    if dialect_name == "postgresql":
        lock_res = await session.execute(
            text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
            {"lock_id": ADVISORY_LOCK_ID},
        )
        has_lock = lock_res.scalar()
        if not has_lock:
            # Otro worker o hilo está procesando el tick en este instante
            return []

    # 2. Hora canónica oficial del servidor
    db_now = await time_provider.now(session)

    # -------------------------------------------------------------------------
    # Transición 1: SCHEDULED -> REGISTRATION_OPEN
    # -------------------------------------------------------------------------
    stmt_to_reg_open = select(Election).where(
        Election.status == ElectionStatus.SCHEDULED,
        Election.registration_opens_at <= db_now,
    )
    res_to_reg_open = await session.execute(stmt_to_reg_open)
    for election in res_to_reg_open.scalars().all():
        election.status = ElectionStatus.REGISTRATION_OPEN
        election.updated_at = db_now

        event_msg = f"Elección '{election.name}' [{election.id}]: Abierta fase de Registro de Votantes"
        events.append(event_msg)

        await AuditService.log_event(
            db=session,
            action="ELECTION_REGISTRATION_OPENED",
            entity_type="election",
            entity_id=str(election.id),
            actor_role="SCHEDULER",
            organization_id=election.organization_id,
            election_id=election.id,
            payload={"status": election.status.value, "timestamp": db_now.isoformat()},
        )

    # -------------------------------------------------------------------------
    # Transición 2: REGISTRATION_OPEN -> REGISTRATION_CLOSED (Congelamiento de Padrón)
    # -------------------------------------------------------------------------
    stmt_to_reg_close = select(Election).where(
        Election.status == ElectionStatus.REGISTRATION_OPEN,
        Election.registration_closes_at <= db_now,
    )
    res_to_reg_close = await session.execute(stmt_to_reg_close)
    for election in res_to_reg_close.scalars().all():
        election.status = ElectionStatus.REGISTRATION_CLOSED
        election.registration_frozen_at = db_now
        election.updated_at = db_now

        # Congelamiento del padrón: seleccionar votantes ACTIVE ordenados por document_id
        stmt_voters = (
            select(Voter)
            .where(
                Voter.election_id == election.id,
                Voter.status == VoterStatus.ACTIVE,
            )
            .order_by(Voter.document_id.asc())
        )
        active_voters = (await session.execute(stmt_voters)).scalars().all()

        canonical_roll_data = [
            {
                "document_id": v.document_id,
                "full_name": v.full_name,
                "group_id": str(v.group_id),
                "node_id": str(v.node_id),
                "attributes": v.attributes,
            }
            for v in active_voters
        ]
        roll_hash = sha256_hex(canonical_json(canonical_roll_data))
        election.roll_hash = roll_hash

        # Expirar enlaces de registro activos
        await session.execute(
            update(RegistrationLink)
            .where(
                RegistrationLink.election_id == election.id,
                RegistrationLink.status == LinkStatus.ACTIVE,
            )
            .values(status=LinkStatus.EXPIRED)
        )

        event_msg = f"Elección '{election.name}' [{election.id}]: Cerrado y congelado el padrón electoral (roll_hash: {roll_hash[:16]}...)"
        events.append(event_msg)

        await AuditService.log_event(
            db=session,
            action="ELECTION_REGISTRATION_CLOSED_AND_FROZEN",
            entity_type="election",
            entity_id=str(election.id),
            actor_role="SCHEDULER",
            organization_id=election.organization_id,
            election_id=election.id,
            payload={
                "roll_hash": roll_hash,
                "active_voters_count": len(active_voters),
                "timestamp": db_now.isoformat(),
            },
        )

    # -------------------------------------------------------------------------
    # Transición 3: REGISTRATION_CLOSED -> VOTING_OPEN (Emisión de Credenciales)
    # -------------------------------------------------------------------------
    stmt_to_vote_open = select(Election).where(
        Election.status == ElectionStatus.REGISTRATION_CLOSED,
        Election.voting_opens_at <= db_now,
    )
    res_to_vote_open = await session.execute(stmt_to_vote_open)
    for election in res_to_vote_open.scalars().all():
        election.status = ElectionStatus.VOTING_OPEN
        election.updated_at = db_now

        # Emisión de credenciales para votantes ACTIVE que aún no la posean
        stmt_active_voters = (
            select(Voter)
            .where(
                Voter.election_id == election.id,
                Voter.status == VoterStatus.ACTIVE,
            )
        )
        active_voters = (await session.execute(stmt_active_voters)).scalars().all()

        issued_count = 0
        for v in active_voters:
            # Comprobar si ya tiene credencial
            stmt_cred = select(VotingCredential).where(
                VotingCredential.voter_id == v.id,
                VotingCredential.election_id == election.id,
            )
            existing_cred = (await session.execute(stmt_cred)).scalar_one_or_none()
            if not existing_cred:
                raw_token = generate_credential_code()
                token_hash = sha256_hex(raw_token)
                cred = VotingCredential(
                    election_id=election.id,
                    voter_id=v.id,
                    token_hash=token_hash,
                    raw_token=raw_token,
                    issued_at=db_now,
                    expires_at=election.voting_closes_at,
                    used_at=None,
                )
                session.add(cred)
                issued_count += 1

        event_msg = f"Elección '{election.name}' [{election.id}]: Votación abierta (Credenciales emitidas: {issued_count})"
        events.append(event_msg)

        await AuditService.log_event(
            db=session,
            action="ELECTION_VOTING_OPENED",
            entity_type="election",
            entity_id=str(election.id),
            actor_role="SCHEDULER",
            organization_id=election.organization_id,
            election_id=election.id,
            payload={
                "credentials_issued": issued_count,
                "timestamp": db_now.isoformat(),
            },
        )

    # -------------------------------------------------------------------------
    # Transición 4: VOTING_OPEN -> VOTING_CLOSED
    # -------------------------------------------------------------------------
    stmt_to_vote_close = select(Election).where(
        Election.status == ElectionStatus.VOTING_OPEN,
        Election.voting_closes_at <= db_now,
    )
    res_to_vote_close = await session.execute(stmt_to_vote_close)
    for election in res_to_vote_close.scalars().all():
        election.status = ElectionStatus.VOTING_CLOSED
        election.voting_closed_at = db_now
        election.updated_at = db_now

        event_msg = f"Elección '{election.name}' [{election.id}]: Votación finalizada y cerrada para cómputo"
        events.append(event_msg)

        await AuditService.log_event(
            db=session,
            action="ELECTION_VOTING_CLOSED",
            entity_type="election",
            entity_id=str(election.id),
            actor_role="SCHEDULER",
            organization_id=election.organization_id,
            election_id=election.id,
            payload={"timestamp": db_now.isoformat()},
        )

    await session.commit()
    return events
