"""
Router API para Padrón Electoral, Carga Masiva y Detección de Duplicados (S1-07, IA-L2a)
"""
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    TenantContext,
    get_tenant_context,
    get_time_provider,
    require_admin_general,
)
from app.core.time import TimeProvider
from app.db.models.voter import VoterStatus
from app.db.session import get_db_session
from app.modules.voters.schemas import (
    DuplicateResolveRequest,
    ImportBatchResponse,
    ImportIssueResponse,
    RegistrationSummaryResponse,
    VoterCreate,
    VoterResponse,
    VoterUpdate,
)
from app.modules.voters.service import VoterService

router = APIRouter(tags=["Padrón Electoral y Registro"])


@router.get("/elections/{election_id}/registration/summary", response_model=RegistrationSummaryResponse)
async def get_registration_summary(
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Retorna resumen estadístico del padrón con conteos por estado, avance porcentual,
    desglose por grupo y por nodo, respetando el alcance territorial si es ADMIN_SEGMENT.
    """
    return await VoterService.get_summary(db=db, election_id=election_id, tenant=tenant)


@router.get("/elections/{election_id}/voters", response_model=list[VoterResponse])
async def list_voters(
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    group_id: uuid.UUID | None = None,
    node_id: uuid.UUID | None = None,
    status: VoterStatus | None = None,
    search: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista paginada de votantes empadronados, filtrable por grupo, nodo, estado y búsqueda por CI o nombre."""
    return await VoterService.list_voters(
        db=db,
        election_id=election_id,
        tenant=tenant,
        group_id=group_id,
        node_id=node_id,
        status=status,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.post("/elections/{election_id}/voters", response_model=VoterResponse, status_code=status.HTTP_201_CREATED)
async def create_voter(
    request: Request,
    election_id: uuid.UUID,
    payload: VoterCreate,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """Alta individual de un votante en el padrón con validación de profundidad de nodo y detector IA-L2a."""
    client_ip = request.client.host if request.client else None
    return await VoterService.create_voter(
        db=db,
        election_id=election_id,
        payload=payload,
        actor=tenant.user,
        time_provider=time_provider,
        client_ip=client_ip,
    )


@router.post("/elections/{election_id}/voters/import", response_model=ImportBatchResponse, status_code=status.HTTP_201_CREATED)
async def import_voters_csv(
    request: Request,
    election_id: uuid.UUID,
    file: UploadFile = File(...),
    tenant: Annotated[TenantContext, Depends(require_admin_general)] = None,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)] = None,
):
    """Carga masiva CSV del padrón con procesamiento tolerante a fallos y detector de duplicados (IA-L2a)."""
    client_ip = request.client.host if request.client else None
    content_bytes = await file.read()
    csv_text = content_bytes.decode("utf-8-sig", errors="replace")
    return await VoterService.import_voters_csv(
        db=db,
        election_id=election_id,
        csv_content=csv_text,
        filename=file.filename or "padron.csv",
        actor=tenant.user,
        time_provider=time_provider,
        client_ip=client_ip,
    )


@router.get("/elections/{election_id}/voters/import-batches", response_model=list[ImportBatchResponse])
async def list_import_batches(
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Lista los lotes de importación CSV procesados para una elección."""
    return await VoterService.list_import_batches(db=db, election_id=election_id)


@router.get("/elections/{election_id}/voters/import/{batch_id}/issues", response_model=list[ImportIssueResponse])
async def list_batch_issues(
    election_id: uuid.UUID,
    batch_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Retorna los errores de validación y advertencias de un lote de importación."""
    return await VoterService.list_batch_issues(db=db, batch_id=batch_id)


@router.get("/elections/{election_id}/voters/duplicates", response_model=list[ImportIssueResponse])
async def list_pending_duplicates(
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Retorna la lista de posibles duplicados pendientes de dictamen humano (IA-L2a)."""
    return await VoterService.list_duplicates(db=db, election_id=election_id)


@router.post("/elections/{election_id}/voters/duplicates/{issue_id}/resolve", response_model=ImportIssueResponse)
async def resolve_duplicate(
    request: Request,
    election_id: uuid.UUID,
    issue_id: uuid.UUID,
    payload: DuplicateResolveRequest,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """Dictamen humano sobre alerta de duplicidad: CONFIRM_DISTINCT, BLOCK_NEW o REMOVE_NEW."""
    client_ip = request.client.host if request.client else None
    return await VoterService.resolve_duplicate(
        db=db,
        election_id=election_id,
        issue_id=issue_id,
        payload=payload,
        actor=tenant.user,
        time_provider=time_provider,
        client_ip=client_ip,
    )


@router.patch("/elections/{election_id}/voters/{voter_id}", response_model=VoterResponse)
async def update_voter(
    request: Request,
    election_id: uuid.UUID,
    voter_id: uuid.UUID,
    payload: VoterUpdate,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Actualiza o bloquea a un votante mientras la fase de registro está abierta."""
    client_ip = request.client.host if request.client else None
    return await VoterService.update_voter(
        db=db,
        election_id=election_id,
        voter_id=voter_id,
        payload=payload,
        actor=tenant.user,
        client_ip=client_ip,
    )


@router.delete("/elections/{election_id}/voters/{voter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voter(
    request: Request,
    election_id: uuid.UUID,
    voter_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Retira/elimina a un votante del padrón mientras la fase de registro está abierta."""
    client_ip = request.client.host if request.client else None
    await VoterService.delete_voter(
        db=db, election_id=election_id, voter_id=voter_id, actor=tenant.user, client_ip=client_ip
    )
