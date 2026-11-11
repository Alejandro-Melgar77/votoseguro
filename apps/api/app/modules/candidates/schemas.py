"""
Esquemas Pydantic para Gestión de Candidatos y Papeleta (S1-05)
"""
import uuid
from pydantic import BaseModel, ConfigDict, Field


class CandidateCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    party_or_front: str | None = Field(None, max_length=200)
    photo_url: str | None = None
    ballot_order: int | None = Field(None, ge=1)


class CandidateUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=200)
    party_or_front: str | None = Field(None, max_length=200)
    photo_url: str | None = None
    ballot_order: int | None = Field(None, ge=1)


class CandidateReorderRequest(BaseModel):
    ordered_candidate_ids: list[uuid.UUID] = Field(..., min_length=1)


class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    constituency_id: uuid.UUID
    name: str
    party_or_front: str | None
    photo_url: str | None
    ballot_order: int


class PhotoUploadResponse(BaseModel):
    photo_url: str
