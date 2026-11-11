"""
Rutas API para Exportaciones Oficiales en Excel y PDF (S2-08)
"""
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_time_provider, require_roles
from app.core.time import TimeProvider
from app.db.models.user import User, UserRole
from app.db.session import get_db_session
from app.modules.exports.service import ExportService

router = APIRouter(prefix="", tags=["Exportaciones Oficiales (Excel / PDF)"])


@router.get(
    "/elections/{election_id}/exports/results",
    summary="Exportar Acta Oficial de Resultados y Escrutinio (S2-08)",
)
async def export_results_endpoint(
    election_id: uuid.UUID,
    format: str = Query(default="xlsx", pattern="^(xlsx|pdf)$"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(
        require_roles(
            UserRole.PLATFORM_ADMIN,
            UserRole.ADMIN_GENERAL,
            UserRole.ADMIN_SEGMENT,
            UserRole.OBSERVER,
        )
    ),
    time_provider: TimeProvider = Depends(get_time_provider),
):
    """
    S2-08: Exporta el Acta Oficial de Resultados y Escrutinio en formato PDF o Excel (.xlsx).
    INVARIANTE #11: Solo permitido cuando election.status in [VOTING_CLOSED, TALLIED].
    INVARIANTE #12: Desgloses redactados estrictamente por k-anonimato (< k votos).
    """
    buffer, filename, media_type = await ExportService.export_results(
        db=db,
        election_id=election_id,
        user=current_user,
        time_provider=time_provider,
        export_format=format,
    )

    return Response(
        content=buffer.getvalue(),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/elections/{election_id}/exports/participation",
    summary="Exportar Reporte de Participación y Padrón (S2-08)",
)
async def export_participation_endpoint(
    election_id: uuid.UUID,
    format: str = Query(default="xlsx", pattern="^(xlsx|pdf)$"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(
        require_roles(
            UserRole.PLATFORM_ADMIN,
            UserRole.ADMIN_GENERAL,
            UserRole.ADMIN_SEGMENT,
            UserRole.OBSERVER,
        )
    ),
    time_provider: TimeProvider = Depends(get_time_provider),
):
    """
    S2-08: Exporta el reporte de empadronamiento, participación territorial y serie de votos por hora.
    """
    buffer, filename, media_type = await ExportService.export_participation(
        db=db,
        election_id=election_id,
        user=current_user,
        time_provider=time_provider,
        export_format=format,
    )

    return Response(
        content=buffer.getvalue(),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/elections/{election_id}/exports/audit",
    summary="Exportar Bitácora de Auditoría y Certificación de Integridad (S2-08)",
)
async def export_audit_endpoint(
    election_id: uuid.UUID,
    format: str = Query(default="xlsx", pattern="^(xlsx|pdf)$"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(
        require_roles(
            UserRole.PLATFORM_ADMIN,
            UserRole.ADMIN_GENERAL,
            UserRole.ADMIN_SEGMENT,
            UserRole.OBSERVER,
        )
    ),
    time_provider: TimeProvider = Depends(get_time_provider),
):
    """
    S2-08: Exporta la bitácora inmutable de auditoría con sus hashes encadenados,
    el historial de cambios de cronograma y la verificación de integridad.
    """
    buffer, filename, media_type = await ExportService.export_audit(
        db=db,
        election_id=election_id,
        user=current_user,
        time_provider=time_provider,
        export_format=format,
    )

    return Response(
        content=buffer.getvalue(),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
