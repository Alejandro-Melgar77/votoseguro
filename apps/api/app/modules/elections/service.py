"""
Servicio de Gestión de Elecciones y Cronograma Electoral (S1-02)
"""
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException, UnprocessableEntityException
from app.core.time import TimeProvider
from app.db.models.election import Election, ElectionStatus, ScheduleChange
from app.db.models.user import User
from app.modules.audit.service import AuditService
from app.modules.elections.schemas import (
    ElectionCreateRequest,
    ElectionUpdateRequest,
    ScheduleUpdateRequest,
)
from app.modules.elections.schedule_validator import (
    ensure_utc,
    validate_and_diff_schedule_update,
)


class ElectionService:
    @staticmethod
    async def create_election(
        db: AsyncSession,
        payload: ElectionCreateRequest,
        creator: User,
        time_provider: TimeProvider,
        client_ip: str | None = None,
    ) -> Election:
        db_now = await time_provider.now(db)

        reg_open = ensure_utc(payload.registration_opens_at)
        reg_close = ensure_utc(payload.registration_closes_at)
        vote_open = ensure_utc(payload.voting_opens_at)
        vote_close = ensure_utc(payload.voting_closes_at)

        if not (reg_open < reg_close <= vote_open < vote_close):
            raise UnprocessableEntityException(
                "El orden cronológico es inválido: registration_opens_at < registration_closes_at <= voting_opens_at < voting_closes_at"
            )

        election = Election(
            organization_id=creator.organization_id,
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            timezone=payload.timezone,
            registration_opens_at=reg_open,
            registration_closes_at=reg_close,
            voting_opens_at=vote_open,
            voting_closes_at=vote_close,
            status=ElectionStatus.DRAFT,
            k_anonymity=payload.k_anonymity,
            created_by=creator.id,
            created_at=db_now,
            updated_at=db_now,
        )
        db.add(election)
        await db.flush()

        await AuditService.log_event(
            db=db,
            action="ELECTION_CREATED",
            entity_type="election",
            entity_id=str(election.id),
            actor_role=creator.role.value,
            actor_id=creator.id,
            organization_id=creator.organization_id,
            election_id=election.id,
            payload={"name": election.name, "timezone": election.timezone},
            ip_address=client_ip,
        )
        await db.commit()
        await db.refresh(election)
        return election

    @staticmethod
    async def list_elections(
        db: AsyncSession, organization_id: uuid.UUID
    ) -> list[Election]:
        stmt = (
            select(Election)
            .where(Election.organization_id == organization_id)
            .order_by(Election.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_election(
        db: AsyncSession, election_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Election:
        stmt = select(Election).where(
            Election.id == election_id,
            Election.organization_id == organization_id,
        )
        election = (await db.execute(stmt)).scalar_one_or_none()
        if not election:
            raise NotFoundException("La elección indicada no existe en su organización.")
        return election

    @staticmethod
    async def update_election_meta(
        db: AsyncSession,
        election_id: uuid.UUID,
        organization_id: uuid.UUID,
        payload: ElectionUpdateRequest,
        updater: User,
        time_provider: TimeProvider,
        client_ip: str | None = None,
    ) -> Election:
        db_now = await time_provider.now(db)
        election = await ElectionService.get_election(db, election_id, organization_id)

        if payload.name is not None:
            election.name = payload.name.strip()
        if payload.description is not None:
            election.description = payload.description.strip()
        if payload.timezone is not None:
            election.timezone = payload.timezone.strip()
        if payload.k_anonymity is not None:
            election.k_anonymity = payload.k_anonymity

        election.updated_at = db_now
        await AuditService.log_event(
            db=db,
            action="ELECTION_METADATA_UPDATED",
            entity_type="election",
            entity_id=str(election.id),
            actor_role=updater.role.value,
            actor_id=updater.id,
            organization_id=organization_id,
            election_id=election.id,
            payload={"name": election.name, "timezone": election.timezone},
            ip_address=client_ip,
        )
        await db.commit()
        await db.refresh(election)
        return election

    @staticmethod
    async def update_schedule(
        db: AsyncSession,
        election_id: uuid.UUID,
        organization_id: uuid.UUID,
        payload: ScheduleUpdateRequest,
        updater: User,
        time_provider: TimeProvider,
        client_ip: str | None = None,
    ) -> Election:
        db_now = await time_provider.now(db)
        election = await ElectionService.get_election(db, election_id, organization_id)

        # Validar reglas de cronograma y obtener diferencias
        diffs = validate_and_diff_schedule_update(election, payload, db_now)

        if not diffs:
            return election

        reason_text = payload.reason.strip() if payload.reason else "Ajuste de cronograma en borrador"

        # Aplicar cambios y registrar en schedule_change
        for diff in diffs:
            setattr(election, diff.field_name, diff.new_value)

            change_record = ScheduleChange(
                organization_id=organization_id,
                election_id=election.id,
                field_name=diff.field_name,
                old_value=diff.old_value,
                new_value=diff.new_value,
                election_status_at_change=election.status.value,
                reason=reason_text,
                changed_by=updater.id,
                changed_at=db_now,
            )
            db.add(change_record)

        election.updated_at = db_now

        await AuditService.log_event(
            db=db,
            action="SCHEDULE_UPDATED",
            entity_type="election",
            entity_id=str(election.id),
            actor_role=updater.role.value,
            actor_id=updater.id,
            organization_id=organization_id,
            election_id=election.id,
            payload={
                "diffs": [
                    {
                        "field": d.field_name,
                        "old": d.old_value.isoformat(),
                        "new": d.new_value.isoformat(),
                    }
                    for d in diffs
                ],
                "reason": reason_text,
            },
            ip_address=client_ip,
        )
        await db.commit()
        await db.refresh(election)
        return election

    @staticmethod
    async def open_registration_now(
        db: AsyncSession,
        election_id: uuid.UUID,
        organization_id: uuid.UUID,
        actor: User,
        time_provider: TimeProvider,
        client_ip: str | None = None,
    ) -> Election:
        db_now = await time_provider.now(db)
        election = await ElectionService.get_election(db, election_id, organization_id)

        # Regla: solo permitido en SCHEDULED
        if election.status != ElectionStatus.SCHEDULED:
            raise ConflictException(
                f"La acción 'Abrir registro ahora' solo está permitida cuando la elección está programada (SCHEDULED). Estado actual: {election.status.value}"
            )

        if db_now >= election.registration_closes_at:
            raise ConflictException(
                "No se puede abrir el registro porque la fecha de cierre de registro ya ha expirado."
            )

        old_open = election.registration_opens_at
        election.registration_opens_at = db_now
        election.status = ElectionStatus.REGISTRATION_OPEN
        election.updated_at = db_now

        reason = "Apertura inmediata manual del registro por el Administrador General"

        change_record = ScheduleChange(
            organization_id=organization_id,
            election_id=election.id,
            field_name="registration_opens_at",
            old_value=old_open,
            new_value=db_now,
            election_status_at_change=ElectionStatus.SCHEDULED.value,
            reason=reason,
            changed_by=actor.id,
            changed_at=db_now,
        )
        db.add(change_record)

        await AuditService.log_event(
            db=db,
            action="ELECTION_REGISTRATION_OPENED_NOW",
            entity_type="election",
            entity_id=str(election.id),
            actor_role=actor.role.value,
            actor_id=actor.id,
            organization_id=organization_id,
            election_id=election.id,
            payload={
                "previous_open": old_open.isoformat(),
                "new_open": db_now.isoformat(),
                "reason": reason,
            },
            ip_address=client_ip,
        )
        await db.commit()
        await db.refresh(election)
        return election

    @staticmethod
    async def list_schedule_history(
        db: AsyncSession, election_id: uuid.UUID, organization_id: uuid.UUID
    ) -> list[ScheduleChange]:
        # Validar existencia de la elección en el tenant
        await ElectionService.get_election(db, election_id, organization_id)

        stmt = (
            select(ScheduleChange)
            .where(
                ScheduleChange.election_id == election_id,
                ScheduleChange.organization_id == organization_id,
            )
            .order_by(ScheduleChange.changed_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
