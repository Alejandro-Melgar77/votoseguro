"""
Router API para Escrutinio, Desgloses y k-Anonimato (S1-10)
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
from app.core.time import TimeProvider
from app.db.session import get_db_session
from app.modules.results.schemas import (
    CloseVotingRequest,
    ElectionResultsResponse,
    ParticipationMetricsResponse,
)
from app.modules.results.service import ResultsService

router = APIRouter(tags=["Resultados y Cómputo Oficial"])


@router.get(
    "/elections/{election_id}/participation",
    response_model=ParticipationMetricsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_election_participation(
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Retorna las métricas de participación ciudadana desglosadas por grupo y árbol nodal."""
    return await ResultsService.get_participation_metrics(
        db=db,
        election_id=election_id,
        tenant=tenant,
    )


@router.get(
    "/elections/{election_id}/results",
    response_model=ElectionResultsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_election_results(
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Invariante #11 y #12: Escrutinio oficial tras el cierre de votación.
    Bloqueado con HTTP 403 Forbidden antes de VOTING_CLOSED.
    Aplica k-anonimato suprimiendo el desglose en celdas con menos de k votos.
    """
    return await ResultsService.compute_election_results(
        db=db,
        election_id=election_id,
        tenant=tenant,
    )


@router.post(
    "/elections/{election_id}/voting/close-now",
    status_code=status.HTTP_200_OK,
)
async def close_voting_now(
    election_id: uuid.UUID,
    payload: CloseVotingRequest,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """
    Cierre formal de la votación (VOTING_CLOSED) para demostraciones o cierre manual.
    Exclusivo para ADMIN_GENERAL con motivo justificado.
    """
    return await ResultsService.close_voting_now(
        db=db,
        election_id=election_id,
        reason=payload.reason,
        tenant=tenant,
        time_provider=time_provider,
    )
