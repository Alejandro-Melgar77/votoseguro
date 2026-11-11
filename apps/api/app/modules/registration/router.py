"""
Router API para Enlaces de Registro, Activación Pública y Congelamiento del Padrón (S1-08)
"""
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    TenantContext,
    get_tenant_context,
    get_time_provider,
    require_admin_general,
)
from app.core.exceptions import ConflictException, NotFoundException
from app.core.time import TimeProvider
from app.db.models.election import Election, ElectionStatus
from app.db.session import get_db_session
from app.modules.registration.schemas import (
    PublicRegistrationInfoResponse,
    PublicVoterActivationRequest,
    PublicVoterActivationResponse,
    RegistrationLinkCreate,
    RegistrationLinkResponse,
    RollHashFreezeResponse,
    SendInvitationsRequest,
    SendInvitationsResponse,
)
from app.modules.registration.service import RegistrationService

router = APIRouter(tags=["Registro y Activación de Votantes"])


@router.post(
    "/elections/{election_id}/registration-links",
    response_model=RegistrationLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_registration_link(
    election_id: uuid.UUID,
    payload: RegistrationLinkCreate,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """Crea un enlace público de registro por grupo o nodo (Exclusivo ADMIN_GENERAL)."""
    return await RegistrationService.create_registration_link(
        db=db,
        election_id=election_id,
        payload=payload,
        tenant=tenant,
        time_provider=time_provider,
    )


@router.get(
    "/elections/{election_id}/registration-links",
    response_model=list[RegistrationLinkResponse],
    status_code=status.HTTP_200_OK,
)
async def list_registration_links(
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Lista todos los enlaces de registro de la elección (ADMIN_GENERAL y ADMIN_SEGMENT)."""
    return await RegistrationService.list_registration_links(
        db=db,
        election_id=election_id,
        tenant=tenant,
    )


@router.post(
    "/elections/{election_id}/registration-links/{link_id}/revoke",
    status_code=status.HTTP_200_OK,
)
async def revoke_registration_link(
    election_id: uuid.UUID,
    link_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Revoca un enlace de registro activo (Exclusivo ADMIN_GENERAL)."""
    return await RegistrationService.revoke_registration_link(
        db=db,
        election_id=election_id,
        link_id=link_id,
        tenant=tenant,
    )


@router.post(
    "/elections/{election_id}/registration-links/send",
    response_model=SendInvitationsResponse,
    status_code=status.HTTP_200_OK,
)
async def send_registration_invitations(
    election_id: uuid.UUID,
    payload: SendInvitationsRequest,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """Prepara y envía invitaciones masivas de registro al segmento electoral."""
    return await RegistrationService.send_invitations(
        db=db,
        election_id=election_id,
        payload=payload,
        tenant=tenant,
        time_provider=time_provider,
    )


@router.post(
    "/elections/{election_id}/registration/close-now",
    response_model=RollHashFreezeResponse,
    status_code=status.HTTP_200_OK,
)
async def close_registration_and_freeze_roll(
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """
    Invariante #5: Cierra la fase de registro y congela el padrón con roll_hash determinista.
    Permite tanto pruebas directas como override administrativo.
    """
    from sqlalchemy import select
    stmt_el = select(Election).where(
        Election.id == election_id,
        Election.organization_id == tenant.organization_id,
    )
    election = (await db.execute(stmt_el)).scalar_one_or_none()
    if not election:
        raise NotFoundException("Elección no encontrada en su institución.")

    if election.status != ElectionStatus.REGISTRATION_OPEN:
        raise ConflictException(
            "Únicamente se puede congelar el padrón si la elección se encuentra en REGISTRATION_OPEN."
        )

    db_now = await time_provider.now(db)
    return await RegistrationService.compute_and_freeze_roll_hash(
        db=db,
        election=election,
        db_now=db_now,
        tenant=tenant,
    )


# =============================================================================
# Rutas Públicas (Sin autenticación institucional)
# =============================================================================

@router.get(
    "/register/{token}",
    response_model=PublicRegistrationInfoResponse,
    status_code=status.HTTP_200_OK,
)
async def get_public_registration_info(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """Obtiene los metadatos públicos de la elección y segmento para la página de activación."""
    return await RegistrationService.get_public_link_info(
        db=db,
        token=token,
        time_provider=time_provider,
    )


@router.post(
    "/register/{token}",
    response_model=PublicVoterActivationResponse,
    status_code=status.HTTP_200_OK,
)
async def activate_voter_publicly(
    token: str,
    payload: PublicVoterActivationRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """Activa a un votante empadronado que abre su enlace de registro."""
    return await RegistrationService.activate_voter_publicly(
        db=db,
        token=token,
        payload=payload,
        time_provider=time_provider,
    )
