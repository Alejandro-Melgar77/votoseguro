"""
Router API para Enlaces de Registro, Activación Pública y Congelamiento del Padrón (S1-08)
"""
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter

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
    RejectVoterRequest,
    RollHashFreezeResponse,
    SelfRegistrationInfoResponse,
    SelfRegistrationRequest,
    SelfRegistrationResponse,
    SendInvitationsRequest,
    SendInvitationsResponse,
)
from app.modules.voters.schemas import VoterResponse
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
@limiter.limit("20/minute")
async def activate_voter_publicly(
    request: Request,
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


# =============================================================================
# S2-10: Autoinscripción en Registro Abierto con Aprobación
# =============================================================================

@router.get(
    "/public/elections/{election_id}/self-registration-info",
    response_model=SelfRegistrationInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Información Pública para Formulario de Autoinscripción (S2-10)",
)
async def get_self_registration_info_endpoint(
    election_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Retorna los grupos y nodos válidos para la autoinscripción pública."""
    return await RegistrationService.get_self_registration_info(db, election_id)


@router.post(
    "/public/elections/{election_id}/self-register",
    response_model=SelfRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar Solicitud Pública de Autoinscripción (S2-10)",
)
@limiter.limit("20/minute")
async def self_register_endpoint(
    request: Request,
    election_id: uuid.UUID,
    payload: SelfRegistrationRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """
    S2-10: Registra la solicitud de un ciudadano en estado PENDING_APPROVAL
    cuando election.registration_mode == 'OPEN_WITH_APPROVAL'.
    """
    return await RegistrationService.self_register_voter(
        db=db,
        election_id=election_id,
        payload=payload,
        time_provider=time_provider,
    )


@router.get(
    "/elections/{election_id}/voters/pending-approval",
    response_model=list[VoterResponse],
    status_code=status.HTTP_200_OK,
    summary="Bandeja de Solicitudes de Autoinscripción Pendientes (S2-10)",
)
async def list_pending_approval_voters(
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Lista las solicitudes de autoinscripción en estado PENDING_APPROVAL."""
    voters = await RegistrationService.list_pending_voters(db, election_id)
    return [
        VoterResponse(
            id=v.id,
            organization_id=v.organization_id,
            election_id=v.election_id,
            group_id=v.group_id,
            group_name=v.group.name if v.group else None,
            node_id=v.node_id,
            node_name=v.node.name if v.node else None,
            node_path=v.node.path if v.node else None,
            document_id=v.document_id,
            full_name=v.full_name,
            email=v.email,
            phone=v.phone,
            attributes=v.attributes or {},
            status=v.status,
            blocked_reason=v.blocked_reason,
            rejection_reason=v.rejection_reason,
            invited_at=v.invited_at,
            activated_at=v.activated_at,
            created_at=v.created_at,
        )
        for v in voters
    ]


@router.post(
    "/elections/{election_id}/voters/{voter_id}/approve",
    response_model=VoterResponse,
    status_code=status.HTTP_200_OK,
    summary="Aprobar Autoinscripción de Votante (S2-10)",
)
async def approve_voter_endpoint(
    election_id: uuid.UUID,
    voter_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """Aprueba un votante en PENDING_APPROVAL pasándolo a ACTIVE."""
    voter = await RegistrationService.approve_voter(
        db=db,
        election_id=election_id,
        voter_id=voter_id,
        admin_user=tenant.user,
        time_provider=time_provider,
    )
    return VoterResponse(
        id=voter.id,
        organization_id=voter.organization_id,
        election_id=voter.election_id,
        group_id=voter.group_id,
        group_name=voter.group.name if voter.group else None,
        node_id=voter.node_id,
        node_name=voter.node.name if voter.node else None,
        node_path=voter.node.path if voter.node else None,
        document_id=voter.document_id,
        full_name=voter.full_name,
        email=voter.email,
        phone=voter.phone,
        attributes=voter.attributes or {},
        status=voter.status,
        blocked_reason=voter.blocked_reason,
        rejection_reason=voter.rejection_reason,
        invited_at=voter.invited_at,
        activated_at=voter.activated_at,
        created_at=voter.created_at,
    )


@router.post(
    "/elections/{election_id}/voters/{voter_id}/reject",
    response_model=VoterResponse,
    status_code=status.HTTP_200_OK,
    summary="Rechazar Autoinscripción de Votante (S2-10)",
)
async def reject_voter_endpoint(
    election_id: uuid.UUID,
    voter_id: uuid.UUID,
    payload: RejectVoterRequest,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """Rechaza un votante en PENDING_APPROVAL pasándolo a BLOCKED con motivo."""
    voter = await RegistrationService.reject_voter(
        db=db,
        election_id=election_id,
        voter_id=voter_id,
        reason=payload.reason,
        admin_user=tenant.user,
        time_provider=time_provider,
    )
    return VoterResponse(
        id=voter.id,
        organization_id=voter.organization_id,
        election_id=voter.election_id,
        group_id=voter.group_id,
        group_name=voter.group.name if voter.group else None,
        node_id=voter.node_id,
        node_name=voter.node.name if voter.node else None,
        node_path=voter.node.path if voter.node else None,
        document_id=voter.document_id,
        full_name=voter.full_name,
        email=voter.email,
        phone=voter.phone,
        attributes=voter.attributes or {},
        status=voter.status,
        blocked_reason=voter.blocked_reason,
        rejection_reason=voter.rejection_reason,
        invited_at=voter.invited_at,
        activated_at=voter.activated_at,
        created_at=voter.created_at,
    )
