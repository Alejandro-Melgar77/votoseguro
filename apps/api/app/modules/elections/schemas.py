"""
Esquemas Pydantic para el módulo de Elecciones y Cronograma Electoral (S1-02)
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.election import ElectionStatus


@dataclass
class ScheduleDiff:
    field_name: str
    old_value: datetime
    new_value: datetime


class ElectionCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=250)
    description: str | None = None
    timezone: str = Field(default="America/La_Paz", min_length=2, max_length=64)
    registration_opens_at: datetime
    registration_closes_at: datetime
    voting_opens_at: datetime
    voting_closes_at: datetime
    k_anonymity: int = Field(default=5, ge=0)


class ElectionUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=3, max_length=250)
    description: str | None = None
    timezone: str | None = Field(None, min_length=2, max_length=64)
    k_anonymity: int | None = Field(None, ge=0)


class ScheduleUpdateRequest(BaseModel):
    registration_opens_at: datetime
    registration_closes_at: datetime
    voting_opens_at: datetime
    voting_closes_at: datetime
    reason: str | None = Field(None, description="Motivo obligatorio si la elección no está en DRAFT")


class ElectionResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: str | None
    timezone: str
    registration_opens_at: datetime
    registration_closes_at: datetime
    voting_opens_at: datetime
    voting_closes_at: datetime
    status: ElectionStatus
    k_anonymity: int
    config_hash: str | None
    roll_hash: str | None
    published_at: datetime | None
    registration_frozen_at: datetime | None
    voting_closed_at: datetime | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScheduleChangeResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    election_id: uuid.UUID
    field_name: str
    old_value: datetime
    new_value: datetime
    election_status_at_change: str
    reason: str
    changed_by: uuid.UUID
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)
