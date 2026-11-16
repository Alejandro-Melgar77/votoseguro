"""
Pruebas de Invariante para Verificación Facial Asistida Selfie vs. Cédula (IA-E3):
- Consentimiento explícito obligatorio (rechazo 422 ante negativa).
- Invariante #15: Cero persistencia de imágenes en disco ni base de datos.
- Alternativa siempre disponible de verificación por código o mesa electoral.
"""
import base64
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import FakeTimeProvider
from app.db.models.audit import AuditLog
from app.db.models.election import BiometricVerificationAudit, Election, ElectionStatus


@pytest.mark.asyncio
async def test_biometric_verification_consent_rejection(
    test_db: AsyncSession,
    client: AsyncClient,
    org1_setup,
):
    """
    IA-E3 & Principio de Consentimiento: Si consent_accepted es False, la API
    debe rechazar la solicitud inmediatamente con HTTP 422 Unprocessable Entity.
    """
    org, admin, admin_token = org1_setup
    election_id = uuid.uuid4()

    payload = {
        "election_id": str(election_id),
        "document_id": "8001002",
        "consent_accepted": False,
        "selfie_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg==",
        "id_card_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg==",
        "use_fallback_code": False,
    }

    res = await client.post("/ai/biometric/verify", json=payload)
    assert res.status_code == 422, res.text
    err_data = res.json()
    assert "consentimiento explícito" in err_data.get("detail", "").lower()


@pytest.mark.asyncio
async def test_biometric_verification_images_processed_and_never_persisted(
    test_db: AsyncSession,
    client: AsyncClient,
    org1_setup,
    fake_time: FakeTimeProvider,
):
    """
    IA-E3 & Invariante #15: Procesa las imágenes exclusivamente en memoria RAM,
    devuelve veredicto estructurado y garantiza que ninguna imagen binaria ni Base64
    sea persistida en la tabla biometric_verification_audit ni en audit_log.
    """
    org, admin, admin_token = org1_setup
    now = datetime(2026, 11, 26, 10, 0, 0, tzinfo=timezone.utc)
    fake_time.set_time(now)

    # 1. Crear Elección
    election = Election(
        organization_id=org.id,
        name="Elección con Verificación Biométrica",
        timezone="America/La_Paz",
        registration_opens_at=now - timedelta(days=5),
        registration_closes_at=now + timedelta(days=5),
        voting_opens_at=now + timedelta(days=6),
        voting_closes_at=now + timedelta(days=7),
        status=ElectionStatus.REGISTRATION_OPEN,
        created_by=admin.id,
    )
    test_db.add(election)
    await test_db.commit()
    await test_db.refresh(election)

    # 2. Generar datos Base64 sintéticos identificables
    unique_marker_selfie = "SECRET_CANARY_SELFIE_BYTE_STREAM_12345"
    unique_marker_id = "SECRET_CANARY_ID_CARD_BYTE_STREAM_67890"

    fake_selfie_b64 = base64.b64encode(f"HEADER_JPEG_{unique_marker_selfie}".encode("utf-8")).decode("utf-8")
    fake_id_b64 = base64.b64encode(f"HEADER_JPEG_{unique_marker_id}".encode("utf-8")).decode("utf-8")

    payload = {
        "election_id": str(election.id),
        "document_id": "8002004",
        "consent_accepted": True,
        "selfie_base64": fake_selfie_b64,
        "id_card_base64": fake_id_b64,
        "use_fallback_code": False,
    }

    # 3. Invocación pública sin token (acceso de ciudadano en registro)
    res = await client.post("/ai/biometric/verify", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["match_verdict"] in ("MATCH_PROBABLE", "MISMATCH", "INCONCLUSIVE")
    assert data["images_persisted"] is False
    assert data["ai_source"] in ("GEMINI_EXTERNAL_API", "DETERMINISTIC_FALLBACK")
    assert "explanation_es" in data

    # 4. INVARIANTE #15: Comprobar la tabla biometric_verification_audit
    stmt = select(BiometricVerificationAudit).where(
        BiometricVerificationAudit.election_id == election.id
    )
    audit_rows = list((await test_db.execute(stmt)).scalars().all())
    assert len(audit_rows) >= 1

    saved = audit_rows[-1]
    assert saved.images_persisted is False
    assert saved.explicit_consent_given is True

    # Comprobación rigurosa de que ningún campo contiene el stream Base64 ni los canarios
    for attr in ("document_id", "verdict", "confidence_band", "explanation_es", "ai_source"):
        val = getattr(saved, attr, "")
        assert unique_marker_selfie not in str(val)
        assert unique_marker_id not in str(val)
        assert fake_selfie_b64 not in str(val)
        assert fake_id_b64 not in str(val)

    # 5. Comprobar que en audit_log tampoco se filtró ningún byte de las imágenes
    stmt_audit = select(AuditLog).where(AuditLog.election_id == election.id)
    audit_logs = list((await test_db.execute(stmt_audit)).scalars().all())
    for log in audit_logs:
        log_str = str(log.payload)
        assert unique_marker_selfie not in log_str
        assert unique_marker_id not in log_str
        assert fake_selfie_b64 not in log_str
        assert fake_id_b64 not in log_str


@pytest.mark.asyncio
async def test_biometric_fallback_alternative_code_without_images(
    test_db: AsyncSession,
    client: AsyncClient,
    org1_setup,
):
    """
    IA-E3 & Alternativa Cívica: Verifica que un votante pueda activar su credencial
    mediante código alternativo sin cámara ni imágenes biométricas.
    """
    org, admin, admin_token = org1_setup
    now = datetime(2026, 11, 26, 10, 0, 0, tzinfo=timezone.utc)

    election = Election(
        organization_id=org.id,
        name="Elección con Alternativa Cívica",
        timezone="America/La_Paz",
        registration_opens_at=now - timedelta(days=2),
        registration_closes_at=now + timedelta(days=5),
        voting_opens_at=now + timedelta(days=6),
        voting_closes_at=now + timedelta(days=7),
        status=ElectionStatus.REGISTRATION_OPEN,
        created_by=admin.id,
    )
    test_db.add(election)
    await test_db.commit()

    payload = {
        "election_id": str(election.id),
        "document_id": "8003005",
        "consent_accepted": False,
        "selfie_base64": None,
        "id_card_base64": None,
        "use_fallback_code": True,
    }

    res = await client.post("/ai/biometric/verify", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["verdict"] == "VERIFIED_BY_FALLBACK"
    assert data["confidence_band"] == "MANUAL"
    assert data["images_persisted"] is False
    assert data["ai_source"] == "CIVIC_FALLBACK"

    # Verificar registro en base de datos
    stmt = select(BiometricVerificationAudit).where(
        BiometricVerificationAudit.election_id == election.id
    )
    audit_rows = list((await test_db.execute(stmt)).scalars().all())
    assert len(audit_rows) >= 1
    assert audit_rows[-1].verification_channel == "ALTERNATIVE_CODE_VERIFICATION"
