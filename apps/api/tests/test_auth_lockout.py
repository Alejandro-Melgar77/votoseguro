"""
Pruebas de Invariante: Bloqueo de Cuenta por Fuerza Bruta (RF-03)
Valida bloqueo temporal tras 5 intentos fallidos y desbloqueo determinista por tiempo de servidor.
"""
import pytest
from httpx import AsyncClient
from app.core.time import FakeTimeProvider


@pytest.mark.asyncio
async def test_brute_force_lockout_and_expiration(client: AsyncClient, org1_setup, fake_time: FakeTimeProvider):
    org, admin, token = org1_setup

    email = "admin@granestudio.edu.bo"
    correct_password = "AdminGranEstudio2026!"
    wrong_password = "PasswordIncorrecto!"

    # 1. Primeros 4 intentos fallidos -> 401 Unauthorized
    for attempt in range(1, 5):
        res = await client.post("/auth/login", json={"email": email, "password": wrong_password})
        assert res.status_code == 401
        assert "Correo electrónico o contraseña incorrectos" in res.json()["detail"]

    # 2. Quinto intento fallido consecutivo -> 423 Locked
    res_fifth = await client.post("/auth/login", json={"email": email, "password": wrong_password})
    assert res_fifth.status_code == 423
    assert "Cuenta bloqueada temporalmente" in res_fifth.json()["detail"]

    # 3. Intentar con la contraseña CORRECTA mientras está bloqueada -> Sigue respondiendo 423 Locked
    res_locked_correct = await client.post("/auth/login", json={"email": email, "password": correct_password})
    assert res_locked_correct.status_code == 423
    assert "Cuenta bloqueada temporalmente" in res_locked_correct.json()["detail"]

    # 4. El tiempo del servidor avanza 16 minutos (el bloqueo es de 15 minutos)
    fake_time.advance(minutes=16)

    # 5. Tras expirar el tiempo de bloqueo, el login con la contraseña correcta debe ser exitoso (200 OK)
    res_success = await client.post("/auth/login", json={"email": email, "password": correct_password})
    assert res_success.status_code == 200
    data = res_success.json()
    assert "access_token" in data
    assert data["user"]["email"] == email
    assert data["user"]["failed_attempts"] == 0
    assert data["user"]["locked_until"] is None
