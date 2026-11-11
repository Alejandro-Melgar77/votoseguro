"""
Router API para consulta de bitácora de auditoría
"""
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import TenantContext, get_tenant_context
from app.db.session import get_db_session
from app.modules.audit.schemas import AuditLogResponse
from app.modules.audit.service import AuditService

router = APIRouter(prefix="/audit", tags=["Auditoría"])


@router.get("", response_model=list[AuditLogResponse])
async def get_audit_logs(
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    election_id: uuid.UUID | None = Query(None, description="Filtrar por ID de elección"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Consulta la bitácora inmutable de auditoría institucional."""
    return await AuditService.list_logs(
        db=db,
        organization_id=tenant.organization_id,
        election_id=election_id,
        limit=limit,
        offset=offset,
    )
