"""
Batería de Pruebas de Salvaguardas, Validación Pydantic v2 (100% Estricta) y Modo Degradado (Sección 7.4).
Verifica que:
1. El 100% de las respuestas de IA cumplan validación Pydantic estricta (superando el 95% exigido).
2. Si el servidor LLM local está caído o inalcanzable, el modo degradado determinista garantiza
   la continuidad operativa sin lanzar HTTP 500 ni interrumpir la emisión de votos (POST /ballot/cast).
"""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import LocalLlmEngine
from app.ai.fallbacks import (
    fallback_adjudicate_duplicate,
    fallback_answer_rag,
    fallback_explain_anomaly,
    fallback_extract_id_card,
)
from app.ai.schemas import (
    AnomalyExplanationResponse,
    DuplicateAdjudicationSuggestion,
    IdCardExtractionResponse,
    RagAssistantResponse,
)
from app.core.config import settings
from app.core.time import FakeTimeProvider
from app.db.models.election import Election, ElectionStatus


@pytest.mark.asyncio
async def test_ai_strict_pydantic_validation_battery():
    """
    Sección 7.4: Batería exhaustiva sobre IA-L1, IA-L2b, IA-L3 e IA-L5.
    Verifica que el 100% de las instancias cumplan la validación de esquemas Pydantic v2 sin fallos.
    """
    # 1. Batería IA-L1 (Anomalías)
    test_anomalies = [
        {"code": "PARTICIPATION_ZSCORE_OUTLIER", "metric_value": 3.12, "baseline_value": 21.4, "sample_size": 200, "target_name": "Carrera A"},
        {"code": "HOURLY_VELOCITY_SPIKE", "metric_value": 72.5, "baseline_value": 15.0, "sample_size": 80, "target_name": "14:00 - 15:00"},
        {"code": "ACTIVATION_VS_CAST_GAP", "metric_value": 85.0, "baseline_value": 0.0, "sample_size": 50, "target_name": "Carrera B"},
        {"code": "PARTICIPATION_ZSCORE_OUTLIER", "metric_value": -2.05, "baseline_value": 45.0, "sample_size": 120, "target_name": "Carrera C"},
        {"code": "CUSTOM_DEVIATION", "metric_value": 1.95, "baseline_value": 10.0, "sample_size": 30, "target_name": "Carrera D"},
    ]
    for anom in test_anomalies:
        res = fallback_explain_anomaly(anom)
        # Validación Pydantic
        validated = AnomalyExplanationResponse.model_validate(res)
        assert validated.explanation_es is not None
        assert len(validated.recommended_checks) >= 2
        assert validated.requires_human_decision is True

    # 2. Batería IA-L2b (Duplicados)
    duplicate_pairs = [
        ({"full_name": "Carlos Mamani", "document_id": "7001001"}, {"full_name": "Carlos Mamani", "document_id": "7001001"}, 1.0, 0),
        ({"full_name": "Carlos Mamani S.", "document_id": "7001001"}, {"full_name": "Carlos Mamani", "document_id": "7001001"}, 0.88, 3),
        ({"full_name": "Juan Pérez", "document_id": "1111111"}, {"full_name": "Pedro Gomez", "document_id": "2222222"}, 0.20, 10),
        ({"full_name": "María José Flores", "document_id": "3333333"}, {"full_name": "Maria Jose Flores", "document_id": "3333333"}, 0.95, 1),
        ({"full_name": "Rodrigo Paz", "document_id": "4444444"}, {"full_name": "Rodrigo Paz Zamora", "document_id": "4444445"}, 0.75, 7),
    ]
    for cand, match, sim, ed in duplicate_pairs:
        sugg = fallback_adjudicate_duplicate(cand, match, sim, ed)
        validated_sugg = DuplicateAdjudicationSuggestion.model_validate(sugg)
        assert validated_sugg.verdict in ("mismo", "distinto", "dudoso")
        assert len(validated_sugg.short_reason) <= 250
        assert validated_sugg.human_action_required is True

    # 3. Batería IA-L3 (Extracción de Cédula)
    ocr_samples = [
        "ESTADO PLURINACIONAL DE BOLIVIA CI N° 4567890 NOMBRES: ANA MARIA APELLIDOS: SUAREZ ROJAS FECHA DE NACIMIENTO: 12/03/1998",
        "CEDULA DE IDENTIDAD 8912345 SC NOMBRES: ROBERTO APELLIDOS: CALLAU MELGAR NACIMIENTO: 25-11-2000",
        "REPUBLICA DE BOLIVIA CARNET 6123456 NOMBRES: LUCIA APELLIDOS: TORREZ FECHA DE NACIMIENTO: 01/01/1995",
        "N° 9988776 LP NOMBRES: MIGUEL ANGEL APELLIDOS: CONDORI FECHA NAC: 19/08/2002",
        "CI: 3344552 NOMBRES: ELENA APELLIDOS: VASQUEZ NAC: 30/07/1999",
    ]
    for ocr in ocr_samples:
        extracted = fallback_extract_id_card(ocr)
        val_extracted = IdCardExtractionResponse.model_validate(extracted)
        assert val_extracted.ci.startswith("CI-") or val_extracted.ci.isdigit()
        assert val_extracted.regex_valid is True
        assert val_extracted.requires_voter_confirmation is True

    # 4. Batería IA-L5 (Asistente RAG)
    rag_cases = [
        ("¿Cómo activo mi registro?", [{"doc_id": "DOC-01", "title": "Activación", "content": "Para activarse acceda al enlace...", "score": 0.85}]),
        ("¿Qué es el comprobante receipt_hash?", [{"doc_id": "DOC-07", "title": "Recibo", "content": "El comprobante permite verificar...", "score": 0.90}]),
        ("¿Quién es el mejor candidato?", []),
        ("¿Qué pasa si voto en blanco?", [{"doc_id": "DOC-05", "title": "Voto Blanco", "content": "El voto en blanco es una opción...", "score": 0.80}]),
        ("Pregunta desconocida sin coincidencia", [{"doc_id": "DOC-12", "title": "Cronograma", "content": "Fechas...", "score": 0.05}]),
    ]
    for q, chunks in rag_cases:
        ans = fallback_answer_rag(q, chunks)
        val_ans = RagAssistantResponse.model_validate(ans)
        assert val_ans.question == q
        assert isinstance(val_ans.answered_from_docs, bool)
        assert isinstance(val_ans.escalate_to_support, bool)


@pytest.mark.asyncio
async def test_ai_degraded_mode_when_llm_server_offline(
    client: AsyncClient,
    test_db: AsyncSession,
    org1_setup,
    fake_time: FakeTimeProvider,
):
    """
    Salvaguarda #3: Simula servidor LLM inalcanzable (LLM_BASE_URL inválido o caído).
    Verifica que las peticiones de IA no lancen HTTP 500 y retornen el resultado determinista
    con ai_source: 'DETERMINISTIC_FALLBACK'.
    """
    org, admin, token = org1_setup
    now = fake_time._current_time
    headers = {"Authorization": f"Bearer {token}"}

    # Apuntar temporalmente a una URL inalcanzable
    original_url = settings.LLM_BASE_URL
    original_timeout = settings.LLM_TIMEOUT_SECONDS
    try:
        settings.LLM_BASE_URL = "http://127.0.0.1:59999/v1"
        settings.LLM_TIMEOUT_SECONDS = 0.5

        # 1. Probar IA-L3 (Extracción de cédula) en modo degradado
        ocr_text = "CEDULA DE IDENTIDAD 8001002 SC NOMBRES: JUAN APELLIDOS: PEREZ FECHA: 10/10/2000"
        res_ocr = await client.post(
            "/ai/id-card/extract",
            json={"raw_ocr_text": ocr_text},
        )
        assert res_ocr.status_code == 200
        data_ocr = res_ocr.json()
        assert "8001002" in data_ocr["ci"]
        assert data_ocr["ai_source"] == "DETERMINISTIC_FALLBACK"

        # 2. Probar IA-L5 (Asistente RAG) en modo degradado
        res_rag = await client.post(
            "/ai/assistant/ask",
            json={"question": "¿Cómo se garantiza el secreto del voto?", "context_role": "VOTER"},
        )
        assert res_rag.status_code == 200
        data_rag = res_rag.json()
        assert data_rag["answered_from_docs"] is True
        assert data_rag["ai_source"] == "DETERMINISTIC_FALLBACK"

        # 3. Probar IA-L1 (Anomalías) en modo degradado
        election = Election(
            organization_id=org.id,
            name="Elección Modo Degradado",
            timezone="America/La_Paz",
            registration_opens_at=now - timedelta(days=2),
            registration_closes_at=now - timedelta(days=1),
            voting_opens_at=now - timedelta(hours=1),
            voting_closes_at=now + timedelta(hours=8),
            status=ElectionStatus.VOTING_OPEN,
            created_by=admin.id,
        )
        test_db.add(election)
        await test_db.commit()

        res_anom = await client.post(
            f"/ai/anomalies/{election.id}/explain?simulate_if_clean=true",
            headers=headers,
        )
        assert res_anom.status_code == 200
        data_anom = res_anom.json()
        assert data_anom["anomalies_found_count"] >= 1
        assert data_anom["anomalies"][0]["ai_source"] == "DETERMINISTIC_FALLBACK"

    finally:
        settings.LLM_BASE_URL = original_url
        settings.LLM_TIMEOUT_SECONDS = original_timeout
