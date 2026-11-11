"""
Pruebas de Invariante: Padrón Electoral, Carga Masiva, Detección de Duplicados (IA-L2a) y Scope de ADMIN_SEGMENT (S1-07, Invariante #5)
"""
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash
from app.core.time import FakeTimeProvider
from app.db.models.election import Election, ElectionStatus
from app.db.models.user import AdminAssignment, User, UserRole, UserStatus


@pytest.mark.asyncio
async def test_voter_roll_phase_guard_and_node_depth_validation(
    client: AsyncClient, test_db: AsyncSession, org1_setup, fake_time: FakeTimeProvider
):
    org, admin, token = org1_setup
    now = fake_time._current_time
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Crear elección en DRAFT
    elect_res = await client.post(
        "/elections",
        headers=headers,
        json={
            "name": "Elección Padrón y Duplicados",
            "timezone": "America/La_Paz",
            "registration_opens_at": (now + timedelta(hours=1)).isoformat(),
            "registration_closes_at": (now + timedelta(hours=5)).isoformat(),
            "voting_opens_at": (now + timedelta(hours=6)).isoformat(),
            "voting_closes_at": (now + timedelta(hours=12)).isoformat(),
            "k_anonymity": 5,
        },
    )
    election_id = elect_res.json()["id"]

    # 2. Configurar Grupo ESTUDIANTES con 3 niveles: Universidad -> Facultad -> Carrera
    group = (await client.post(
        f"/elections/{election_id}/groups",
        headers=headers,
        json={"name": "ESTUDIANTES", "code": "EST"},
    )).json()
    group_id = group["id"]

    lvl1 = (await client.post(f"/groups/{group_id}/levels", headers=headers, json={"name": "Universidad"})).json()
    lvl2 = (await client.post(f"/groups/{group_id}/levels", headers=headers, json={"name": "Facultad"})).json()
    lvl3 = (await client.post(f"/groups/{group_id}/levels", headers=headers, json={"name": "Carrera"})).json()

    univ_node = (await client.post(
        f"/groups/{group_id}/nodes",
        headers=headers,
        json={"level_id": lvl1["id"], "parent_id": None, "name": "Universidad", "code": "UNIV"},
    )).json()

    fac_tec = (await client.post(
        f"/groups/{group_id}/nodes",
        headers=headers,
        json={"level_id": lvl2["id"], "parent_id": univ_node["id"], "name": "Facultad Tecnología", "code": "FICCT"},
    )).json()

    carr_inf = (await client.post(
        f"/groups/{group_id}/nodes",
        headers=headers,
        json={"level_id": lvl3["id"], "parent_id": fac_tec["id"], "name": "Ingeniería Informática", "code": "INF"},
    )).json()

    # Cargo de nivel 3 (Encargado de Carrera)
    contest = (await client.post(
        f"/groups/{group_id}/contests",
        headers=headers,
        json={"name": "Encargado de Carrera", "scope_level_id": lvl3["id"]},
    )).json()

    constituencies = (await client.get(f"/contests/{contest['id']}/constituencies", headers=headers)).json()
    await client.post(
        f"/constituencies/{constituencies[0]['id']}/candidates",
        headers=headers,
        json={"name": "Univ. Juan Perez", "party_or_front": "FRENTE INF"},
    )

    # =========================================================================
    # Invariante #5: Cargar votantes en DRAFT debe fallar con 409 Conflict
    # =========================================================================
    voter_payload = {
        "group_id": group_id,
        "node_id": carr_inf["id"],
        "document_id": "CI-7001",
        "full_name": "Juan Carlos Votante",
    }
    err_draft = await client.post(f"/elections/{election_id}/voters", headers=headers, json=voter_payload)
    assert err_draft.status_code == 409
    assert "REGISTRATION_OPEN" in err_draft.json()["detail"]

    # Publicar elección -> pasa a SCHEDULED
    pub_res = await client.post(f"/elections/{election_id}/publish", headers=headers)
    assert pub_res.status_code == 200

    # Cargar votantes en SCHEDULED -> Sigue fallando con 409 Conflict
    err_sched = await client.post(f"/elections/{election_id}/voters", headers=headers, json=voter_payload)
    assert err_sched.status_code == 409

    # Abrir registro ("Abrir registro ahora" o transición temporal a REGISTRATION_OPEN)
    open_res = await client.post(f"/elections/{election_id}/registration/open-now", headers=headers)
    assert open_res.status_code == 200
    assert open_res.json()["status"] == "REGISTRATION_OPEN"

    # =========================================================================
    # Validación de Profundidad de Nodo del Votante
    # Intentar asignar al estudiante solo al nivel 2 (Facultad) cuando hay un cargo de nivel 3 (Carrera)
    # =========================================================================
    invalid_depth_payload = {
        "group_id": group_id,
        "node_id": fac_tec["id"],  # Nivel 2
        "document_id": "CI-7002",
        "full_name": "Estudiante Sin Carrera",
    }
    err_depth = await client.post(f"/elections/{election_id}/voters", headers=headers, json=invalid_depth_payload)
    assert err_depth.status_code == 422
    assert "profundidad suficiente" in err_depth.json()["detail"]

    # Asignación válida al nivel 3 (Carrera)
    valid_res = await client.post(f"/elections/{election_id}/voters", headers=headers, json=voter_payload)
    assert valid_res.status_code == 201
    created_voter = valid_res.json()
    assert created_voter["document_id"] == "CI-7001"
    assert created_voter["status"] == "IMPORTED"


@pytest.mark.asyncio
async def test_duplicate_detection_and_segment_admin_scope(
    client: AsyncClient, test_db: AsyncSession, org1_setup, fake_time: FakeTimeProvider
):
    org, admin, token = org1_setup
    now = fake_time._current_time
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Crear elección y abrir registro inmediatamente
    elect = (await client.post(
        "/elections",
        headers=headers,
        json={
            "name": "Elección Detección Duplicados",
            "timezone": "America/La_Paz",
            "registration_opens_at": (now + timedelta(hours=1)).isoformat(),
            "registration_closes_at": (now + timedelta(hours=5)).isoformat(),
            "voting_opens_at": (now + timedelta(hours=6)).isoformat(),
            "voting_closes_at": (now + timedelta(hours=12)).isoformat(),
            "k_anonymity": 5,
        },
    )).json()
    election_id = elect["id"]

    group = (await client.post(
        f"/elections/{election_id}/groups",
        headers=headers,
        json={"name": "ESTUDIANTES", "code": "EST"},
    )).json()
    group_id = group["id"]

    lvl1 = (await client.post(f"/groups/{group_id}/levels", headers=headers, json={"name": "Facultad"})).json()
    lvl2 = (await client.post(f"/groups/{group_id}/levels", headers=headers, json={"name": "Carrera"})).json()

    fac_tec = (await client.post(
        f"/groups/{group_id}/nodes",
        headers=headers,
        json={"level_id": lvl1["id"], "parent_id": None, "name": "Tecnología", "code": "TEC"},
    )).json()
    fac_eco = (await client.post(
        f"/groups/{group_id}/nodes",
        headers=headers,
        json={"level_id": lvl1["id"], "parent_id": None, "name": "Económicas", "code": "ECO"},
    )).json()

    carr_inf = (await client.post(
        f"/groups/{group_id}/nodes",
        headers=headers,
        json={"level_id": lvl2["id"], "parent_id": fac_tec["id"], "name": "Informática", "code": "INF"},
    )).json()
    carr_eco = (await client.post(
        f"/groups/{group_id}/nodes",
        headers=headers,
        json={"level_id": lvl2["id"], "parent_id": fac_eco["id"], "name": "Economía", "code": "ECN"},
    )).json()

    # Cargo
    cnt = (await client.post(
        f"/groups/{group_id}/contests",
        headers=headers,
        json={"name": "Delegado Estudiantil", "scope_level_id": lvl2["id"]},
    )).json()

    for c in (await client.get(f"/contests/{cnt['id']}/constituencies", headers=headers)).json():
        await client.post(f"/constituencies/{c['id']}/candidates", headers=headers, json={"name": f"Cand {c['node_code']}"})

    await client.post(f"/elections/{election_id}/publish", headers=headers)
    await client.post(f"/elections/{election_id}/registration/open-now", headers=headers)

    # =========================================================================
    # 2. Importación CSV con Votantes y Posible Duplicado (IA-L2a)
    # Votante 1: "José Rodríguez" (CI: 10001) en INF
    # Votante 2: "Jose Rodriguez S." (CI: 10002) en INF -> Alta similitud trigram
    # Votante 3: "Mariana Rojas" (CI: 20001) en ECN
    # =========================================================================
    csv_voters = (
        "document_id,full_name,email,phone,group_code,node_code,attributes_json\n"
        "10001,José Rodríguez,jose1@uagrm.bo,70001,EST,INF,{}\n"
        "10002,Jose Rodriguez S.,jose2@uagrm.bo,70002,EST,INF,{}\n"
        "20001,Mariana Rojas,mariana@uagrm.bo,70003,EST,ECN,{}\n"
    )
    import_res = await client.post(
        f"/elections/{election_id}/voters/import",
        headers=headers,
        files={"file": ("padron.csv", csv_voters.encode("utf-8"), "text/csv")},
    )
    assert import_res.status_code == 201
    batch = import_res.json()
    assert batch["total_rows"] == 3
    assert batch["valid_rows"] == 3
    assert batch["duplicate_warnings"] >= 1

    # Consultar bandeja de duplicados
    dups_res = await client.get(f"/elections/{election_id}/voters/duplicates", headers=headers)
    assert dups_res.status_code == 200
    dups = dups_res.json()
    assert len(dups) >= 1
    issue = dups[0]
    assert issue["issue_type"] == "POSSIBLE_DUPLICATE"
    assert issue["similarity_score"] >= 0.45
    assert issue["resolution"] == "PENDING"

    # Resolver duplicado: Dictamen Humano (CONFIRM_DISTINCT)
    resolve_res = await client.post(
        f"/elections/{election_id}/voters/duplicates/{issue['id']}/resolve",
        headers=headers,
        json={"action": "CONFIRM_DISTINCT", "reason": "Verificado con cédula física y huella digital"},
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["resolution"] == "CONFIRMED_DISTINCT"

    # =========================================================================
    # 3. Restricción de Alcance para ADMIN_SEGMENT (Delegado de Tecnología)
    # =========================================================================
    seg_user = User(
        organization_id=org.id,
        email="delegado.tec@granestudio.edu.bo",
        full_name="Delegado Tecnología",
        password_hash=get_password_hash("DelegadoPass2026!"),
        role=UserRole.ADMIN_SEGMENT,
        status=UserStatus.ACTIVE,
    )
    test_db.add(seg_user)
    await test_db.flush()

    import uuid as uuid_pkg
    assignment = AdminAssignment(
        organization_id=org.id,
        user_id=seg_user.id,
        election_id=uuid_pkg.UUID(election_id),
        group_id=uuid_pkg.UUID(group_id),
        node_id=uuid_pkg.UUID(fac_tec["id"]),
        permission="READ",
    )
    test_db.add(assignment)
    await test_db.commit()

    seg_token = create_access_token(
        subject=str(seg_user.id),
        role=seg_user.role.value,
        organization_id=str(org.id),
    )
    seg_headers = {"Authorization": f"Bearer {seg_token}"}

    # El ADMIN_SEGMENT consulta el padrón: Solo debe ver a los votantes de Tecnología (José y Jose), NO a Mariana (Economía)
    seg_voters_res = await client.get(f"/elections/{election_id}/voters", headers=seg_headers)
    assert seg_voters_res.status_code == 200
    seg_voters = seg_voters_res.json()
    assert len(seg_voters) == 2
    seg_docs = {v["document_id"] for v in seg_voters}
    assert seg_docs == {"10001", "10002"}
    assert "20001" not in seg_docs

    # Resumen de registro del delegado: total 2
    seg_summary_res = await client.get(f"/elections/{election_id}/registration/summary", headers=seg_headers)
    assert seg_summary_res.status_code == 200
    assert seg_summary_res.json()["total_voters"] == 2

    # Intentos de mutación por ADMIN_SEGMENT deben ser rechazados con 403 Forbidden (Invariante #2)
    err_post_voter = await client.post(
        f"/elections/{election_id}/voters",
        headers=seg_headers,
        json={"group_id": group_id, "node_id": carr_inf["id"], "document_id": "99999", "full_name": "No Permitido"},
    )
    assert err_post_voter.status_code == 403

    err_del_voter = await client.delete(
        f"/elections/{election_id}/voters/{seg_voters[0]['id']}",
        headers=seg_headers,
    )
    assert err_del_voter.status_code == 403
