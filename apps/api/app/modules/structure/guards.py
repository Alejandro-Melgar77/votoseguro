"""
Guardias de Inmutabilidad Estructural (Regla Invariante #3)
"""
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ConflictException, NotFoundException
from app.db.models.election import Election, ElectionStatus
from app.db.models.structure import VoterGroup


async def require_election_draft(db: AsyncSession, election_id: uuid.UUID) -> Election:
    """
    Verifica que la elección exista y se encuentre estrictamente en estado DRAFT.
    Si la elección ya fue publicada (SCHEDULED, REGISTRATION_OPEN, etc.),
    lanza HTTP 409 Conflict impidiendo cualquier mutación sobre la estructura.
    """
    stmt = select(Election).where(Election.id == election_id)
    election = (await db.execute(stmt)).scalar_one_or_none()
    if not election:
        raise NotFoundException("Elección no encontrada.")

    if election.status != ElectionStatus.DRAFT:
        raise ConflictException(
            "La estructura de la elección está congelada tras su publicación (config_hash emitido) y no admite modificaciones."
        )
    return election


async def require_group_draft(db: AsyncSession, group_id: uuid.UUID) -> tuple[VoterGroup, Election]:
    """
    Obtiene el VoterGroup y verifica que su elección asociada esté en estado DRAFT.
    """
    stmt = select(VoterGroup).where(VoterGroup.id == group_id)
    group = (await db.execute(stmt)).scalar_one_or_none()
    if not group:
        raise NotFoundException("Grupo de votantes no encontrado.")

    election = await require_election_draft(db, group.election_id)
    return group, election
