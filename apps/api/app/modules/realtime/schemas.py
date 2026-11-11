"""
Esquemas Pydantic para el Monitoreo en Tiempo Real y WebSockets (S2-04)
INVARIANTE #11: Prohibido incluir conteos por candidato o tendencias antes de VOTING_CLOSED.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel


class RegistrationMetricsDTO(BaseModel):
    imported: int = 0
    invited: int = 0
    active: int = 0
    blocked: int = 0
    pending_approval: int = 0
    total: int = 0
    activation_rate_pct: float = 0.0


class ParticipationMetricsDTO(BaseModel):
    total_eligible_active: int = 0
    total_voted: int = 0
    abstention_count: int = 0
    participation_rate_pct: float = 0.0


class SegmentBreakdownItemDTO(BaseModel):
    group_id: str
    group_name: str
    node_id: str
    node_name: str
    node_path: str
    active_voters: int
    votes_cast: int
    participation_pct: float


class HourlyVotesBucketDTO(BaseModel):
    hour_bucket_utc: str
    hour_label_local: str
    ballots_cast: int
    cumulative_ballots: int


class LiveDashboardSnapshot(BaseModel):
    election_id: uuid.UUID
    election_name: str
    status: str
    server_now_utc: datetime
    config_hash: str | None = None
    roll_hash: str | None = None
    merkle_root: str | None = None
    registration_metrics: RegistrationMetricsDTO
    participation_metrics: ParticipationMetricsDTO
    segment_breakdown: list[SegmentBreakdownItemDTO]
    hourly_votes_series: list[HourlyVotesBucketDTO]
