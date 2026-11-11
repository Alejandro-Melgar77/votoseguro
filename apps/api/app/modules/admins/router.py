"""
Router API para Delegados de Solo Lectura (ADMIN_SEGMENT - S1-11)
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
from app.modules.admins.schemas import (
    AdminAssignmentResponse,
    AdminSegmentCreateRequest,
)
from app.modules.admins.service import AdminAssignmentService

router = APIRouter(tags=["Administradores Delegados"])


@router.post(
    "/elections/{election_id}/delegates",
    response_model=AdminAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_delegate(
    request: Request,
    election_id: uuid.UUID,
    payload: AdminSegmentCreateRequest,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """Asigna o crea un delegado de solo lectura (ADMIN_SEGMENT) acotado a un grupo o nodo."""
    client_ip = request.client.host if request.client else None
    return await AdminAssignmentService.create_delegated_admin(
        db=db,
        election_id=election_id,
        payload=payload,
        creator=tenant.user,
        time_provider=time_provider,
        client_ip=client_ip,
    )


@router.get(
    "/elections/{election_id}/delegates",
    response_model=list[AdminAssignmentResponse],
)
async def list_delegates(
    election_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Lista las asignaciones de delegados para una elección."""
    return await AdminAssignmentService.list_delegates(
        db=db,
        election_id=election_id,
        organization_id=tenant.organization_id,
    )


@router.delete(
    "/elections/{election_id}/delegates/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_delegate(
    request: Request,
    election_id: uuid.UUID,
    assignment_id: uuid.UUID,
    tenant: Annotated[TenantContext, Depends(require_admin_general)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Revoca el permiso de visualización a un delegado."""
    client_ip = request.client.host if request.client else None
    await AdminAssignmentService.revoke_delegate(
        db=db,
        election_id=election_id,
        assignment_id=assignment_id,
        revoker=tenant.user,
        client_ip=client_ip,
    )
