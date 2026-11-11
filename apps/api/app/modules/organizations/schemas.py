"""
Esquemas Pydantic para el módulo de Organizaciones y Solicitudes Electorales
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.db.models.organization import (
    ElectionRequestStatus,
    OrganizationStatus,
    OrganizationType,
)


class AdminUserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=3, max_length=200)
    password: str = Field(..., min_length=8)


class OrganizationCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    org_type: OrganizationType = OrganizationType.UNIVERSITY
    contact_email: EmailStr
    admin_user: AdminUserCreate


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    org_type: OrganizationType
    status: OrganizationStatus
    contact_email: EmailStr
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ElectionRequestCreate(BaseModel):
    organization_name: str = Field(..., min_length=3, max_length=200)
    org_type: OrganizationType = OrganizationType.UNIVERSITY
    requester_name: str = Field(..., min_length=3, max_length=150)
    contact_email: EmailStr
    contact_phone: str | None = None
    desired_date: datetime
    description: str | None = None


class ElectionRequestResponse(BaseModel):
    id: uuid.UUID
    organization_name: str
    org_type: OrganizationType
    requester_name: str
    contact_email: EmailStr
    contact_phone: str | None
    desired_date: datetime
    description: str | None
    status: ElectionRequestStatus
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    rejection_reason: str | None
    approved_organization_id: uuid.UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApproveElectionRequest(BaseModel):
    organization_slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    admin_password: str = Field(..., min_length=8)


class RejectElectionRequest(BaseModel):
    rejection_reason: str = Field(..., min_length=5)
