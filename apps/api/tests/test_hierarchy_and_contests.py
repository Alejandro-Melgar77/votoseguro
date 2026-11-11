"""
Pruebas de Invariante: Jerarquía Electoral, Árbol de Nodos y Autogeneración de Circunscripciones (S1-03, S1-04)
"""
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import FakeTimeProvider
from app.db.models.election import Election, ElectionStatus


@pytest.mark.asyncio
async def test_hierarchy_levels_nodes_and_path(client: AsyncClient, test_db: AsyncSession, org1_setup, fake_time: FakeTimeProvider):
    org, admin, token = org1_setup
    now = fake_time._current_time
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Crear elección en DRAFT
    elect_res = await client.post(
        "/elections",
        headers=headers,
        json={
            "name": "Elección Universitaria 2026",
            "timezone": "America/La_Paz",
            "registration_opens_at": (now + timedelta(days=1)).isoformat(),
            "registration_closes_at": (now + timedelta(days=2)).isoformat(),
            "voting_opens_at": (now + timedelta(days=3)).isoformat(),
            "voting_closes_at": (now + timedelta(days=4)).isoformat(),
            "k_anonymity": 5,
        },
    )
    assert elect_res.status_code == 201, elect_res.text
    election_id = elect_res.json()["id"]

    # 2. Crear Grupo de Votantes ESTUDIANTES
    group_res = await client.post(
        f"/elections/{election_id}/groups",
        headers=headers,
        json={"name": "ESTUDIANTES", "code": "EST", "description": "Estudiantes regulares"},
    )
    assert group_res.status_code == 201
    group_id = group_res.json()["id"]

    # 3. Crear 3 Niveles Jerárquicos: Universidad (1) -> Facultad (2) -> Carrera (3)
    lvl1_res = await client.post(f"/groups/{group_id}/levels", headers=headers, json={"name": "Universidad"})
    assert lvl1_res.status_code == 201
    lvl1_id = lvl1_res.json()["id"]
    assert lvl1_res.json()["depth"] == 1

    lvl2_res = await client.post(f"/groups/{group_id}/levels", headers=headers, json={"name": "Facultad"})
    assert lvl2_res.status_code == 201
    lvl2_id = lvl2_res.json()["id"]
    assert lvl2_res.json()["depth"] == 2

    lvl3_res = await client.post(f"/groups/{group_id}/levels", headers=headers, json={"name": "Carrera"})
    assert lvl3_res.status_code == 201
    lvl3_id = lvl3_res.json()["id"]
    assert lvl3_res.json()["depth"] == 3

    # 4. Crear Nodo Raíz (Universidad)
    node1_res = await client.post(
        f"/groups/{group_id}/nodes",
        headers=headers,
        json={"level_id": lvl1_id, "parent_id": None, "name": "Universidad UAGRM", "code": "UAGRM"},
    )
    assert node1_res.status_code == 201
    node1 = node1_res.json()
    assert node1["path"] == "/UAGRM/"
    node1_id = node1["id"]

    # 5. Intentar colgar un nodo de nivel 3 (Carrera) directamente del nodo raíz (nivel 1) -> debe fallar con 422
    invalid_hang = await client.post(
        f"/groups/{group_id}/nodes",
        headers=headers,
        json={"level_id": lvl3_id, "parent_id": node1_id, "name": "Ingeniería Informática", "code": "INF"},
    )
    assert invalid_hang.status_code == 422
    assert "inmediatamente superior" in invalid_hang.json()["detail"]

    # 6. Crear Nodos de Nivel 2 (Facultades)
    fac1_res = await client.post(
        f"/groups/{group_id}/nodes",
        headers=headers,
        json={"level_id": lvl2_id, "parent_id": node1_id, "name": "Facultad de Tecnología", "code": "FICCT"},
    )
    assert fac1_res.status_code == 201
    fac1 = fac1_res.json()
    assert fac1["path"] == "/UAGRM/FICCT/"
    fac1_id = fac1["id"]

    fac2_res = await client.post(
        f"/groups/{group_id}/nodes",
        headers=headers,
        json={"level_id": lvl2_id, "parent_id": node1_id, "name": "Facultad de Económicas", "code": "FCE"},
    )
    assert fac2_res.status_code == 201
    fac2_id = fac2_res.json()["id"]

    fac3_res = await client.post(
        f"/groups/{group_id}/nodes",
        headers=headers,
        json={"level_id": lvl2_id, "parent_id": node1_id, "name": "Facultad de Humanidades", "code": "FH"},
    )
    assert fac3_res.status_code == 201

    # 7. Crear Nodo de Nivel 3 (Carrera) bajo FICCT
    carr1_res = await client.post(
        f"/groups/{group_id}/nodes",
        headers=headers,
        json={"level_id": lvl3_id, "parent_id": fac1_id, "name": "Ingeniería Informática", "code": "INF"},
    )
    assert carr1_res.status_code == 201
    assert carr1_res.json()["path"] == "/UAGRM/FICCT/INF/"

    # 8. Importación CSV de nodos (orden topológico resiliente)
    csv_payload = (
        "code,name,level_depth,parent_code\n"
        "SIS,Ingeniería de Sistemas,3,FICCT\n"
        "RED,Ingeniería en Redes,3,FICCT\n"
        "FAR,Facultad de Farmacia,2,UAGRM\n"
    )
    import_res = await client.post(
        f"/groups/{group_id}/nodes/import",
        headers=headers,
        files={"file": ("nodos.csv", csv_payload.encode("utf-8"), "text/csv")},
    )
    assert import_res.status_code == 200
    import_data = import_res.json()
    assert import_data["created_nodes"] == 3
    assert len(import_data["errors"]) == 0

    # 9. Consultar Árbol Jerárquico
    tree_res = await client.get(f"/groups/{group_id}/nodes/tree", headers=headers)
    assert tree_res.status_code == 200
    tree = tree_res.json()
    assert len(tree) == 1  # 1 raíz: UAGRM
    assert tree[0]["code"] == "UAGRM"
    # UAGRM tiene 4 facultades: FICCT, FCE, FH, FAR
    assert len(tree[0]["children"]) == 4


@pytest.mark.asyncio
async def test_contest_automatic_constituencies_and_dynamic_sync(
    client: AsyncClient, test_db: AsyncSession, org1_setup, fake_time: FakeTimeProvider
):
    org, admin, token = org1_setup
    now = fake_time._current_time
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Crear elección y grupo
    elect_res = await client.post(
        "/elections",
        headers=headers,
        json={
            "name": "Elección con Circunscripciones Automáticas",
            "timezone": "America/La_Paz",
            "registration_opens_at": (now + timedelta(days=1)).isoformat(),
            "registration_closes_at": (now + timedelta(days=2)).isoformat(),
            "voting_opens_at": (now + timedelta(days=3)).isoformat(),
            "voting_closes_at": (now + timedelta(days=4)).isoformat(),
            "k_anonymity": 5,
        },
    )
    election_id = elect_res.json()["id"]

    group_res = await client.post(
        f"/elections/{election_id}/groups",
        headers=headers,
        json={"name": "DOCENTES", "code": "DOC"},
    )
    group_id = group_res.json()["id"]

    # 2. Niveles: Universidad (1) y Facultad (2)
    lvl1 = (await client.post(f"/groups/{group_id}/levels", headers=headers, json={"name": "Universidad"})).json()
    lvl2 = (await client.post(f"/groups/{group_id}/levels", headers=headers, json={"name": "Facultad"})).json()

    # 3. Crear Universidad raíz y 3 Facultades
    u_node = (await client.post(
        f"/groups/{group_id}/nodes",
        headers=headers,
        json={"level_id": lvl1["id"], "parent_id": None, "name": "Universidad", "code": "UNIV"},
    )).json()

    for code, name in [("TEC", "Facultad Tecnología"), ("ECO", "Facultad Económicas"), ("HUM", "Facultad Humanidades")]:
        await client.post(
            f"/groups/{group_id}/nodes",
            headers=headers,
            json={"level_id": lvl2["id"], "parent_id": u_node["id"], "name": name, "code": code},
        )

    # 4. Crear Cargo 'Decano' con alcance Nivel 2 ('Facultad')
    contest_res = await client.post(
        f"/groups/{group_id}/contests",
        headers=headers,
        json={
            "name": "Decano",
            "description": "Elección de Decano de Facultad",
            "scope_level_id": lvl2["id"],
            "allow_blank": True,
            "allow_null": True,
            "display_order": 1,
        },
    )
    assert contest_res.status_code == 201
    contest = contest_res.json()
    assert contest["name"] == "Decano"

    # Verificar que se hayan generado exactamente 3 circunscripciones automáticas
    const_res = await client.get(f"/contests/{contest['id']}/constituencies", headers=headers)
    assert const_res.status_code == 200
    constituencies = const_res.json()
    assert len(constituencies) == 3
    node_codes = {c["node_code"] for c in constituencies}
    assert node_codes == {"TEC", "ECO", "HUM"}

    # 5. Sincronización Dinámica: Añadir una 4ta Facultad mientras sigue en DRAFT
    await client.post(
        f"/groups/{group_id}/nodes",
        headers=headers,
        json={"level_id": lvl2["id"], "parent_id": u_node["id"], "name": "Facultad Salud", "code": "SALUD"},
    )

    # Verificar que el cargo Decano ahora tiene automáticamente 4 circunscripciones
    const_res2 = await client.get(f"/contests/{contest['id']}/constituencies", headers=headers)
    assert const_res2.status_code == 200
    constituencies2 = const_res2.json()
    assert len(constituencies2) == 4
    assert any(c["node_code"] == "SALUD" for c in constituencies2)
