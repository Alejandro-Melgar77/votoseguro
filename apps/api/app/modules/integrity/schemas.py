"""
Esquemas Pydantic para Verificación Criptográfica de Integridad y Árbol de Merkle (S2-02, S2-05, S2-07)
"""
import uuid
from datetime import datetime
from pydantic import BaseModel


class VoteChainIntegrityResponse(BaseModel):
    valid: bool
    election_id: uuid.UUID
    genesis_hash: str
    head_hash: str | None = None
    total_blocks: int
    verified_blocks: int
    broken_at_index: int | None = None
    broken_vote_id: str | None = None
    error_detail: str | None = None
    checked_at: datetime


class AuditChainIntegrityResponse(BaseModel):
    valid: bool
    organization_id: uuid.UUID | None = None
    election_id: uuid.UUID | None = None
    genesis_hash: str
    head_hash: str | None = None
    total_entries: int
    verified_entries: int
    broken_at_index: int | None = None
    broken_entry_id: int | None = None
    error_detail: str | None = None
    checked_at: datetime


class MerkleProofStep(BaseModel):
    position: str  # "left" | "right"
    sibling_hash: str


class MerkleInclusionProofResponse(BaseModel):
    election_id: uuid.UUID
    document_id: str
    leaf_hash: str
    leaf_index: int
    total_active_voters: int
    merkle_root: str
    proof: list[MerkleProofStep]


class MerkleVerifyRequest(BaseModel):
    leaf_hash: str
    merkle_root: str
    proof: list[MerkleProofStep]


class MerkleVerifyResponse(BaseModel):
    valid: bool
    computed_root: str
    expected_root: str
