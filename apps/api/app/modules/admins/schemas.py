"""
Esquemas Pydantic para el módulo de Administradores Delegados (ADMIN_SEGMENT - S1-11)
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.modules.auth.schemas import UserResponse


class AdminSegmentCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=3, max_length=200)
    password: str = Field(..., min_length=8)
    group_id: uuid.UUID | None = None
    node_id: uuid.UUID | None = None


class AdminAssignmentResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    election_id: uuid.UUID
    group_id: uuid.UUID | None
    node_id: uuid.UUID | None
    permission: str
    created_at: datetime
    user: UserResponse | None = None

    model_config = ConfigDict(from_attributes=True)
