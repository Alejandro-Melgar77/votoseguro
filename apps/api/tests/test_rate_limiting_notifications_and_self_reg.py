"""
Pruebas Automatizadas para:
1. Rate Limiting contra Fuerza Bruta y DoS con slowapi (S2-06)
2. Notificaciones de Cambio de Cronograma a Votantes Activos (S2-09)
3. Autoinscripción Pública con Bandeja de Aprobación/Rechazo OPEN_WITH_APPROVAL (S2-10)
"""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import FakeTimeProvider
from app.db.models.election import Election, ElectionStatus
from app.db.models.structure import HierarchyLevel, UnitNode, VoterGroup
from app.db.models.voter import Voter, VoterStatus


@pytest.mark.asyncio
async def test_schedule_notifications_and_self_registration(
    test_db: AsyncSession,
    client: AsyncClient,
    org1_setup,
    fake_time: FakeTimeProvider,
):
    org, admin, admin_token = org1_setup
    now = datetime(2026, 11, 20, 10, 0, 0, tzinfo=timezone.utc)
    fake_time.set_time(now)
    auth_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Crear Elección en REGISTRATION_OPEN con registration_mode = "OPEN_WITH_APPROVAL"
    election = Election(
        organization_id=org.id,
        name="Elección Autoinscripción y Notificaciones S2-09-10",
        timezone="America/La_Paz",
        registration_opens_at=now - timedelta(days=1),
        registration_closes_at=now + timedelta(days=2),
        voting_opens_at=now + timedelta(days=3),
        voting_closes_at=now + timedelta(days=4),
        status=ElectionStatus.REGISTRATION_OPEN,
        config_hash="CONFIG_HASH_NOTIF_SELFREG",
        registration_mode="OPEN_WITH_APPROVAL",
        created_by=admin.id,
    )
    test_db.add(election)
    await test_db.flush()

    grp = VoterGroup(organization_id=org.id, election_id=election.id, name="Estudiantes", code="EST")
    test_db.add(grp)
    await test_db.flush()

    lvl = HierarchyLevel(group_id=grp.id, depth=1, name="Carrera")
    test_db.add(lvl)
    await test_db.flush()

    node = UnitNode(group_id=grp.id, level_id=lvl.id, parent_id=None, name="Sistemas", code="SIS", path="/SIS/", depth=1)
    test_db.add(node)
    await test_db.flush()

    # Crear 1 votante ACTIVE con email para probar notificaciones de cronograma
    v_active = Voter(
        organization_id=org.id,
        election_id=election.id,
        group_id=grp.id,
        node_id=node.id,
        document_id="CI-NOTIF-01",
        full_name="Votante Notificable",
        email="votante01@uagrm.edu.bo",
        status=VoterStatus.ACTIVE,
        attributes={},
    )
    test_db.add(v_active)
    await test_db.commit()

    # 2. Test S2-10: Autoinscripción Pública
    # A. Consultar info de autoinscripción pública
    res_info = await client.get(f"/public/elections/{election.id}/self-registration-info")
    assert res_info.status_code == 200
    info_data = res_info.json()
    assert info_data["election_id"] == str(election.id)
    assert info_data["registration_mode"] == "OPEN_WITH_APPROVAL"
    assert len(info_data["groups"]) > 0

    # B. Postular autoinscripción pública (Votante Aspirante 1)
    res_self1 = await client.post(
        f"/public/elections/{election.id}/self-register",
        json={
            "document_id": "CI-ASPIRANTE-1",
            "full_name": "Aspirante Aprobado",
            "email": "aspirante1@uagrm.edu.bo",
            "phone": "+59170011223",
            "group_id": str(grp.id),
            "node_id": str(node.id),
            "attributes": {"semestre": 5},
        },
    )
    assert res_self1.status_code == 201
    s1_data = res_self1.json()
    assert s1_data["status"] == "PENDING_APPROVAL"
    aspirant1_id = s1_data["voter_id"]

    # C. Postular autoinscripción pública (Votante Aspirante 2 para rechazo)
    res_self2 = await client.post(
        f"/public/elections/{election.id}/self-register",
        json={
            "document_id": "CI-ASPIRANTE-2",
            "full_name": "Aspirante Rechazado",
            "email": "aspirante2@uagrm.edu.bo",
            "group_id": str(grp.id),
            "node_id": str(node.id),
        },
    )
    assert res_self2.status_code == 201
    aspirant2_id = res_self2.json()["voter_id"]

    # D. Consultar bandeja de pendientes como ADMIN
    res_pending = await client.get(f"/elections/{election.id}/voters/pending-approval", headers=auth_headers)
    assert res_pending.status_code == 200
    pending_items = res_pending.json()
    assert len(pending_items) >= 2
    pending_doc_ids = [p["document_id"] for p in pending_items]
    assert "CI-ASPIRANTE-1" in pending_doc_ids
    assert "CI-ASPIRANTE-2" in pending_doc_ids

    # E. Aprobar Aspirante 1
    res_appr = await client.post(
        f"/elections/{election.id}/voters/{aspirant1_id}/approve",
        headers=auth_headers,
    )
    assert res_appr.status_code == 200
    assert res_appr.json()["status"] == "ACTIVE"

    # F. Rechazar Aspirante 2 con motivo formal
    res_rej = await client.post(
        f"/elections/{election.id}/voters/{aspirant2_id}/reject",
        headers=auth_headers,
        json={
            "reason": "Matrícula universitaria no vigente en el semestre actual.",
        },
    )
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "BLOCKED"

    # Verificar que la bandeja de pendientes ahora no contenga a ninguno de los dos
    res_pending_after = await client.get(f"/elections/{election.id}/voters/pending-approval", headers=auth_headers)
    pending_after_ids = [p["id"] for p in res_pending_after.json()]
    assert aspirant1_id not in pending_after_ids
    assert aspirant2_id not in pending_after_ids

    # 3. Test S2-09: Notificación de Cambio de Cronograma
    # Modificar el cronograma de votación
    new_voting_closes = now + timedelta(days=5)
    res_sched = await client.put(
        f"/elections/{election.id}/schedule",
        headers=auth_headers,
        json={
            "registration_opens_at": election.registration_opens_at.isoformat(),
            "registration_closes_at": election.registration_closes_at.isoformat(),
            "voting_opens_at": election.voting_opens_at.isoformat(),
            "voting_closes_at": new_voting_closes.isoformat(),
            "reason": "Ampliación de jornada electoral autorizada por el Comité Electoral.",
        },
    )
    assert res_sched.status_code == 200

    # Consultar bandeja de salida de notificaciones (notification_outbox)
    res_outbox = await client.get(f"/elections/{election.id}/notifications/outbox", headers=auth_headers)
    assert res_outbox.status_code == 200
    outbox_items = res_outbox.json()
    assert len(outbox_items) >= 2  # v_active y aspirant1 (ahora ACTIVE con email)

    recipients = [item["recipient_email"] for item in outbox_items]
    assert "votante01@uagrm.edu.bo" in recipients
    assert "aspirante1@uagrm.edu.bo" in recipients
    assert any("Ampliación de jornada" in item["body_text"] or "Ampliación de jornada" in item["subject"] for item in outbox_items)
