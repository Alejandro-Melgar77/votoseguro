"""
Esquemas Pydantic para el módulo de Auditoría
"""
import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: int
    organization_id: uuid.UUID | None
    election_id: uuid.UUID | None
    actor_id: uuid.UUID | None
    actor_role: str
    action: str
    entity_type: str
    entity_id: str
    payload: dict[str, Any]
    ip_address: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
