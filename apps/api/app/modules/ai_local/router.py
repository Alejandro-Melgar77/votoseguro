"""
Router API para la Suite de Inteligencia Artificial Local (IA-L1 a IA-L5).
Endpoints versionados bajo /api/v1/ai/
"""
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import (
    TenantContext,
    get_current_user,
    get_tenant_context,
    require_admin_general,
)
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.rate_limit import limiter
from app.db.models.ai import AiRuntimeConfig
from app.db.models.election import Election
from app.db.models.user import User, UserRole
from app.db.session import get_db_session
from app.modules.ai_local.service import AiLocalService
from app.ai.client import LocalLlmEngine
from app.ai.schemas import (
    AnomalyScanResponse,
    BatchDuplicateAdjudicationResponse,
    DuplicateAdjudicationSuggestion,
    IdCardExtractionRequest,
    IdCardExtractionResponse,
    RagAssistantRequest,
    RagAssistantResponse,
    AiNodeStatusResponse,
    AiNodeConfigUpdateRequest,
    AiNodeTestInferenceRequest,
    AiNodeTestInferenceResponse,
    AiNodePingRequest,
    AiNodePingResponse,
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


# ==========================================
# Sprint 2.5: Diagnóstico y Control del Túnel Estático (PC <-> Render)
# ==========================================

@router.get("/node/status", response_model=AiNodeStatusResponse)
async def get_ai_node_status(
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Diagnóstico en vivo del túnel estático hacia el Nodo Neuronal Local en la PC del usuario.
    Mide la latencia de red desde Render hasta la PC y lista los modelos cargados en Ollama.
    """
    active_cfg = await LocalLlmEngine.get_effective_config(db)
    llm_base_url = active_cfg["llm_base_url"]
    model_name = active_cfg["llm_model_name"]
    provider = active_cfg["provider"]
    strict_mode = active_cfg["strict_neural_mode"]

    ping_result = await LocalLlmEngine.ping_tunnel(llm_base_url=llm_base_url, timeout=10.0)
    is_online = ping_result.get("online", False)
    latency_ms = ping_result.get("latency_ms")
    available_models = ping_result.get("available_models", [])

    # Actualizar estado de último ping en BD
    try:
        stmt = select(AiRuntimeConfig).limit(1)
        res = await db.execute(stmt)
        cfg_record = res.scalar_one_or_none()
        if cfg_record:
            cfg_record.last_ping_status = "ONLINE" if is_online else "OFFLINE"
            cfg_record.last_ping_latency_ms = latency_ms
            cfg_record.last_ping_at = datetime.now(timezone.utc)
            await db.commit()
    except Exception as err:
        logger.debug(f"Error actualizando last_ping_status: {err}")

    if is_online:
        label = "🟢 NODO NEURONAL LOCAL CONECTADO (TÚNEL ESTÁTICO NGROK ACTIVO)"
    else:
        label = "🟠 NODO PC APAGADO (OPERANDO EN MODO DEGRADADO — EJECUTE INICIAR_IA_LOCAL.BAT)"

    return AiNodeStatusResponse(
        online=is_online,
        llm_base_url=llm_base_url,
        model_name=model_name,
        provider=provider,
        strict_neural_mode=strict_mode,
        latency_ms=latency_ms,
        available_models=available_models,
        status_label=label,
        last_ping_at=datetime.now(timezone.utc).isoformat(),
    )


@router.put("/node/config", response_model=AiNodeStatusResponse)
async def update_ai_node_config(
    body: AiNodeConfigUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Actualiza la configuración persistente del túnel (URL, modelo, modo estricto o proveedor).
    Restringido a PLATFORM_ADMIN o ADMIN_GENERAL.
    """
    if current_user.role not in (UserRole.PLATFORM_ADMIN, UserRole.ADMIN_GENERAL):
        raise ForbiddenException("Acceso restringido a administradores electorales o de plataforma.")

    stmt = select(AiRuntimeConfig).limit(1)
    res = await db.execute(stmt)
    cfg_record = res.scalar_one_or_none()

    if not cfg_record:
        cfg_record = AiRuntimeConfig(
            llm_base_url=body.llm_base_url or settings.LLM_BASE_URL,
            llm_model_name=body.model_name or settings.LLM_MODEL_NAME,
            provider=body.provider or "OLLAMA",
            strict_neural_mode=body.strict_neural_mode if body.strict_neural_mode is not None else False,
            timeout_seconds=body.timeout_seconds or 25.0,
        )
        db.add(cfg_record)
    else:
        if body.llm_base_url is not None:
            cfg_record.llm_base_url = body.llm_base_url.rstrip("/")
        if body.model_name is not None:
            cfg_record.llm_model_name = body.model_name
        if body.provider is not None:
            cfg_record.provider = body.provider
        if body.strict_neural_mode is not None:
            cfg_record.strict_neural_mode = body.strict_neural_mode
        if body.timeout_seconds is not None:
            cfg_record.timeout_seconds = body.timeout_seconds
        cfg_record.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(cfg_record)

    # Realizar ping con la nueva configuración
    ping_result = await LocalLlmEngine.ping_tunnel(llm_base_url=cfg_record.llm_base_url, timeout=5.0)
    is_online = ping_result.get("online", False)
    latency_ms = ping_result.get("latency_ms")

    return AiNodeStatusResponse(
        online=is_online,
        llm_base_url=cfg_record.llm_base_url,
        model_name=cfg_record.llm_model_name,
        provider=cfg_record.provider,
        strict_neural_mode=cfg_record.strict_neural_mode,
        latency_ms=latency_ms,
        available_models=ping_result.get("available_models", []),
        status_label="🟢 NODO CONECTADO" if is_online else "🟠 NODO OFFLINE",
        last_ping_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/node/test-inference", response_model=AiNodeTestInferenceResponse)
async def test_ai_node_inference(
    body: AiNodeTestInferenceRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Envía un prompt electoral en vivo a través del túnel estático hacia la PC del usuario
    y verifica la respuesta neuronal directa de votoseguro-lfm3 registrando la llamada en ai_call_log.
    Restringido a PLATFORM_ADMIN o ADMIN_GENERAL.
    """
    if current_user.role not in (UserRole.PLATFORM_ADMIN, UserRole.ADMIN_GENERAL):
        raise ForbiddenException("Acceso restringido a administradores electorales.")

    test_prompt = body.prompt or (
        "Analiza las siguientes métricas de participación de la urna electoral:\n"
        "Mesa M-Test-Live: participación registrada de 91.5% frente a media de 49.0% (z-score = 2.45, umbral 1.80)."
    )

    t0 = datetime.now(timezone.utc)
    try:
        from app.ai.schemas import AnomalyExplanationResponse
        res = await LocalLlmEngine.call_structured(
            prompt=test_prompt,
            schema_cls=AnomalyExplanationResponse,
            fallback_fn=lambda: AnomalyExplanationResponse(
                anomaly_id="TEST-FALLBACK",
                code="Z_SCORE_SPIKE",
                severity="HIGH",
                metrics_summary={"z_score": 2.45},
                explanation_es="Respuesta simulada generada por el fallback determinista local.",
                recommended_checks=["Verificar que el servicio local en la PC esté encendido con INICIAR_IA_LOCAL.bat"],
                requires_human_decision=True,
                ai_source="DETERMINISTIC_FALLBACK",
            ),
            system_instruction="Eres el auditor estadístico asistido de VotoSeguro. Responde estrictamente en JSON.",
            function_name="IA_NODE_TEST_INFERENCE",
            organization_id=current_user.organization_id,
            db=db,
            sanitized_summary="Prueba de inferencia neuronal en vivo hacia PC Local",
        )

        return AiNodeTestInferenceResponse(
            success=True,
            ai_source=getattr(res, "ai_source", "UNKNOWN"),
            model_name=getattr(res, "model_name", "votoseguro-lfm3"),
            latency_ms=float(getattr(res, "latency_ms", 0) or 0),
            raw_response=res.model_dump(),
            audit_logged=True,
        )
    except Exception as exc:
        return AiNodeTestInferenceResponse(
            success=False,
            ai_source="ERROR",
            model_name="NONE",
            latency_ms=0.0,
            raw_response={},
            audit_logged=False,
            error_message=str(exc),
        )


@router.post("/node/ping", response_model=AiNodePingResponse)
async def ping_from_local_node(
    body: Optional[AiNodePingRequest] = None,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    """
    Endpoint público (sin autenticación requerida) invocado por INICIAR_IA_LOCAL.bat,
    start_static_ai_tunnel.ps1 o por el frontend web para sincronizar la presencia del nodo.
    Persiste la URL estática de ngrok en ai_runtime_config en Supabase y ejecuta un ping de verificación.
    """
    req = body or AiNodePingRequest()
    now = datetime.now(timezone.utc)
    current_strict = False

    target_url = (req.llm_base_url or settings.LLM_BASE_URL).rstrip("/")
    target_model = req.model_name or settings.LLM_MODEL_NAME

    # 1. Asegurar persistencia y auto-curación en ai_runtime_config
    cfg = None
    try:
        stmt = select(AiRuntimeConfig).limit(1)
        res = await db.execute(stmt)
        cfg = res.scalar_one_or_none()
        if not cfg:
            cfg = AiRuntimeConfig(
                llm_base_url=target_url,
                llm_model_name=target_model,
                provider="OLLAMA",
                strict_neural_mode=False,
                timeout_seconds=25.0,
                last_ping_status=req.node_status or "ONLINE",
                last_ping_at=now,
            )
            db.add(cfg)
        else:
            cfg.llm_base_url = target_url
            cfg.llm_model_name = target_model
            cfg.last_ping_status = req.node_status or "ONLINE"
            cfg.last_ping_at = now
            cfg.updated_at = now
            current_strict = cfg.strict_neural_mode

        await db.commit()
        await db.refresh(cfg)
    except Exception as err:
        logger.error(f"[AI Node Ping] Error actualizando ai_runtime_config: {err}", exc_info=True)

    # 2. Hacer ping en vivo hacia el túnel estático
    ping_result = await LocalLlmEngine.ping_tunnel(llm_base_url=target_url, timeout=6.0)
    is_online = ping_result.get("online", False)
    latency_ms = ping_result.get("latency_ms")

    # 3. Guardar estado verificado
    if cfg:
        try:
            cfg.last_ping_status = "ONLINE" if is_online else "OFFLINE"
            if latency_ms is not None:
                cfg.last_ping_latency_ms = latency_ms
            await db.commit()
        except Exception:
            pass

    return AiNodePingResponse(
        acknowledged=True,
        online=is_online,
        llm_base_url=target_url,
        model_name=target_model,
        latency_ms=latency_ms,
        received_at=now.isoformat(),
        current_strict_mode=current_strict,
    )

