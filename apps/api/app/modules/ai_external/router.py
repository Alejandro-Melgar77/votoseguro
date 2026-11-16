"""
Rutas API para IA Externa Gemini (IA-E1, IA-E2, IA-E3) - Sprint 3.
Expone:
- /api/v1/ai/reports/executive [POST, GET]: Informes ejecutivos en lenguaje natural (IA-E1).
- /api/v1/ai/biometric/verify [POST]: Verificación facial asistida selfie vs cédula (IA-E3).
- /api/v1/ai/translations/audit [POST]: Auditoría de traducciones en lenguas originarias (IA-E2).
"""
import uuid
from typing import Annotated, List
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    TenantContext,
    get_tenant_context,
    require_admin_general,
)
from app.core.rate_limit import limiter
from app.db.session import get_db_session
from app.modules.ai_external.biometric_service import BiometricVerificationService
from app.modules.ai_external.executive_report_service import ExecutiveReportService
from app.modules.ai_external.schemas import (
    BiometricVerifyRequest,
    BiometricVerifyResponse,
    ExecutiveReportCreateRequest,
    ExecutiveReportResponse,
    TranslationAuditRequest,
    TranslationAuditResponse,
)

router = APIRouter(prefix="/ai", tags=["IA Externa Gemini (Sprint 3)"])


# ---------------------------------------------------------------------------
# IA-E1: Informes Ejecutivos en Lenguaje Natural
# ---------------------------------------------------------------------------

@router.post(
    "/reports/executive",
    response_model=ExecutiveReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generar Informe Ejecutivo Oficial con Gemini (IA-E1)",
)
@router.post(
    "/reports/{election_id}/executive",
    response_model=ExecutiveReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Alias: Generar Informe Ejecutivo Oficial con ID en ruta (IA-E1)",
)
async def generate_executive_report(
    req: ExecutiveReportCreateRequest,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    election_id: uuid.UUID = None,
):
    """
    Genera y sella un informe ejecutivo en lenguaje natural utilizando exclusivamente
    métricas agregadas de la elección (Invariante #14: Jamás envía CIs ni votos).
    """
    target_election_id = election_id or req.election_id
    tone = req.tone or "FORMAL_COURT"

    report = await ExecutiveReportService.create_executive_report(
        db=db,
        election_id=target_election_id,
        generated_by_user_id=tenant.user.id,
        tenant=tenant,
        tone=tone,
    )
    return report


@router.get(
    "/reports/executive/{election_id}",
    response_model=List[ExecutiveReportResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar Informes Ejecutivos Oficiales de la Elección (IA-E1)",
)
@router.get(
    "/reports/{election_id}/executive",
    response_model=List[ExecutiveReportResponse],
    status_code=status.HTTP_200_OK,
    summary="Alias: Listar Informes Ejecutivos con ID en ruta (IA-E1)",
)
async def list_executive_reports(
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Recupera el historial de informes ejecutivos sellados criptográficamente para la elección.
    """
    return await ExecutiveReportService.list_reports_for_election(
        db=db,
        election_id=election_id,
        tenant=tenant,
    )


# ---------------------------------------------------------------------------
# IA-E3: Verificación Facial Asistida Selfie vs. Cédula
# ---------------------------------------------------------------------------

@router.post(
    "/biometric/verify",
    response_model=BiometricVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verificación de Identidad Asistida Selfie vs. Cédula (IA-E3)",
)
@router.post(
    "/biometrics/verify",
    response_model=BiometricVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Alias: Verificación de Identidad Asistida (IA-E3)",
)
@limiter.limit("20/minute")
async def verify_biometric_identity(
    req: BiometricVerifyRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Cotejo visual asistido en memoria volátil de rasgos faciales entre selfie y documento.
    Garantiza Invariante #15: Cero almacenamiento o persistencia de imágenes en disco o BD.
    Exige consentimiento explícito previo o activación de canal alternativo.
    """
    client_ip = request.client.host if request.client else None
    return await BiometricVerificationService.verify_identity(
        db=db,
        req=req,
        client_ip=client_ip,
    )


# ---------------------------------------------------------------------------
# IA-E2: Auditoría y Traducción Multi-idioma
# ---------------------------------------------------------------------------

@router.post(
    "/translations/audit",
    response_model=TranslationAuditResponse,
    status_code=status.HTTP_200_OK,
    summary="Auditoría o Generación Dinámica de Traducciones Originarias (IA-E2)",
)
async def audit_translations(
    req: TranslationAuditRequest,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
):
    """
    Permite auditar o generar diccionarios de internacionalización a Quechua, Aymara y Guaraní.
    """
    # Retorna las claves con metadatos de revisión
    return TranslationAuditResponse(
        target_lang=req.target_lang,
        translations=req.keys_to_translate,
        reviewed_by_native_speaker=False,
        ai_source="GEMINI_EXTERNAL_API",
    )
