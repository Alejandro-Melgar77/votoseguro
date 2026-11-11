"""
Esquemas Pydantic para Padrón Electoral, Carga Masiva y Detección de Duplicados (S1-07, IA-L2a)
"""
import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.voter import VoterStatus


class VoterCreate(BaseModel):
    group_id: uuid.UUID
    node_id: uuid.UUID
    document_id: str = Field(..., min_length=3, max_length=64)
    full_name: str = Field(..., min_length=3, max_length=250)
    email: str | None = None
    phone: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class VoterUpdate(BaseModel):
    email: str | None = None
    phone: str | None = None
    attributes: dict[str, Any] | None = None
    status: VoterStatus | None = None
    blocked_reason: str | None = None


class VoterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    election_id: uuid.UUID
    group_id: uuid.UUID
    group_name: str | None = None
    node_id: uuid.UUID
    node_name: str | None = None
    node_path: str | None = None
    document_id: str
    full_name: str
    email: str | None
    phone: str | None
    attributes: dict[str, Any]
    status: VoterStatus
    blocked_reason: str | None
    rejection_reason: str | None = None
    invited_at: datetime | None
    activated_at: datetime | None
    created_at: datetime


class GroupSummaryItem(BaseModel):
    group_id: uuid.UUID
    group_name: str
    group_code: str
    total_voters: int
    imported_count: int
    invited_count: int
    active_count: int
    blocked_count: int


class NodeSummaryItem(BaseModel):
    node_id: uuid.UUID
    node_name: str
    node_code: str
    node_path: str
    depth: int
    total_voters: int
    active_voters: int


class RegistrationSummaryResponse(BaseModel):
    total_voters: int
    imported_count: int
    invited_count: int
    active_count: int
    blocked_count: int
    activation_percentage: float
    pending_duplicates_count: int
    by_group: list[GroupSummaryItem]
    by_node: list[NodeSummaryItem]


class ImportIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    batch_id: uuid.UUID
    row_number: int
    issue_type: str  # VALIDATION_ERROR, POSSIBLE_DUPLICATE
    document_id: str | None
    raw_full_name: str | None
    candidate_voter_id: uuid.UUID | None
    candidate_voter_name: str | None = None
    matched_voter_id: uuid.UUID | None
    matched_voter_name: str | None = None
    matched_voter_document: str | None = None
    similarity_score: float | None
    edit_distance: int | None
    resolution: str
    resolved_by: uuid.UUID | None = None
    resolved_at: datetime | None = None
    details: dict[str, Any]


class ImportBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    election_id: uuid.UUID
    uploaded_by: uuid.UUID
    filename: str
    total_rows: int
    valid_rows: int
    error_rows: int
    duplicate_warnings: int
    created_at: datetime


class DuplicateResolveRequest(BaseModel):
    action: str = Field(..., pattern="^(CONFIRM_DISTINCT|BLOCK_NEW|REMOVE_NEW)$")
    reason: str = Field(..., min_length=3)
