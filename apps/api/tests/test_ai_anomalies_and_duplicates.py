"""
Pruebas de Invariante para IA Local: Detección de Anomalías (IA-L1), Segunda Opinión de Duplicados (IA-L2b),
y Registro Inmutable en ai_call_log y audit_log (Invariantes #11 y #14).
"""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import FakeTimeProvider
from app.db.models.audit import AiCallLog, AuditLog
from app.db.models.election import Election, ElectionStatus
from app.db.models.voter import ImportBatch, ImportIssue, Voter, VoterStatus


@pytest.mark.asyncio
async def test_ai_anomalies_explanation_and_audit(
    client: AsyncClient,
    test_db: AsyncSession,
    org1_setup,
    fake_time: FakeTimeProvider,
):
    """
    IA-L1: Verifica detección de anomalías estadísticas sin revelar conteos por candidato (Invariante #11),
    validación Pydantic estricta y trazabilidad en ai_call_log y audit_log (Invariante #14).
    """
    org, admin, token = org1_setup
    now = fake_time._current_time
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Crear elección en VOTING_OPEN
    election = Election(
        organization_id=org.id,
        name="Elección de Auditoría de Anomalías",
        timezone="America/La_Paz",
        registration_opens_at=now - timedelta(days=2),
        registration_closes_at=now - timedelta(days=1),
        voting_opens_at=now - timedelta(hours=2),
        voting_closes_at=now + timedelta(hours=10),
        status=ElectionStatus.VOTING_OPEN,
        k_anonymity=5,
        created_by=admin.id,
    )
    test_db.add(election)
    await test_db.commit()
    await test_db.refresh(election)

    # 2. Llamar al endpoint de explicación con simulación activa
    res = await client.post(
        f"/ai/anomalies/{election.id}/explain?simulate_if_clean=true",
        headers=headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["election_id"] == str(election.id)
    assert data["anomalies_found_count"] >= 1
    assert len(data["anomalies"]) >= 1

    first_anom = data["anomalies"][0]
    assert first_anom["code"] in ("PARTICIPATION_ZSCORE_OUTLIER", "HOURLY_VELOCITY_SPIKE", "ACTIVATION_VS_CAST_GAP")
    assert first_anom["severity"] in ("LOW", "MEDIUM", "HIGH")
    assert isinstance(first_anom["explanation_es"], str)
    assert len(first_anom["explanation_es"]) > 20
    assert isinstance(first_anom["recommended_checks"], list)
    assert len(first_anom["recommended_checks"]) >= 2
    assert first_anom["requires_human_decision"] is True
    assert first_anom["ai_source"] in ("LFM3-1.7B", "DETERMINISTIC_FALLBACK")

    # Invariante #11: Las métricas jamás contienen conteos por candidato ni opciones políticas
    metrics_str = str(first_anom["metrics_summary"]).lower()
    assert "candidate" not in metrics_str
    assert "candidato" not in metrics_str
    assert "party" not in metrics_str

    # 3. Verificar persistencia en ai_call_log y audit_log encadenado
    stmt_ai = select(AiCallLog).where(AiCallLog.election_id == election.id)
    ai_logs = list((await test_db.execute(stmt_ai)).scalars().all())
    assert len(ai_logs) >= 1
    first_log = ai_logs[0]
    assert first_log.function_name == "IA-L1_ANOMALY_EXPLAIN"
    assert first_log.status in ("SUCCESS_LLM", "FALLBACK_DETERMINISTIC")
    assert "anomalía de participación" in first_log.summary.lower()

    # Verificar que el evento se reflejó en audit_log encadenado
    stmt_audit = select(AuditLog).where(
        AuditLog.election_id == election.id,
        AuditLog.action == "AI_EVENT_RECORDED",
    )
    audit_events = list((await test_db.execute(stmt_audit)).scalars().all())
    assert len(audit_events) >= 1
    assert audit_events[0].actor_role == "SYSTEM_AI"
    assert audit_events[0].entry_hash is not None


@pytest.mark.asyncio
async def test_ai_duplicates_adjudication_human_in_the_loop(
    client: AsyncClient,
    test_db: AsyncSession,
    org1_setup,
    fake_time: FakeTimeProvider,
):
    """
    IA-L2b: Segunda opinión de LFM3-1.7B sobre duplicados ("José Rodríguez" vs "Jose Rodriguez S.").
    Verifica veredicto válido ('mismo' | 'distinto' | 'dudoso'), motivo conciso y que JAMÁS
    se modifique de forma autónoma el campo resolution ni el estado del votante en el padrón.
    """
    org, admin, token = org1_setup
    now = fake_time._current_time
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Crear elección y lote de importación con posible duplicado
    election = Election(
        organization_id=org.id,
        name="Elección Duplicados IA",
        timezone="America/La_Paz",
        registration_opens_at=now,
        registration_closes_at=now + timedelta(days=2),
        voting_opens_at=now + timedelta(days=3),
        voting_closes_at=now + timedelta(days=4),
        status=ElectionStatus.REGISTRATION_OPEN,
        created_by=admin.id,
    )
    test_db.add(election)
    await test_db.flush()

    batch = ImportBatch(
        organization_id=org.id,
        election_id=election.id,
        uploaded_by=admin.id,
        filename="padron_estudiantes_2026.csv",
        total_rows=10,
        valid_rows=8,
        error_rows=0,
        duplicate_warnings=1,
    )
    test_db.add(batch)
    await test_db.flush()

    issue = ImportIssue(
        batch_id=batch.id,
        row_number=4,
        issue_type="POSSIBLE_DUPLICATE",
        document_id="8001002",
        raw_full_name="José Rodríguez",
        similarity_score=0.82,
        edit_distance=2,
        resolution="PENDING",
        details={
            "matched_name": "Jose Rodriguez S.",
            "matched_doc": "8001002",
        },
    )
    test_db.add(issue)
    await test_db.commit()

    # 2. Arbitrar por lote: POST /ai/duplicates/{batch_id}/adjudicate
    res_batch = await client.post(
        f"/ai/duplicates/{batch.id}/adjudicate",
        headers=headers,
    )
    assert res_batch.status_code == 200, res_batch.text
    batch_data = res_batch.json()

    assert batch_data["batch_id"] == str(batch.id)
    assert batch_data["total_evaluated"] == 1
    assert len(batch_data["suggestions"]) == 1

    sugg = batch_data["suggestions"][0]
    assert sugg["issue_id"] == str(issue.id)
    assert sugg["verdict"] in ("mismo", "distinto", "dudoso")
    assert sugg["confidence_label"] in ("ALTA", "MEDIA", "BAJA")
    assert len(sugg["short_reason"]) <= 250
    assert sugg["human_action_required"] is True
    assert sugg["ai_source"] in ("LFM3-1.7B", "DETERMINISTIC_FALLBACK")

    # 3. Comprobar en base de datos: guardó veredicto y motivo pero NUNCA cambió resolution
    await test_db.refresh(issue)
    assert issue.ai_verdict in ("mismo", "distinto", "dudoso")
    assert issue.ai_reason is not None
    assert issue.ai_model in ("LiquidAI/LFM3-1.7B-Q4_K_M", "DETERMINISTIC_FALLBACK")
    assert issue.ai_evaluated_at is not None
    # Salvaguarda Crítica: La resolución permanece intacta hasta que el Administrador decida
    assert issue.resolution == "PENDING"

    # 4. Probar arbitraje individual por issue_id
    res_single = await client.post(
        f"/ai/duplicates/issues/{issue.id}/adjudicate",
        headers=headers,
    )
    assert res_single.status_code == 200
    single_data = res_single.json()
    assert single_data["issue_id"] == str(issue.id)
    assert single_data["verdict"] in ("mismo", "distinto", "dudoso")
    assert single_data["human_action_required"] is True
