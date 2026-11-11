"""
Esquemas Pydantic para Estructura Electoral: Grupos, Jerarquías, Nodos, Filtros, Cargos y Circunscripciones (S1-03, S1-04)
"""
import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.structure import BreakdownKind


# --- Grupos de Votantes ---
class VoterGroupCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    voting_opens_at: datetime | None = None
    voting_closes_at: datetime | None = None


class VoterGroupUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=150)
    code: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None


class VoterGroupVotingWindowUpdate(BaseModel):
    voting_opens_at: datetime | None = None
    voting_closes_at: datetime | None = None


class VoterGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    election_id: uuid.UUID
    name: str
    code: str
    description: str | None
    voting_opens_at: datetime | None
    voting_closes_at: datetime | None
    created_at: datetime
    levels_count: int = 0
    nodes_count: int = 0
    contests_count: int = 0


# --- Niveles Jerárquicos ---
class HierarchyLevelCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)


class HierarchyLevelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    group_id: uuid.UUID
    depth: int
    name: str


# --- Nodos Unitarios (Árbol con Ruta Materializada) ---
class UnitNodeCreate(BaseModel):
    level_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    name: str = Field(..., min_length=2, max_length=200)
    code: str = Field(..., min_length=1, max_length=80)


class UnitNodeUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=200)
    code: str | None = Field(None, min_length=1, max_length=80)


class UnitNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    group_id: uuid.UUID
    level_id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    code: str
    path: str
    depth: int


class UnitNodeTreeNode(UnitNodeResponse):
    children: list["UnitNodeTreeNode"] = []


class NodeImportRowError(BaseModel):
    row: int
    code: str
    message: str


class NodeImportResult(BaseModel):
    total_rows: int
    created_nodes: int
    errors: list[NodeImportRowError]


# --- Filtros Dinámicos ---
class FilterDefinitionCreate(BaseModel):
    key: str = Field(..., min_length=2, max_length=64)
    label: str = Field(..., min_length=2, max_length=120)
    allowed_values: list[str] = Field(default_factory=list)
    is_required: bool = False


class FilterDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    group_id: uuid.UUID
    key: str
    label: str
    allowed_values: list[str]
    is_required: bool


# --- Cargos (Contests) y Desgloses ---
class ContestBreakdownConfig(BaseModel):
    kind: BreakdownKind
    level_id: uuid.UUID | None = None
    filter_id: uuid.UUID | None = None
    label: str = Field(..., min_length=2, max_length=150)


class ContestBreakdownResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contest_id: uuid.UUID
    kind: BreakdownKind
    level_id: uuid.UUID | None
    filter_id: uuid.UUID | None
    label: str


class ContestCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: str | None = None
    scope_level_id: uuid.UUID
    allow_blank: bool = True
    allow_null: bool = True
    display_order: int = 1
    breakdowns: list[ContestBreakdownConfig] = Field(default_factory=list)


class ContestUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=200)
    description: str | None = None
    scope_level_id: uuid.UUID | None = None
    allow_blank: bool | None = None
    allow_null: bool | None = None
    display_order: int | None = None


class CandidateBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    party_or_front: str | None
    photo_url: str | None
    ballot_order: int


class ConstituencyBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contest_id: uuid.UUID
    node_id: uuid.UUID
    node_name: str
    node_code: str
    node_path: str
    candidates: list[CandidateBrief] = []


class ContestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    group_id: uuid.UUID
    name: str
    description: str | None
    scope_level_id: uuid.UUID
    scope_level_name: str | None = None
    scope_level_depth: int | None = None
    allow_blank: bool
    allow_null: bool
    display_order: int
    constituencies_count: int = 0
    breakdowns: list[ContestBreakdownResponse] = []
