"""
Router API para la Suite de Inteligencia Artificial Local (IA-L1 a IA-L5).
Endpoints versionados bajo /api/v1/ai/
"""
import uuid
from typing import Annotated, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    TenantContext,
    get_current_user,
    get_tenant_context,
    require_admin_general,
)
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.rate_limit import limiter
from app.db.models.election import Election
from app.db.models.user import User, UserRole
from app.db.session import get_db_session
from app.modules.ai_local.service import AiLocalService
from app.ai.schemas import (
    AnomalyScanResponse,
    BatchDuplicateAdjudicationResponse,
    DuplicateAdjudicationSuggestion,
    IdCardExtractionRequest,
    IdCardExtractionResponse,
    RagAssistantRequest,
    RagAssistantResponse,
)

router = APIRouter(prefix="/ai", tags=["Inteligencia Artificial Local (LFM3-1.7B)"])


# ==========================================
# IA-L1: Anomalías Estadísticas de Participación
# ==========================================

@router.get("/anomalies/{election_id}", response_model=AnomalyScanResponse)
async def get_election_anomalies(
    election_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    simulate_if_clean: bool = Query(False, description="Incluye una anomalía sintética para prueba si no hay anomalías reales."),
):
    """
    IA-L1: Escanea métricas de participación agregadas (Invariante #11 y #14) y retorna anomalías detectadas.
    Accesible para ADMIN_GENERAL y ADMIN_SEGMENT de la organización.
    """
    election = await db.get(Election, election_id)
    if not election:
        raise NotFoundException(f"Elección no encontrada: {election_id}")

    if current_user.role != UserRole.PLATFORM_ADMIN and election.organization_id != current_user.organization_id:
        raise ForbiddenException("No tiene permisos para auditar elecciones de otra organización.")

    if current_user.role not in (UserRole.ADMIN_GENERAL, UserRole.ADMIN_SEGMENT, UserRole.PLATFORM_ADMIN):
        raise ForbiddenException("Acceso restringido a administradores electorales.")

    return await AiLocalService.get_or_scan_anomalies(
        db=db,
        election_id=election_id,
        simulate_if_clean=simulate_if_clean,
    )


@router.post("/anomalies/{election_id}/explain", response_model=AnomalyScanResponse)
async def explain_election_anomalies(
    election_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    simulate_if_clean: bool = Query(False, description="Incluye una anomalía sintética para prueba si no hay anomalías reales."),
):
    """
    IA-L1: Dispara el análisis y genera la explicación asistida en español con LFM3-1.7B (o fallback determinista).
    Accesible para ADMIN_GENERAL y ADMIN_SEGMENT.
    """
    election = await db.get(Election, election_id)
    if not election:
        raise NotFoundException(f"Elección no encontrada: {election_id}")

    if current_user.role != UserRole.PLATFORM_ADMIN and election.organization_id != current_user.organization_id:
        raise ForbiddenException("No tiene permisos para auditar elecciones de otra organización.")

    if current_user.role not in (UserRole.ADMIN_GENERAL, UserRole.ADMIN_SEGMENT, UserRole.PLATFORM_ADMIN):
        raise ForbiddenException("Acceso restringido a administradores electorales.")

    return await AiLocalService.get_or_scan_anomalies(
        db=db,
        election_id=election_id,
        simulate_if_clean=simulate_if_clean,
    )


# ==========================================
# IA-L2b: Segunda Opinión sobre Posibles Duplicados
# ==========================================

@router.post("/duplicates/{batch_id}/adjudicate", response_model=BatchDuplicateAdjudicationResponse)
async def adjudicate_duplicates_batch(
    batch_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    IA-L2b: Genera la segunda opinión de LFM3-1.7B para todos los duplicados del lote.
    Requiere ADMIN_GENERAL. Nunca fusiona ni altera votos de forma autónoma.
    """
    try:
        return await AiLocalService.adjudicate_duplicate_batch_by_id(db=db, batch_id=batch_id)
    except ValueError as err:
        raise NotFoundException(str(err))


@router.post("/duplicates/issues/{issue_id}/adjudicate", response_model=DuplicateAdjudicationSuggestion)
async def adjudicate_duplicate_single_issue(
    issue_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    IA-L2b: Genera la segunda opinión de LFM3-1.7B para un ImportIssue individual.
    Requiere ADMIN_GENERAL.
    """
    try:
        return await AiLocalService.adjudicate_duplicate_issue_by_id(db=db, issue_id=issue_id)
    except ValueError as err:
        raise NotFoundException(str(err))


# ==========================================
# IA-L3: Extracción OCR de Cédula de Identidad
# ==========================================

@router.post("/id-card/extract", response_model=IdCardExtractionResponse)
@limiter.limit("20/minute")
async def extract_id_card(
    request: Request,
    body: IdCardExtractionRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    IA-L3: Endpoint público protegido por rate limiting (20/min por IP).
    Invariante #15: Recibe únicamente texto plano; no persiste ni almacena imágenes.
    """
    election_uuid: Optional[uuid.UUID] = None
    if body.election_id:
        try:
            election_uuid = uuid.UUID(body.election_id)
        except ValueError:
            pass

    return await AiLocalService.extract_id_card_ocr(
        raw_ocr_text=body.raw_ocr_text,
        election_id=election_uuid,
        db=db,
    )


# ==========================================
# IA-L5: Asistente RAG sobre Manuales Oficiales
# ==========================================

@router.post("/assistant/ask", response_model=RagAssistantResponse)
@limiter.limit("30/minute")
async def ask_assistant(
    request: Request,
    body: RagAssistantRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    IA-L5: Asistente electoral oficial (RAG) acotado estrictamente a los manuales de VotoSeguro.
    Responde con base documental o indica 'no lo sé' derivando a soporte.
    """
    election_uuid: Optional[uuid.UUID] = None
    if body.election_id:
        try:
            election_uuid = uuid.UUID(body.election_id)
        except ValueError:
            pass

    return await AiLocalService.ask_rag_assistant(
        question=body.question,
        context_role=body.context_role,
        election_id=election_uuid,
        db=db,
    )


@router.get("/assistant/docs", response_model=List[dict[str, Any]])
async def list_official_docs():
    """
    Catálogo de los 12 fragmentos oficiales que conforman la base de conocimiento de VotoSeguro.
    """
    return AiLocalService.get_official_docs_catalog()
