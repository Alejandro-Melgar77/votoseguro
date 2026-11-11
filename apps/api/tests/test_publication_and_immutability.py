"""
Pruebas de Invariante: Publicación de la Elección, ConfigHash Criptográfico e Inmutabilidad Estructural (S1-05, S1-06, Invariante #3)
"""
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import FakeTimeProvider


@pytest.mark.asyncio
async def test_publication_candidate_coverage_validation_and_config_hash(
    client: AsyncClient, test_db: AsyncSession, org1_setup, fake_time: FakeTimeProvider
):
    org, admin, token = org1_setup
    now = fake_time._current_time
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Crear elección en DRAFT con cronograma válido
    elect_res = await client.post(
        "/elections",
        headers=headers,
        json={
            "name": "Elección con Ceremonia de Publicación",
            "timezone": "America/La_Paz",
            "registration_opens_at": (now + timedelta(days=2)).isoformat(),
            "registration_closes_at": (now + timedelta(days=4)).isoformat(),
            "voting_opens_at": (now + timedelta(days=5)).isoformat(),
            "voting_closes_at": (now + timedelta(days=6)).isoformat(),
            "k_anonymity": 5,
        },
    )
    assert elect_res.status_code == 201
    election_id = elect_res.json()["id"]

    # 2. Configurar Grupo, Niveles y Nodos (Universidad y 2 Facultades)
    group = (await client.post(
        f"/elections/{election_id}/groups",
        headers=headers,
        json={"name": "ESTUDIANTES", "code": "EST"},
    )).json()
    group_id = group["id"]

    lvl1 = (await client.post(f"/groups/{group_id}/levels", headers=headers, json={"name": "Universidad"})).json()
    lvl2 = (await client.post(f"/groups/{group_id}/levels", headers=headers, json={"name": "Facultad"})).json()

    univ_node = (await client.post(
        f"/groups/{group_id}/nodes",
        headers=headers,
        json={"level_id": lvl1["id"], "parent_id": None, "name": "Universidad", "code": "UNIV"},
    )).json()

    fac1_node = (await client.post(
        f"/groups/{group_id}/nodes",
        headers=headers,
        json={"level_id": lvl2["id"], "parent_id": univ_node["id"], "name": "Facultad Tecnología", "code": "TEC"},
    )).json()

    fac2_node = (await client.post(
        f"/groups/{group_id}/nodes",
        headers=headers,
        json={"level_id": lvl2["id"], "parent_id": univ_node["id"], "name": "Facultad Económicas", "code": "ECO"},
    )).json()

    # 3. Crear Cargo Decano (genera 2 circunscripciones: TEC y ECO)
    contest = (await client.post(
        f"/groups/{group_id}/contests",
        headers=headers,
        json={
            "name": "Decano",
            "scope_level_id": lvl2["id"],
            "allow_blank": True,
            "allow_null": True,
            "display_order": 1,
        },
    )).json()
    contest_id = contest["id"]

    constituencies = (await client.get(f"/contests/{contest_id}/constituencies", headers=headers)).json()
    assert len(constituencies) == 2
    const_tec_id = [c["id"] for c in constituencies if c["node_code"] == "TEC"][0]
    const_eco_id = [c["id"] for c in constituencies if c["node_code"] == "ECO"][0]

    # 4. Intentar publicar sin candidatos -> Debe fallar con 422 (Regla 5 de consistencia)
    pub_fail_1 = await client.post(f"/elections/{election_id}/publish", headers=headers)
    assert pub_fail_1.status_code == 422
    assert "no tiene candidatos registrados" in pub_fail_1.json()["detail"]

    # 5. Registrar candidato solo en TEC
    cand_tec = (await client.post(
        f"/constituencies/{const_tec_id}/candidates",
        headers=headers,
        json={"name": "Ing. Carlos Perez", "party_or_front": "FRENTE TEC 1", "ballot_order": 1},
    )).json()
    assert cand_tec["ballot_order"] == 1

    # Intentar publicar teniendo aún ECO sin candidatos -> Sigue fallando con 422
    pub_fail_2 = await client.post(f"/elections/{election_id}/publish", headers=headers)
    assert pub_fail_2.status_code == 422
    assert "Facultad Económicas" in pub_fail_2.json()["detail"]

    # 6. Registrar candidato en ECO
    await client.post(
        f"/constituencies/{const_eco_id}/candidates",
        headers=headers,
        json={"name": "Lic. Mario Gomez", "party_or_front": "FRENTE ECO 1", "ballot_order": 1},
    )

    # 7. Publicar Elección -> Ahora debe ser exitosa
    pub_success = await client.post(f"/elections/{election_id}/publish", headers=headers)
    assert pub_success.status_code == 200, pub_success.text
    published_election = pub_success.json()

    assert published_election["status"] == "SCHEDULED"
    assert published_election["published_at"] is not None
    config_hash = published_election["config_hash"]
    assert config_hash is not None
    assert len(config_hash) == 64
    assert all(c in "0123456789abcdef" for c in config_hash)

    # 8. Reintentar publicar cuando ya está SCHEDULED -> Debe responder 409 Conflict (Regla 1)
    pub_again = await client.post(f"/elections/{election_id}/publish", headers=headers)
    assert pub_again.status_code == 409
    assert "borrador" in pub_again.json()["detail"]

    # =========================================================================
    # 9. Invariante #3: Congelamiento e Inmutabilidad Estructural Post-Publicación
    # =========================================================================
    # Intento de agregar un nuevo grupo
    err_grp = await client.post(
        f"/elections/{election_id}/groups",
        headers=headers,
        json={"name": "NUEVO GRUPO", "code": "NEW"},
    )
    assert err_grp.status_code == 409
    assert "congelada" in err_grp.json()["detail"]

    # Intento de agregar un nuevo nivel
    err_lvl = await client.post(f"/groups/{group_id}/levels", headers=headers, json={"name": "Nivel Extra"})
    assert err_lvl.status_code == 409
    assert "congelada" in err_lvl.json()["detail"]

    # Intento de agregar un nuevo nodo
    err_node = await client.post(
        f"/groups/{group_id}/nodes",
        headers=headers,
        json={"level_id": lvl1["id"], "parent_id": None, "name": "Nodo Extra", "code": "EXTRA"},
    )
    assert err_node.status_code == 409
    assert "congelada" in err_node.json()["detail"]

    # Intento de agregar un nuevo cargo
    err_cnt = await client.post(
        f"/groups/{group_id}/contests",
        headers=headers,
        json={"name": "Cargo Extra", "scope_level_id": lvl1["id"]},
    )
    assert err_cnt.status_code == 409
    assert "congelada" in err_cnt.json()["detail"]

    # Intento de agregar un candidato
    err_cand = await client.post(
        f"/constituencies/{const_tec_id}/candidates",
        headers=headers,
        json={"name": "Candidato Tarde", "party_or_front": "FRENTE TARDE"},
    )
    assert err_cand.status_code == 409
    assert "congelada" in err_cand.json()["detail"]
