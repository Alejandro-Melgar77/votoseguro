"""
Esquemas Pydantic para Enlaces de Registro, Activación y Padrón Congelado
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class RegistrationLinkCreate(BaseModel):
    group_id: uuid.UUID
    node_id: uuid.UUID | None = None
    label: str | None = Field(default=None, max_length=150)
    expires_at: datetime
    max_uses: int | None = Field(default=None, ge=1)


class RegistrationLinkResponse(BaseModel):
    id: uuid.UUID
    election_id: uuid.UUID
    group_id: uuid.UUID
    node_id: uuid.UUID | None = None
    group_name: str | None = None
    node_name: str | None = None
    node_path: str | None = None
    label: str | None = None
    token_hash: str
    raw_token: str | None = None
    registration_url: str
    expires_at: datetime
    max_uses: int | None = None
    uses_count: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SendInvitationsRequest(BaseModel):
    group_id: uuid.UUID
    node_id: uuid.UUID | None = None
    registration_link_id: uuid.UUID | None = None


class SendInvitationsResponse(BaseModel):
    invited_count: int
    registration_url: str
    message: str


class PublicRegistrationInfoResponse(BaseModel):
    organization_name: str
    election_id: uuid.UUID
    election_name: str
    group_id: uuid.UUID
    group_name: str
    node_id: uuid.UUID | None = None
    node_name: str | None = None
    node_path: str | None = None
    registration_closes_at: datetime
    link_expires_at: datetime
    is_valid: bool


class PublicVoterActivationRequest(BaseModel):
    document_id: str = Field(min_length=3, max_length=64)
    email: str | None = None
    phone: str | None = None


class PublicVoterActivationResponse(BaseModel):
    success: bool
    message: str
    voter_id: uuid.UUID
    document_id: str
    full_name: str
    group_name: str
    node_name: str
    node_path: str
    status: str
    activated_at: datetime


class RollHashFreezeResponse(BaseModel):
    election_id: uuid.UUID
    roll_hash: str
    merkle_root: str | None = None
    active_voters_count: int
    registration_frozen_at: datetime
    status: str


# S2-10: Autoinscripción con Aprobación
class SelfRegistrationNodeDTO(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    path: str
    depth: int


class SelfRegistrationGroupDTO(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    nodes: list[SelfRegistrationNodeDTO]


class SelfRegistrationInfoResponse(BaseModel):
    election_id: uuid.UUID
    election_name: str
    registration_mode: str
    status: str
    is_open: bool
    groups: list[SelfRegistrationGroupDTO]
    filter_definitions: list[dict] = []


class SelfRegistrationRequest(BaseModel):
    document_id: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    group_id: uuid.UUID
    node_id: uuid.UUID
    attributes: dict = {}


class SelfRegistrationResponse(BaseModel):
    success: bool
    message: str
    voter_id: uuid.UUID
    document_id: str
    full_name: str
    status: str


class RejectVoterRequest(BaseModel):
    reason: str

