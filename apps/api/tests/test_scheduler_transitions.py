"""
Pruebas de Invariante: Transiciones Autónomas e Idempotentes del Scheduler (RF-12, RF-25, RF-30)
Valida la máquina de estados temporal gobernada por SELECT now() y APScheduler.
"""
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import FakeTimeProvider
from app.db.models.election import Election, ElectionStatus
from app.db.models.structure import HierarchyLevel, UnitNode, VoterGroup
from app.db.models.voter import Voter, VoterStatus
from app.db.models.voting import VotingCredential
from app.modules.scheduler.transition_service import run_scheduler_tick


@pytest.mark.asyncio
async def test_scheduler_complete_lifecycle_transitions(test_db: AsyncSession, org1_setup, fake_time: FakeTimeProvider):
    org, admin, _ = org1_setup
    base_time = datetime(2026, 11, 25, 8, 0, 0, tzinfo=timezone.utc)
    fake_time.set_time(base_time)

    # 1. Definir marcas temporales de la elección
    t_reg_open = base_time + timedelta(hours=2)
    t_reg_close = base_time + timedelta(hours=6)
    t_vote_open = base_time + timedelta(hours=8)
    t_vote_close = base_time + timedelta(hours=14)

    election = Election(
        organization_id=org.id,
        name="Elección de Prueba Ciclo Completo",
        description="Ciclo de vida automático",
        timezone="America/La_Paz",
        registration_opens_at=t_reg_open,
        registration_closes_at=t_reg_close,
        voting_opens_at=t_vote_open,
        voting_closes_at=t_vote_close,
        status=ElectionStatus.SCHEDULED,  # Ya publicada
        k_anonymity=5,
        created_by=admin.id,
        created_at=base_time,
        updated_at=base_time,
    )
    test_db.add(election)
    await test_db.flush()

    # Estructura mínima para empadronar votantes
    group = VoterGroup(
        organization_id=org.id,
        election_id=election.id,
        name="ESTUDIANTES",
        code="EST",
    )
    test_db.add(group)
    await test_db.flush()

    level = HierarchyLevel(
        group_id=group.id,
        depth=1,
        name="Universidad",
    )
    test_db.add(level)
    await test_db.flush()

    node = UnitNode(
        group_id=group.id,
        level_id=level.id,
        parent_id=None,
        name="Universidad EL GRAN ESTUDIO",
        code="UNIV",
        path="/UNIV/",
        depth=1,
    )
    test_db.add(node)
    await test_db.flush()

    # Votantes en el padrón
    voter1 = Voter(
        organization_id=org.id,
        election_id=election.id,
        group_id=group.id,
        node_id=node.id,
        document_id="CI-1001",
        full_name="Carlos Votante Uno",
        status=VoterStatus.ACTIVE,
    )
    voter2 = Voter(
        organization_id=org.id,
        election_id=election.id,
        group_id=group.id,
        node_id=node.id,
        document_id="CI-1002",
        full_name="Maria Votante Dos",
        status=VoterStatus.ACTIVE,
    )
    test_db.add_all([voter1, voter2])
    await test_db.commit()

    # -------------------------------------------------------------------------
    # Hito 1: Avanzar tiempo hasta registration_opens_at
    # -------------------------------------------------------------------------
    fake_time.set_time(t_reg_open)
    events1 = await run_scheduler_tick(test_db, fake_time)
    assert any("Abierta fase de Registro" in e for e in events1)

    await test_db.refresh(election)
    assert election.status == ElectionStatus.REGISTRATION_OPEN

    # -------------------------------------------------------------------------
    # Hito 2: Avanzar tiempo hasta registration_closes_at
    # -------------------------------------------------------------------------
    fake_time.set_time(t_reg_close)
    events2 = await run_scheduler_tick(test_db, fake_time)
    assert any("Cerrado y congelado el padrón" in e for e in events2)

    await test_db.refresh(election)
    assert election.status == ElectionStatus.REGISTRATION_CLOSED
    assert election.roll_hash is not None
    assert len(election.roll_hash) == 64
    assert election.registration_frozen_at is not None

    # -------------------------------------------------------------------------
    # Hito 3: Avanzar tiempo hasta voting_opens_at
    # -------------------------------------------------------------------------
    fake_time.set_time(t_vote_open)
    events3 = await run_scheduler_tick(test_db, fake_time)
    assert any("Votación abierta" in e for e in events3)

    await test_db.refresh(election)
    assert election.status == ElectionStatus.VOTING_OPEN

    # Verificar que se hayan emitido credenciales para los votantes ACTIVE
    stmt_creds = select(VotingCredential).where(VotingCredential.election_id == election.id)
    credentials = (await test_db.execute(stmt_creds)).scalars().all()
    assert len(credentials) == 2
    assert all(c.used_at is None for c in credentials)

    # -------------------------------------------------------------------------
    # Hito 4: Avanzar tiempo hasta voting_closes_at
    # -------------------------------------------------------------------------
    fake_time.set_time(t_vote_close)
    events4 = await run_scheduler_tick(test_db, fake_time)
    assert any("Votación finalizada y cerrada" in e for e in events4)

    await test_db.refresh(election)
    assert election.status == ElectionStatus.VOTING_CLOSED
    assert election.voting_closed_at is not None
