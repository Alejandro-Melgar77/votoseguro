"""
Esquemas Pydantic para el módulo de Autenticación
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.db.models.organization import OrganizationType, OrganizationStatus
from app.db.models.user import UserRole, UserStatus


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID | None
    email: EmailStr
    full_name: str
    role: UserRole
    status: UserStatus
    failed_attempts: int
    locked_until: datetime | None
    last_login_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationBriefResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    org_type: OrganizationType
    status: OrganizationStatus
    contact_email: str

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    organization: OrganizationBriefResponse | None = None
