"""
Router API para Elecciones y Panel de Control de Cronograma Electoral (S1-02)
"""
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    TenantContext,
    get_tenant_context,
    get_time_provider,
    require_admin_general,
)
from app.core.time import TimeProvider
from app.db.session import get_db_session
from app.modules.elections.publication_service import PublicationService
from app.modules.elections.schemas import (
    ElectionCreateRequest,
    ElectionResponse,
    ElectionUpdateRequest,
    ScheduleChangeResponse,
    ScheduleUpdateRequest,
)
from app.modules.elections.service import ElectionService

router = APIRouter(prefix="/elections", tags=["Elecciones y Cronograma"])


@router.post("", response_model=ElectionResponse, status_code=status.HTTP_201_CREATED)
async def create_election(
    request: Request,
    payload: ElectionCreateRequest,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """Crea una nueva elección en borrador (DRAFT) para la organización."""
    client_ip = request.client.host if request.client else None
    return await ElectionService.create_election(
        db=db,
        payload=payload,
        creator=tenant.user,
        time_provider=time_provider,
        client_ip=client_ip,
    )


@router.get("", response_model=list[ElectionResponse])
async def list_elections(
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Lista todas las elecciones pertenecientes a la organización activa."""
    return await ElectionService.list_elections(
        db=db, organization_id=tenant.organization_id
    )


@router.get("/{election_id}", response_model=ElectionResponse)
async def get_election(
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Obtiene los detalles de una elección específica."""
    return await ElectionService.get_election(
        db=db, election_id=election_id, organization_id=tenant.organization_id
    )


@router.patch("/{election_id}", response_model=ElectionResponse)
async def update_election_metadata(
    request: Request,
    election_id: uuid.UUID,
    payload: ElectionUpdateRequest,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """Actualiza metadatos generales de la elección (nombre, descripción, k-anonimato)."""
    client_ip = request.client.host if request.client else None
    return await ElectionService.update_election_meta(
        db=db,
        election_id=election_id,
        organization_id=tenant.organization_id,
        payload=payload,
        updater=tenant.user,
        time_provider=time_provider,
        client_ip=client_ip,
    )


@router.put("/{election_id}/schedule", response_model=ElectionResponse)
async def update_schedule(
    request: Request,
    election_id: uuid.UUID,
    payload: ScheduleUpdateRequest,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """
    Modifica el cronograma electoral bajo las reglas de la matriz de estados.
    Exige motivo justificativo obligatorio si la elección ya fue publicada.
    """
    client_ip = request.client.host if request.client else None
    return await ElectionService.update_schedule(
        db=db,
        election_id=election_id,
        organization_id=tenant.organization_id,
        payload=payload,
        updater=tenant.user,
        time_provider=time_provider,
        client_ip=client_ip,
    )


@router.post("/{election_id}/registration/open-now", response_model=ElectionResponse)
async def open_registration_now(
    request: Request,
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """
    Acción rápida 'Abrir registro ahora'.
    Fija registration_opens_at a la hora actual del servidor y pasa la elección a REGISTRATION_OPEN.
    """
    client_ip = request.client.host if request.client else None
    return await ElectionService.open_registration_now(
        db=db,
        election_id=election_id,
        organization_id=tenant.organization_id,
        actor=tenant.user,
        time_provider=time_provider,
        client_ip=client_ip,
    )


@router.get("/{election_id}/schedule/history", response_model=list[ScheduleChangeResponse])
async def get_schedule_history(
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Retorna la bitácora histórica inmutable de cambios de cronograma para esta elección."""
    return await ElectionService.list_schedule_history(
        db=db, election_id=election_id, organization_id=tenant.organization_id
    )


@router.post("/{election_id}/publish", response_model=ElectionResponse)
async def publish_election(
    request: Request,
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """
    Publica la elección previa validación de las 6 reglas de consistencia electoral.
    Emite el config_hash canónico SHA-256, congela la estructura y transiciona a SCHEDULED.
    """
    client_ip = request.client.host if request.client else None
    return await PublicationService.publish_election(
        db=db,
        election_id=election_id,
        actor=tenant.user,
        time_provider=time_provider,
        client_ip=client_ip,
    )

