"""
Esquemas Pydantic para Cabina de Votación, Papeleta Automática y Emisión Atómica (S1-09)
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field

from app.db.models.voting import VoteChoiceType


class VoterLoginRequest(BaseModel):
    document_id: str = Field(min_length=3, max_length=64)
    credential_code: str = Field(min_length=6, max_length=128)
    election_id: uuid.UUID | None = None


class VoterSessionProfile(BaseModel):
    id: uuid.UUID
    document_id: str
    full_name: str
    group_id: uuid.UUID
    group_name: str
    node_id: uuid.UUID
    node_name: str
    node_path: str


class VoterElectionInfo(BaseModel):
    id: uuid.UUID
    name: str
    voting_closes_at: datetime


class VoterLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    voter: VoterSessionProfile
    election: VoterElectionInfo


class BallotCandidateDTO(BaseModel):
    id: uuid.UUID
    full_name: str
    ballot_number: int | None = None
    ballot_order: int
    party_affiliation: str | None = None
    party_color: str | None = None
    photo_url: str | None = None


class BallotContestSectionDTO(BaseModel):
    contest_id: uuid.UUID
    contest_name: str
    contest_code: str
    description: str | None = None
    display_order: int
    scope_level_id: uuid.UUID
    allow_blank: bool
    allow_null: bool
    constituency_id: uuid.UUID
    node_id: uuid.UUID
    node_name: str
    node_path: str
    candidates: list[BallotCandidateDTO]


class AutomaticBallotResponse(BaseModel):
    election_id: uuid.UUID
    election_name: str
    voter_profile: VoterSessionProfile
    contests: list[BallotContestSectionDTO]
    voting_closes_at: datetime


class BallotSelectionItem(BaseModel):
    contest_id: uuid.UUID
    constituency_id: uuid.UUID
    choice_type: VoteChoiceType
    candidate_id: uuid.UUID | None = None


class CastBallotRequest(BaseModel):
    selections: list[BallotSelectionItem]


class CastBallotReceiptResponse(BaseModel):
    receipt_hash: str
    election_id: uuid.UUID
    election_name: str
    cast_at_minute: datetime
    contests_count: int
    nonce: str
    status: str = "RECORDED_IN_BALLOT_BOX"


class ReceiptVerificationResponse(BaseModel):
    found: bool
    receipt_hash: str
    election_id: uuid.UUID | None = None
    cast_at_minute: datetime | None = None
    contests_recorded: int = 0
    status: str


class CredentialDispatchItem(BaseModel):
    voter_id: uuid.UUID
    document_id: str
    full_name: str
    group_name: str
    node_name: str
    node_path: str
    credential_code: str | None = None
    issued_at: datetime
    used: bool
    used_at: datetime | None = None
