"""
Esquemas Pydantic para Bandeja de Notificaciones (S2-09)
"""
import uuid
from datetime import datetime
from pydantic import BaseModel


class NotificationOutboxItemResponse(BaseModel):
    id: uuid.UUID
    election_id: uuid.UUID
    recipient_email: str
    recipient_name: str
    subject: str
    body_text: str
    delivery_status: str
    created_at: datetime
