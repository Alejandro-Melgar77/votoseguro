"""
Pruebas de Invariante: Enlaces de Registro, Activación del Votante y Congelamiento del Padrón (S1-08)
Valida Invariante #5 (Inmutabilidad Temporal del Padrón y roll_hash) e Invariante #7 (Activación requerida para sufragar).
"""
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import FakeTimeProvider
from app.db.models.election import Election, ElectionStatus
from app.db.models.structure import HierarchyLevel, UnitNode, VoterGroup
from app.db.models.voter import LinkStatus, RegistrationLink, Voter, VoterStatus


@pytest.mark.asyncio
async def test_registration_links_and_roll_hash(
    test_db: AsyncSession,
    client: AsyncClient,
    org1_setup,
    fake_time: FakeTimeProvider,
):
    org, admin, admin_token = org1_setup
    now = datetime(2026, 11, 25, 9, 0, 0, tzinfo=timezone.utc)
    fake_time.set_time(now)

    t_reg_open = now - timedelta(hours=1)
    t_reg_close = now + timedelta(days=2)
    t_vote_open = now + timedelta(days=3)
    t_vote_close = now + timedelta(days=4)

    # 1. Crear Elección en REGISTRATION_OPEN
    election = Election(
        organization_id=org.id,
        name="Elección Universitaria S1-08",
        timezone="America/La_Paz",
        registration_opens_at=t_reg_open,
        registration_closes_at=t_reg_close,
        voting_opens_at=t_vote_open,
        voting_closes_at=t_vote_close,
        status=ElectionStatus.REGISTRATION_OPEN,
        k_anonymity=5,
        created_by=admin.id,
    )
    test_db.add(election)
    await test_db.flush()

    # 2. Estructura: Grupo y Nodos
    group = VoterGroup(
        organization_id=org.id,
        election_id=election.id,
        name="ESTUDIANTES",
        code="EST",
    )
    test_db.add(group)
    await test_db.flush()

    lvl_univ = HierarchyLevel(group_id=group.id, depth=1, name="Universidad")
    lvl_fac = HierarchyLevel(group_id=group.id, depth=2, name="Facultad")
    lvl_car = HierarchyLevel(group_id=group.id, depth=3, name="Carrera")
    test_db.add_all([lvl_univ, lvl_fac, lvl_car])
    await test_db.flush()

    node_univ = UnitNode(group_id=group.id, level_id=lvl_univ.id, parent_id=None, name="UNIV", code="UNIV", path="/UNIV/", depth=1)
    test_db.add(node_univ)
    await test_db.flush()

    node_ficct = UnitNode(group_id=group.id, level_id=lvl_fac.id, parent_id=node_univ.id, name="FICCT", code="FICCT", path="/UNIV/FICCT/", depth=2)
    node_fceh = UnitNode(group_id=group.id, level_id=lvl_fac.id, parent_id=node_univ.id, name="FCEH", code="FCEH", path="/UNIV/FCEH/", depth=2)
    test_db.add_all([node_ficct, node_fceh])
    await test_db.flush()

    node_inf = UnitNode(group_id=group.id, level_id=lvl_car.id, parent_id=node_ficct.id, name="INF", code="INF", path="/UNIV/FICCT/INF/", depth=3)
    node_adm = UnitNode(group_id=group.id, level_id=lvl_car.id, parent_id=node_fceh.id, name="ADM", code="ADM", path="/UNIV/FCEH/ADM/", depth=3)
    test_db.add_all([node_inf, node_adm])
    await test_db.flush()

    # 3. Votantes en padrón
    voter1 = Voter(
        organization_id=org.id,
        election_id=election.id,
        group_id=group.id,
        node_id=node_inf.id,
        document_id="CI-7001",
        full_name="Votante Uno Inf",
        status=VoterStatus.IMPORTED,
    )
    voter2 = Voter(
        organization_id=org.id,
        election_id=election.id,
        group_id=group.id,
        node_id=node_inf.id,
        document_id="CI-7002",
        full_name="Votante Dos Inf",
        status=VoterStatus.IMPORTED,
    )
    voter3 = Voter(
        organization_id=org.id,
        election_id=election.id,
        group_id=group.id,
        node_id=node_inf.id,
        document_id="CI-7003",
        full_name="Votante Tres Inf",
        status=VoterStatus.IMPORTED,
    )
    voter_blocked = Voter(
        organization_id=org.id,
        election_id=election.id,
        group_id=group.id,
        node_id=node_inf.id,
        document_id="CI-7004-BLOCKED",
        full_name="Votante Bloqueado",
        status=VoterStatus.BLOCKED,
    )
    voter_adm = Voter(
        organization_id=org.id,
        election_id=election.id,
        group_id=group.id,
        node_id=node_adm.id,
        document_id="CI-7005-ADM",
        full_name="Votante Administracion",
        status=VoterStatus.IMPORTED,
    )
    test_db.add_all([voter1, voter2, voter3, voter_blocked, voter_adm])
    await test_db.commit()

    headers = {"Authorization": f"Bearer {admin_token}"}

    # 4. Crear enlace de registro segmentado a FICCT con max_uses = 2
    res_link = await client.post(
        f"/elections/{election.id}/registration-links",
        headers=headers,
        json={
            "group_id": str(group.id),
            "node_id": str(node_ficct.id),
            "label": "Enlace Facultad FICCT",
            "expires_at": t_reg_close.isoformat(),
            "max_uses": 2,
        },
    )
    assert res_link.status_code == 201
    link_data = res_link.json()
    raw_token = link_data["raw_token"]
    assert raw_token is not None

    # 5. Consultar información pública del enlace
    res_pub = await client.get(f"/register/{raw_token}")
    assert res_pub.status_code == 200
    pub_info = res_pub.json()
    assert pub_info["is_valid"] is True
    assert pub_info["group_name"] == "ESTUDIANTES"
    assert pub_info["node_name"] == "FICCT"

    # 6. Intentar activar votante BLOCKED -> Debe rechazar con 403
    res_act_blocked = await client.post(
        f"/register/{raw_token}",
        json={"document_id": "CI-7004-BLOCKED"},
    )
    assert res_act_blocked.status_code == 403
    assert "bloqueado" in res_act_blocked.json()["detail"].lower()

    # 7. Intentar activar votante fuera del subárbol de FICCT (voter_adm está en FCEH) -> Debe rechazar con 403
    res_act_adm = await client.post(
        f"/register/{raw_token}",
        json={"document_id": "CI-7005-ADM"},
    )
    assert res_act_adm.status_code == 403
    assert "no pertenece a la unidad" in res_act_adm.json()["detail"].lower()

    # 8. Activar Votante 1 (Uso 1/2)
    res_act1 = await client.post(
        f"/register/{raw_token}",
        json={"document_id": "CI-7001", "email": "voter1@ficct.edu.bo"},
    )
    assert res_act1.status_code == 200
    assert res_act1.json()["success"] is True
    assert res_act1.json()["status"] == "ACTIVE"

    # Re-activación idempotente
    res_act1_dup = await client.post(
        f"/register/{raw_token}",
        json={"document_id": "CI-7001"},
    )
    assert res_act1_dup.status_code == 200
    assert "previamente activado" in res_act1_dup.json()["message"].lower()

    # 9. Activar Votante 2 (Uso 2/2 -> Se agota el enlace)
    res_act2 = await client.post(
        f"/register/{raw_token}",
        json={"document_id": "CI-7002"},
    )
    assert res_act2.status_code == 200
    assert res_act2.json()["status"] == "ACTIVE"

    # 10. Intentar 3er uso con Votante 3 -> Debe fallar por límite de usos (403)
    res_act3 = await client.post(
        f"/register/{raw_token}",
        json={"document_id": "CI-7003"},
    )
    assert res_act3.status_code == 403
    assert "límite máximo de usos" in res_act3.json()["detail"].lower()

    # 11. Invariante #5: Congelar padrón y calcular roll_hash
    res_freeze = await client.post(
        f"/elections/{election.id}/registration/close-now",
        headers=headers,
    )
    assert res_freeze.status_code == 200
    freeze_data = res_freeze.json()
    assert freeze_data["roll_hash"] is not None
    assert len(freeze_data["roll_hash"]) == 64
    assert freeze_data["active_voters_count"] == 2  # voter1 y voter2

    await test_db.refresh(election)
    assert election.status == ElectionStatus.REGISTRATION_CLOSED
    assert election.roll_hash == freeze_data["roll_hash"]

    # 12. Intentar usar un enlace con el padrón cerrado -> Debe rechazar con 403
    res_post_freeze = await client.post(
        f"/register/{raw_token}",
        json={"document_id": "CI-7003"},
    )
    assert res_post_freeze.status_code == 403
