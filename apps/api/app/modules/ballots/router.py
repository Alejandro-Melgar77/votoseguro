"""
Router API para Cabina de Votación, Papeleta Automática y Emisión Atómica (S1-09)
"""
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter

from app.core.dependencies import (
    TenantContext,
    VoterSessionContext,
    get_current_voter_session,
    get_tenant_context,
    get_time_provider,
    require_admin_general,
)
from app.core.time import TimeProvider
from app.db.session import get_db_session
from app.modules.ballots.schemas import (
    AutomaticBallotResponse,
    CastBallotReceiptResponse,
    CastBallotRequest,
    CredentialDispatchItem,
    ReceiptVerificationResponse,
    VoterLoginRequest,
    VoterLoginResponse,
)
from app.modules.ballots.service import BallotService

router = APIRouter(tags=["Cabina de Votación y Papeleta Oficial"])


# =============================================================================
# Rutas de Cabina Oficial de Votación (Votante)
# =============================================================================

@router.post(
    "/voter/login",
    response_model=VoterLoginResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("15/minute")
async def voter_login(
    request: Request,
    payload: VoterLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """Inicio de sesión en cabina de votación mediante CI y Credencial de un solo uso."""
    return await BallotService.voter_login(
        db=db,
        payload=payload,
        time_provider=time_provider,
    )


@router.get(
    "/ballot",
    response_model=AutomaticBallotResponse,
    status_code=status.HTTP_200_OK,
)
async def get_automatic_ballot(
    session_ctx: Annotated[VoterSessionContext, Depends(get_current_voter_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """
    Obtiene la papeleta electoral oficial estructurada automáticamente
    según el grupo y el nodo jerárquico del votante.
    """
    return await BallotService.get_automatic_ballot(
        db=db,
        session_ctx=session_ctx,
        time_provider=time_provider,
    )


@router.post(
    "/ballot/cast",
    response_model=CastBallotReceiptResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
async def cast_ballot_atomic(
    request: Request,
    payload: CastBallotRequest,
    session_ctx: Annotated[VoterSessionContext, Depends(get_current_voter_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """
    Emisión Atómica Ciega del Sufragio (Invariantes #6, #7, #8, #9, #13, #17).
    Registra todos los votos de la papeleta sin almacenar vínculo alguno con voter_id.
    """
    return await BallotService.cast_ballot_atomic(
        db=db,
        session_ctx=session_ctx,
        payload=payload,
        time_provider=time_provider,
    )


@router.get(
    "/receipts/{receipt_hash}",
    response_model=ReceiptVerificationResponse,
    status_code=status.HTTP_200_OK,
)
async def verify_receipt(
    receipt_hash: str,
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Verificación pública de comprobante de urna sin revelar las opciones votadas."""
    return await BallotService.verify_receipt(
        db=db,
        receipt_hash=receipt_hash,
    )


# =============================================================================
# Rutas de Gestión Administrativa de Votación y Credenciales
# =============================================================================

@router.post(
    "/elections/{election_id}/voting/open-now",
    status_code=status.HTTP_200_OK,
)
async def open_voting_now(
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """Abre formalmente la votación (VOTING_OPEN) y emite credenciales a los votantes ACTIVE."""
    return await BallotService.open_voting_now(
        db=db,
        election_id=election_id,
        tenant=tenant,
        time_provider=time_provider,
    )


@router.post(
    "/elections/{election_id}/voting/issue-credentials",
    status_code=status.HTTP_200_OK,
)
async def issue_credentials(
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """Emite de forma idempotente las credenciales a los votantes ACTIVE."""
    from app.db.models.election import Election
    from sqlalchemy import select
    from app.core.exceptions import NotFoundException

    stmt = select(Election).where(
        Election.id == election_id,
        Election.organization_id == tenant.organization_id,
    )
    election = (await db.execute(stmt)).scalar_one_or_none()
    if not election:
        raise NotFoundException("Elección no encontrada.")

    db_now = await time_provider.now(db)
    count = await BallotService.issue_credentials_for_election(db, election, db_now)
    await db.commit()
    return {"message": f"Se emitieron {count} nuevas credenciales.", "credentials_issued": count}


@router.get(
    "/elections/{election_id}/voting/credentials-dispatch",
    response_model=list[CredentialDispatchItem],
    status_code=status.HTTP_200_OK,
)
async def get_credentials_dispatch(
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Retorna la lista de credenciales emitidas para inspección y demo académica.
    Exclusivo para ADMIN_GENERAL y ADMIN_SEGMENT (restringido a su alcance).
    """
    return await BallotService.get_credentials_dispatch(
        db=db,
        election_id=election_id,
        tenant=tenant,
    )
