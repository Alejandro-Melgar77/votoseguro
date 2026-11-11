"""
Pruebas de Invariante #1: Aislamiento Estricto Multi-Tenant
Garantiza que ninguna consulta ni mutación cruce los límites entre organizaciones.
"""
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tenancy_isolation_elections(client: AsyncClient, org1_setup, org2_setup):
    org1, admin1, token1 = org1_setup
    org2, admin2, token2 = org2_setup

    headers_org1 = {"Authorization": f"Bearer {token1}"}
    headers_org2 = {"Authorization": f"Bearer {token2}"}

    # 1. Org 1 crea una elección
    now = datetime.now(timezone.utc)
    election_payload = {
        "name": "Elección Universitaria EL GRAN ESTUDIO 2026",
        "description": "Elección de autoridades de la Org 1",
        "timezone": "America/La_Paz",
        "registration_opens_at": (now + timedelta(days=1)).isoformat(),
        "registration_closes_at": (now + timedelta(days=5)).isoformat(),
        "voting_opens_at": (now + timedelta(days=6)).isoformat(),
        "voting_closes_at": (now + timedelta(days=7)).isoformat(),
        "k_anonymity": 5,
    }

    create_res = await client.post("/elections", json=election_payload, headers=headers_org1)
    assert create_res.status_code == 201
    election_id = create_res.json()["id"]

    # 2. Org 1 puede listar su elección
    list_res1 = await client.get("/elections", headers=headers_org1)
    assert list_res1.status_code == 200
    elections_org1 = list_res1.json()
    assert len(elections_org1) == 1
    assert elections_org1[0]["id"] == election_id

    # 3. Org 2 lista sus elecciones -> DEBE SER VACÍA (Aislamiento Multi-Tenant)
    list_res2 = await client.get("/elections", headers=headers_org2)
    assert list_res2.status_code == 200
    assert len(list_res2.json()) == 0

    # 4. Org 2 intenta leer la elección de Org 1 por ID -> 404 Not Found
    get_res2 = await client.get(f"/elections/{election_id}", headers=headers_org2)
    assert get_res2.status_code == 404
    assert "no existe en su organización" in get_res2.json()["detail"]

    # 5. Org 2 intenta modificar el cronograma de Org 1 -> 404 Not Found
    schedule_payload = {
        "registration_opens_at": (now + timedelta(days=2)).isoformat(),
        "registration_closes_at": (now + timedelta(days=6)).isoformat(),
        "voting_opens_at": (now + timedelta(days=7)).isoformat(),
        "voting_closes_at": (now + timedelta(days=8)).isoformat(),
        "reason": "Intento no autorizado de modificación",
    }
    put_res2 = await client.put(f"/elections/{election_id}/schedule", json=schedule_payload, headers=headers_org2)
    assert put_res2.status_code == 404

    # 6. Org 2 intenta asignar un delegado a la elección de Org 1 -> 404 Not Found
    delegate_payload = {
        "email": "delegado.intruso@cne.gob.ec",
        "full_name": "Delegado Intruso",
        "password": "PasswordValido123!",
    }
    del_res2 = await client.post(f"/elections/{election_id}/delegates", json=delegate_payload, headers=headers_org2)
    assert del_res2.status_code == 404
