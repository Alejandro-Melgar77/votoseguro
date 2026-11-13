"""
Batería de Pruebas de la Infraestructura del Túnel Estático y Puente Neuronal (Sprint 2.5).
Verifica:
1. Extractor robusto extract_first_json_object (bloques markdown, preámbulos y caracteres de escape).
2. Cabeceras obligatorias para ngrok ('ngrok-skip-browser-warning': 'true' y User-Agent).
3. Endpoints de control y telemetría:
   - GET /api/v1/ai/node/status
   - PUT /api/v1/ai/node/config (Restringido a PLATFORM_ADMIN / ADMIN_GENERAL)
   - POST /api/v1/ai/node/test-inference
   - POST /api/v1/ai/node/ping (Notificación desde lanzadores de escritorio)
4. Comportamiento del Modo Neuronal Estricto (HTTP 503 vs Fallback Determinista en modo permisivo).
"""
import json
import uuid
import pytest
import httpx
from httpx import AsyncClient, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import LocalLlmEngine, extract_first_json_object
from app.ai.schemas import AnomalyExplanationResponse
from app.db.models.ai import AiRuntimeConfig
from app.db.models.user import User


class DummySampleSchema(BaseModel):
    key: str
    number: int


def test_extract_first_json_object_robustness():
    """Valida la extracción de JSON ante diversas variaciones de formato y envoltura de modelos 1.7B."""
    # 1. JSON puro
    raw1 = '{"key": "test", "number": 42}'
    assert extract_first_json_object(raw1) == raw1

    # 2. Bloque markdown ```json ... ```
    raw2 = '```json\n{"key": "markdown", "number": 99}\n```'
    clean2 = extract_first_json_object(raw2)
    parsed2 = json.loads(clean2)
    assert parsed2["key"] == "markdown"
    assert parsed2["number"] == 99

    # 3. Bloque markdown ``` ... ``` sin etiqueta json
    raw3 = '```\n{"key": "simple_fence", "number": 100}\n```'
    clean3 = extract_first_json_object(raw3)
    parsed3 = json.loads(clean3)
    assert parsed3["key"] == "simple_fence"

    # 4. Texto conversacional con preámbulo y cierre
    raw4 = (
        "¡Hola! Claro que sí, a continuación presento el dictamen electoral estructurado:\n\n"
        '{"key": "conversational", "number": 7}\n\n'
        "Espero que esta respuesta sea de utilidad para el proceso electoral."
    )
    clean4 = extract_first_json_object(raw4)
    parsed4 = json.loads(clean4)
    assert parsed4["key"] == "conversational"
    assert parsed4["number"] == 7

    # 5. Texto vacío o solo espacios
    assert extract_first_json_object("") == ""
    assert extract_first_json_object("   ") == ""


@pytest.mark.asyncio
async def test_ngrok_mandatory_headers_in_call(monkeypatch):
    """Verifica que toda invocación httpx incluya obligatoriamente ngrok-skip-browser-warning: true."""
    captured_headers = {}

    async def mock_post(self, url, json=None, headers=None, **kwargs):
        nonlocal captured_headers
        captured_headers = headers or {}
        return Response(
            status_code=200,
            json={
                "choices": [
                    {"message": {"content": '{"key": "verified", "number": 1}'}}
                ]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    result = await LocalLlmEngine.call_structured(
        prompt="Dame un json",
        schema_cls=DummySampleSchema,
        fallback_fn=lambda: DummySampleSchema(key="fallback", number=0),
        function_name="TEST_HEADERS",
    )

    assert result.key == "verified"
    assert captured_headers.get("ngrok-skip-browser-warning") == "true"
    assert captured_headers.get("User-Agent") == "VotoSeguro-Core-Backend/2.0"
    assert captured_headers.get("Content-Type") == "application/json"


@pytest.mark.asyncio
async def test_ai_node_status_endpoint(client: AsyncClient, monkeypatch):
    """Verifica el endpoint GET /api/v1/ai/node/status reportando telemetría del túnel."""
    async def mock_ping(llm_base_url, timeout=6.0):
        return {
            "online": True,
            "latency_ms": 35.5,
            "available_models": ["votoseguro-lfm3", "lfm3"],
            "status_code": 200,
        }

    monkeypatch.setattr(LocalLlmEngine, "ping_tunnel", mock_ping)

    resp = await client.get("/ai/node/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["online"] is True
    assert "votoseguro-lfm3" in data["model_name"]
    assert data["latency_ms"] == 35.5
    assert "CONECTADO" in data["status_label"]
    assert "votoseguro-lfm3" in data["available_models"]


@pytest.mark.asyncio
async def test_ai_node_config_update_and_persistence(
    client: AsyncClient,
    platform_admin_token: str,
    test_db: AsyncSession,
    monkeypatch,
):
    """Verifica PUT /api/v1/ai/node/config permitiendo ajustar URL, modo estricto y proveedor."""
    async def mock_ping(llm_base_url, timeout=5.0):
        return {"online": True, "latency_ms": 15.0, "available_models": ["custom-model"]}

    monkeypatch.setattr(LocalLlmEngine, "ping_tunnel", mock_ping)

    payload = {
        "llm_base_url": "https://custom-new-tunnel.ngrok-free.dev/v1",
        "model_name": "custom-lfm3",
        "provider": "LM_STUDIO",
        "strict_neural_mode": True,
        "timeout_seconds": 18.0,
    }

    # Intentar sin token -> HTTP 401
    resp_unauth = await client.put("/ai/node/config", json=payload)
    assert resp_unauth.status_code in (401, 403)

    # Con token de PLATFORM_ADMIN
    headers = {"Authorization": f"Bearer {platform_admin_token}"}
    resp = await client.put("/ai/node/config", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["llm_base_url"] == "https://custom-new-tunnel.ngrok-free.dev/v1"
    assert data["model_name"] == "custom-lfm3"
    assert data["provider"] == "LM_STUDIO"
    assert data["strict_neural_mode"] is True

    # Verificar persistencia efectiva
    effective = await LocalLlmEngine.get_effective_config(test_db)
    assert effective["llm_base_url"] == "https://custom-new-tunnel.ngrok-free.dev/v1"
    assert effective["strict_neural_mode"] is True
    assert effective["provider"] == "LM_STUDIO"


@pytest.mark.asyncio
async def test_ai_node_ping_from_launcher(client: AsyncClient, test_db: AsyncSession):
    """Verifica el endpoint POST /api/v1/ai/node/ping invocado por INICIAR_IA_LOCAL.bat."""
    payload = {
        "node_status": "ONLINE",
        "llm_base_url": "https://repackage-remarry-reviving.ngrok-free.dev/v1",
        "model_name": "votoseguro-lfm3",
        "provider": "OLLAMA",
        "local_latency_ms": 8.4,
    }
    resp = await client.post("/ai/node/ping", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["acknowledged"] is True
    assert "received_at" in data


@pytest.mark.asyncio
async def test_strict_neural_mode_503_vs_degraded_fallback(monkeypatch, test_db: AsyncSession):
    """
    Verifica que:
    1. Si strict_neural_mode == False y la PC está apagada, responde con DETERMINISTIC_FALLBACK sin error.
    2. Si strict_neural_mode == True y la PC está apagada, lanza HTTP 503 explicando que se debe ejecutar INICIAR_IA_LOCAL.bat.
    """
    async def mock_fail_post(self, url, **kwargs):
        raise httpx.ConnectError("Connection refused by host")

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_fail_post)

    # Caso A: strict_neural_mode = False -> Retorna fallback determinista
    async def mock_cfg_permissive(db=None):
        return {
            "llm_base_url": "http://127.0.0.1:9999/v1",
            "llm_model_name": "votoseguro-lfm3",
            "provider": "OLLAMA",
            "strict_neural_mode": False,
            "timeout_seconds": 1.0,
        }

    monkeypatch.setattr(LocalLlmEngine, "get_effective_config", mock_cfg_permissive)

    res_fallback = await LocalLlmEngine.call_structured(
        prompt="Evalúa",
        schema_cls=DummySampleSchema,
        fallback_fn=lambda: DummySampleSchema(key="fallback_permissive", number=10),
        function_name="TEST_STRICT_FALSE",
    )
    assert res_fallback.key == "fallback_permissive"

    # Caso B: strict_neural_mode = True -> Lanza HTTP 503
    async def mock_cfg_strict(db=None):
        return {
            "llm_base_url": "http://127.0.0.1:9999/v1",
            "llm_model_name": "votoseguro-lfm3",
            "provider": "OLLAMA",
            "strict_neural_mode": True,
            "timeout_seconds": 1.0,
        }

    monkeypatch.setattr(LocalLlmEngine, "get_effective_config", mock_cfg_strict)

    with pytest.raises(Exception) as exc_info:
        await LocalLlmEngine.call_structured(
            prompt="Evalúa estricto",
            schema_cls=DummySampleSchema,
            fallback_fn=lambda: DummySampleSchema(key="fallback_strict", number=20),
            function_name="TEST_STRICT_TRUE",
        )
    # Debe ser HTTP 503 con mensaje instructivo
    assert "503" in str(exc_info.value) or "INICIAR_IA_LOCAL.bat" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ai_node_test_inference_endpoint(
    client: AsyncClient,
    platform_admin_token: str,
    monkeypatch,
):
    """Verifica POST /api/v1/ai/node/test-inference ejecutando prueba de inferencia asistida."""
    async def mock_call_structured(prompt, schema_cls, fallback_fn, **kwargs):
        return AnomalyExplanationResponse(
            anomaly_id="TEST-LIVE-001",
            code="Z_SCORE_SPIKE",
            severity="HIGH",
            metrics_summary={"z_score": 2.45},
            explanation_es="Desviación estadística crítica verificada en vivo por el nodo neuronal local.",
            recommended_checks=["Auditar acta de escrutinio", "Verificar cadena de hashes"],
            requires_human_decision=True,
            ai_source="LFM3-1.7B_NEURAL_TUNNEL",
            model_name="votoseguro-lfm3",
            latency_ms=1850,
        )

    monkeypatch.setattr(LocalLlmEngine, "call_structured", mock_call_structured)

    headers = {"Authorization": f"Bearer {platform_admin_token}"}
    resp = await client.post(
        "/ai/node/test-inference",
        json={"prompt": "Prueba electoral", "task_type": "IA-L1"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["ai_source"] == "LFM3-1.7B_NEURAL_TUNNEL"
    assert data["model_name"] == "votoseguro-lfm3"
    assert data["latency_ms"] == 1850.0
    assert data["audit_logged"] is True
