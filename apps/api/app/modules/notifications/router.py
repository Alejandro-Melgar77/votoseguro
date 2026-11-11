"""
Rutas API para Consulta de Bandeja de Notificaciones (S2-09)
"""
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_roles
from app.db.models.user import User, UserRole
from app.db.session import get_db_session
from app.modules.notifications.schemas import NotificationOutboxItemResponse
from app.modules.notifications.service import NotificationService

router = APIRouter(prefix="", tags=["Notificaciones Electorales (S2-09)"])


@router.get(
    "/elections/{election_id}/notifications/outbox",
    response_model=list[NotificationOutboxItemResponse],
    summary="Consultar Bandeja de Notificaciones Despachadas (S2-09)",
)
async def get_notification_outbox(
    election_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(
        require_roles(
            UserRole.PLATFORM_ADMIN,
            UserRole.ADMIN_GENERAL,
            UserRole.ADMIN_SEGMENT,
            UserRole.OBSERVER,
        )
    ),
):
    """
    S2-09: Consulta el historial de notificaciones emitidas por cambios de cronograma
    o avisos solemnes a los electores de la elección.
    """
    entries = await NotificationService.list_outbox(
        db=db,
        election_id=election_id,
        limit=limit,
        offset=offset,
    )
    return [
        NotificationOutboxItemResponse(
            id=e.id,
            election_id=e.election_id,
            recipient_email=e.recipient_email,
            recipient_name=e.recipient_name,
            subject=e.subject,
            body_text=e.body_text,
            delivery_status=e.delivery_status,
            created_at=e.created_at,
        )
        for e in entries
    ]
