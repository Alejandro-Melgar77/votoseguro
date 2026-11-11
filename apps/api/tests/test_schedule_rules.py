"""
Pruebas de Invariante #4: Reglas de Validación y Edición del Cronograma (Secciones 5.3 y 5.4)
"""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.time import FakeTimeProvider
from app.db.models.election import Election, ElectionStatus


@pytest.mark.asyncio
async def test_schedule_chronological_order_invariants(client: AsyncClient, org1_setup, fake_time: FakeTimeProvider):
    org, admin, token = org1_setup
    headers = {"Authorization": f"Bearer {token}"}
    now = await fake_time.now()

    # 1. Intento de crear elección donde registration_closes_at > voting_opens_at (solapamiento prohibido)
    invalid_payload = {
        "name": "Elección con Cronograma Inválido",
        "description": "El registro cierra después de que la votación abrió",
        "timezone": "America/La_Paz",
        "registration_opens_at": (now + timedelta(days=1)).isoformat(),
        "registration_closes_at": (now + timedelta(days=5)).isoformat(),
        "voting_opens_at": (now + timedelta(days=4)).isoformat(),  # INVÁLIDO: antes del fin del registro
        "voting_closes_at": (now + timedelta(days=6)).isoformat(),
        "k_anonymity": 5,
    }

    res = await client.post("/elections", json=invalid_payload, headers=headers)
    assert res.status_code == 422
    assert "orden cronológico es inválido" in res.json()["detail"]


@pytest.mark.asyncio
async def test_schedule_editing_rules_during_voting_open(
    client: AsyncClient, org1_setup, test_db: AsyncSession, fake_time: FakeTimeProvider
):
    org, admin, token = org1_setup
    headers = {"Authorization": f"Bearer {token}"}
    now = await fake_time.now()

    # 1. Crear elección en DRAFT
    valid_payload = {
        "name": "Elección para Prueba de Edición en VOTING_OPEN",
        "description": "Validación de matriz de mutabilidad",
        "timezone": "America/La_Paz",
        "registration_opens_at": (now + timedelta(days=1)).isoformat(),
        "registration_closes_at": (now + timedelta(days=3)).isoformat(),
        "voting_opens_at": (now + timedelta(days=4)).isoformat(),
        "voting_closes_at": (now + timedelta(days=5)).isoformat(),
        "k_anonymity": 5,
    }
    create_res = await client.post("/elections", json=valid_payload, headers=headers)
    assert create_res.status_code == 201
    election_id_str = create_res.json()["id"]
    election_id = uuid.UUID(election_id_str)

    # 2. Simular que la elección transicionó a VOTING_OPEN
    await test_db.execute(
        update(Election)
        .where(Election.id == election_id)
        .values(status=ElectionStatus.VOTING_OPEN)
    )
    await test_db.commit()

    # Situar el reloj dentro de la ventana de votación
    fake_time.set_time(now + timedelta(days=4, hours=2))
    current_now = await fake_time.now()

    # 3. Intentar modificar registration_opens_at en VOTING_OPEN -> 409 Conflict
    forbidden_edit_payload = {
        "registration_opens_at": (current_now + timedelta(days=1)).isoformat(),
        "registration_closes_at": (current_now + timedelta(days=3)).isoformat(),
        "voting_opens_at": (current_now + timedelta(days=4)).isoformat(),
        "voting_closes_at": (current_now + timedelta(days=5)).isoformat(),
        "reason": "Intento de cambiar fecha de registro mientras votación está abierta",
    }
    res_conflict = await client.put(f"/elections/{election_id}/schedule", json=forbidden_edit_payload, headers=headers)
    assert res_conflict.status_code == 409
    assert "únicamente se permite modificar la hora de cierre de la votación" in res_conflict.json()["detail"]

    # 4. Intentar modificar voting_closes_at sin motivo o con motivo menor a 10 caracteres -> 422
    no_reason_payload = {
        "registration_opens_at": (now + timedelta(days=1)).isoformat(),
        "registration_closes_at": (now + timedelta(days=3)).isoformat(),
        "voting_opens_at": (now + timedelta(days=4)).isoformat(),
        "voting_closes_at": (current_now + timedelta(hours=3)).isoformat(),
        "reason": "Corto",  # Menos de 10 caracteres
    }
    res_no_reason = await client.put(f"/elections/{election_id}/schedule", json=no_reason_payload, headers=headers)
    assert res_no_reason.status_code == 422
    assert "al menos 10 caracteres" in res_no_reason.json()["detail"]

    # 5. Intentar fijar voting_closes_at a menos de 5 minutos desde la hora actual del servidor -> 422
    less_than_5_min_payload = {
        "registration_opens_at": (now + timedelta(days=1)).isoformat(),
        "registration_closes_at": (now + timedelta(days=3)).isoformat(),
        "voting_opens_at": (now + timedelta(days=4)).isoformat(),
        "voting_closes_at": (current_now + timedelta(minutes=4)).isoformat(),  # < 5 minutos
        "reason": "Ampliación de prueba con tiempo insuficiente",
    }
    res_under_5min = await client.put(f"/elections/{election_id}/schedule", json=less_than_5_min_payload, headers=headers)
    assert res_under_5min.status_code == 422
    assert "al menos a 5 minutos en el futuro" in res_under_5min.json()["detail"]

    # 6. Modificación válida: ampliar voting_closes_at por 3 horas con motivo formal -> 200 OK
    valid_extension_payload = {
        "registration_opens_at": (now + timedelta(days=1)).isoformat(),
        "registration_closes_at": (now + timedelta(days=3)).isoformat(),
        "voting_opens_at": (now + timedelta(days=4)).isoformat(),
        "voting_closes_at": (current_now + timedelta(hours=3)).isoformat(),
        "reason": "Ampliación autorizada por la Corte debido a alta concurrencia de votantes",
    }
    res_success = await client.put(f"/elections/{election_id}/schedule", json=valid_extension_payload, headers=headers)
    assert res_success.status_code == 200

    # 7. Verificar que el cambio quedó asentado en el historial de schedule_change
    history_res = await client.get(f"/elections/{election_id}/schedule/history", headers=headers)
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) == 1
    assert history[0]["field_name"] == "voting_closes_at"
    assert "Ampliación autorizada" in history[0]["reason"]
