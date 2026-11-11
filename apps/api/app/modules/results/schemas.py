"""
Esquemas Pydantic para Escrutinio, Desgloses Jerárquicos y k-Anonimato (S1-10)
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class CloseVotingRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=255)


class CandidateResultItem(BaseModel):
    candidate_id: uuid.UUID
    full_name: str
    ballot_number: int | None = None
    ballot_order: int
    party_affiliation: str | None = None
    party_color: str | None = None
    photo_url: str | None = None
    votes_count: int | None = None
    percentage: float | None = None


class BreakdownCellResult(BaseModel):
    cell_id: str
    cell_name: str
    cell_code: str | None = None
    cell_path: str | None = None
    total_votes: int
    redacted_by_k_anonymity: bool
    k_threshold: int
    k_anonymity_message: str | None = None
    candidates: list[CandidateResultItem] | None = None
    blank_count: int | None = None
    null_count: int | None = None


class ContestBreakdownResult(BaseModel):
    breakdown_id: uuid.UUID
    kind: str  # LEVEL | FILTER
    label: str | None = None
    level_id: uuid.UUID | None = None
    level_name: str | None = None
    filter_id: uuid.UUID | None = None
    filter_key: str | None = None
    cells: list[BreakdownCellResult]


class ConstituencyResult(BaseModel):
    constituency_id: uuid.UUID
    node_id: uuid.UUID
    node_name: str
    node_code: str
    node_path: str
    total_cast: int
    candidates_total: int
    blank_count: int
    null_count: int
    exact_match_verified: bool
    candidates: list[CandidateResultItem]
    breakdowns: list[ContestBreakdownResult]


class ContestResult(BaseModel):
    contest_id: uuid.UUID
    contest_name: str
    contest_code: str
    description: str | None = None
    scope_level_id: uuid.UUID
    scope_level_name: str
    allow_blank: bool
    allow_null: bool
    constituencies: list[ConstituencyResult]


class GroupResult(BaseModel):
    group_id: uuid.UUID
    group_name: str
    group_code: str
    contests: list[ContestResult]


class ElectionResultsResponse(BaseModel):
    election_id: uuid.UUID
    election_name: str
    status: str
    timezone: str
    k_anonymity: int
    config_hash: str | None = None
    roll_hash: str | None = None
    voting_closed_at: datetime | None = None
    groups: list[GroupResult]


class NodeParticipationItem(BaseModel):
    node_id: uuid.UUID
    node_name: str
    node_code: str
    node_path: str
    depth: int
    active_voters: int
    voted_count: int
    participation_rate_pct: float


class GroupParticipationItem(BaseModel):
    group_id: uuid.UUID
    group_name: str
    group_code: str
    active_voters: int
    voted_count: int
    participation_rate_pct: float
    nodes: list[NodeParticipationItem]


class ParticipationMetricsResponse(BaseModel):
    election_id: uuid.UUID
    election_name: str
    total_active_voters: int
    total_voted: int
    participation_rate_pct: float
    by_group: list[GroupParticipationItem]
