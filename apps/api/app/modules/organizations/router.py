"""
Router API para Organizaciones y Solicitudes Electorales
"""
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_current_user,
    get_time_provider,
    require_platform_admin,
)
from app.core.rate_limit import limiter
from app.core.time import TimeProvider
from app.db.models.organization import ElectionRequestStatus
from app.db.models.user import User
from app.db.session import get_db_session
from app.modules.organizations.schemas import (
    ApproveElectionRequest,
    ElectionRequestCreate,
    ElectionRequestResponse,
    OrganizationCreateRequest,
    OrganizationResponse,
    RejectElectionRequest,
)
from app.modules.organizations.service import OrganizationService

router = APIRouter(tags=["Organizaciones y Plataforma"])


# Endpoints del Operador de Plataforma (PLATFORM_ADMIN)
@router.post(
    "/platform/organizations",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_organization(
    request: Request,
    payload: OrganizationCreateRequest,
    current_user: Annotated[User, Depends(require_platform_admin)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """Crea una nueva institución tenant y su primer usuario ADMIN_GENERAL."""
    client_ip = request.client.host if request.client else None
    return await OrganizationService.create_organization_with_admin(
        db=db,
        payload=payload,
        creator=current_user,
        time_provider=time_provider,
        client_ip=client_ip,
    )


@router.get(
    "/platform/organizations",
    response_model=list[OrganizationResponse],
)
async def list_organizations(
    current_user: Annotated[User, Depends(require_platform_admin)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Lista todas las instituciones creadas en la plataforma."""
    return await OrganizationService.list_organizations(db=db)


@router.post(
    "/platform/seed-demo",
    status_code=status.HTTP_200_OK,
)
async def trigger_seed_demo(
    current_user: Annotated[User, Depends(require_platform_admin)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Puebla de forma idempotente las instituciones de demostración (seed:demo)."""
    from app.db.seed_demo import run_seed_demo
    res = await run_seed_demo(session=db)
    return {
        "status": "success",
        "message": "Datos de demostración aprovisionados exitosamente.",
        "results": res,
    }


@router.get(
    "/platform/election-requests",
    response_model=list[ElectionRequestResponse],
)
async def list_election_requests(
    current_user: Annotated[User, Depends(require_platform_admin)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    status_filter: ElectionRequestStatus | None = Query(None, alias="status"),
):
    """Lista las solicitudes institucionales de elección registradas."""
    return await OrganizationService.list_election_requests(db=db, status_filter=status_filter)


@router.post(
    "/platform/election-requests/{request_id}/approve",
    response_model=OrganizationResponse,
)
async def approve_election_request(
    request: Request,
    request_id: uuid.UUID,
    payload: ApproveElectionRequest,
    current_user: Annotated[User, Depends(require_platform_admin)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """Aprueba una solicitud pública, creando la organización y su ADMIN_GENERAL."""
    client_ip = request.client.host if request.client else None
    return await OrganizationService.approve_election_request(
        db=db,
        request_id=request_id,
        payload=payload,
        reviewer=current_user,
        time_provider=time_provider,
        client_ip=client_ip,
    )


@router.post(
    "/platform/election-requests/{request_id}/reject",
    response_model=ElectionRequestResponse,
)
async def reject_election_request(
    request: Request,
    request_id: uuid.UUID,
    payload: RejectElectionRequest,
    current_user: Annotated[User, Depends(require_platform_admin)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """Rechaza una solicitud pública de elección con un motivo formal."""
    client_ip = request.client.host if request.client else None
    return await OrganizationService.reject_election_request(
        db=db,
        request_id=request_id,
        payload=payload,
        reviewer=current_user,
        time_provider=time_provider,
        client_ip=client_ip,
    )


# Endpoint Público para Solicitudes Electorales (S1-12)
@router.post(
    "/public/election-requests",
    response_model=ElectionRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def submit_public_election_request(
    request: Request,
    payload: ElectionRequestCreate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """Permite a cualquier institución solicitar la realización de un proceso electoral."""
    client_ip = request.client.host if request.client else None
    return await OrganizationService.create_public_election_request(
        db=db,
        payload=payload,
        time_provider=time_provider,
        client_ip=client_ip,
    )
