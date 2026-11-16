"""
Esquemas Pydantic v2 para el Portal Público de Auditoría (S3-03 - RF-57).
Garantiza cero filtración de PII o sufragios individuales.
"""
import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PublicElectionSummary(BaseModel):
    election_id: uuid.UUID
    name: str
    organization_name: str
    status: str
    config_hash: Optional[str] = None
    roll_hash: Optional[str] = None
    merkle_root: Optional[str] = None
    voting_opens_at: datetime
    voting_closes_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScheduleChangePublicItem(BaseModel):
    id: uuid.UUID
    field_name: str
    old_value: str
    new_value: str
    reason: str
    changed_at: datetime


class ChainIntegrityStatus(BaseModel):
    total_items: int
    chain_valid: bool
    head_hash: str
    genesis_hash: Optional[str] = None


class ConstituencyResultPublic(BaseModel):
    constituency_id: uuid.UUID
    constituency_label: str
    ballots_aggregated: int
    suppressed_by_k_anonymity: bool
    results: Optional[dict[str, Any]] = None


class PublicAuditDossierResponse(BaseModel):
    election_id: uuid.UUID
    name: str
    organization_name: str
    status: str
    timezone: str
    k_anonymity: int
    encryption_scheme: str

    # Sellos Criptográficos
    config_hash: Optional[str] = None
    roll_hash: Optional[str] = None
    merkle_root: Optional[str] = None
    key_ceremony_hash: Optional[str] = None
    tally_ceremony_hash: Optional[str] = None
    paillier_public_n: Optional[str] = None
    paillier_public_key: Optional[str] = None
    paillier_public_key_truncated: Optional[str] = None
    shamir_threshold_k: int
    shamir_total_n: int
    key_ceremony_status: str

    # Cronograma
    voting_opens_at: datetime
    voting_closes_at: datetime
    schedule_changes: List[ScheduleChangePublicItem] = Field(default_factory=list)

    # Verificación en Vivo de Cadenas
    votes_integrity: ChainIntegrityStatus
    audit_integrity: ChainIntegrityStatus

    # Participación
    total_registered_voters: int
    total_votes_cast: int
    turnout_percentage: float

    # Resultados Públicos
    results_published: bool
    results: Optional[List[ConstituencyResultPublic]] = None
    results_notice: Optional[str] = None
