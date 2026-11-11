"""
Modelos ORM: Estructura Electoral (Grupos, Jerarquías, Nodos, Cargos y Candidatos)
"""
import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class BreakdownKind(str, enum.Enum):
    LEVEL = "LEVEL"
    FILTER = "FILTER"


class VoterGroup(Base):
    __tablename__ = "voter_group"
    __table_args__ = (
        UniqueConstraint("election_id", "code", name="uq_voter_group_election_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    election_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("election.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    voting_opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voting_closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relaciones
    election = relationship("Election", back_populates="groups")
    levels = relationship("HierarchyLevel", back_populates="group", cascade="all, delete-orphan")
    nodes = relationship("UnitNode", back_populates="group", cascade="all, delete-orphan")
    filters = relationship("FilterDefinition", back_populates="group", cascade="all, delete-orphan")
    contests = relationship("Contest", back_populates="group", cascade="all, delete-orphan")


class HierarchyLevel(Base):
    __tablename__ = "hierarchy_level"
    __table_args__ = (
        UniqueConstraint("group_id", "depth", name="uq_hierarchy_level_group_depth"),
        UniqueConstraint("group_id", "name", name="uq_hierarchy_level_group_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voter_group.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    # Relaciones
    group = relationship("VoterGroup", back_populates="levels")
    nodes = relationship("UnitNode", back_populates="level")


class UnitNode(Base):
    __tablename__ = "unit_node"
    __table_args__ = (
        UniqueConstraint("group_id", "code", name="uq_unit_node_group_code"),
        Index("ix_unit_node_path_pattern", "path", postgresql_using="btree"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voter_group.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hierarchy_level.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("unit_node.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relaciones
    group = relationship("VoterGroup", back_populates="nodes")
    level = relationship("HierarchyLevel", back_populates="nodes")
    parent = relationship("UnitNode", remote_side=[id], backref="children")


class FilterDefinition(Base):
    __tablename__ = "filter_definition"
    __table_args__ = (
        UniqueConstraint("group_id", "key", name="uq_filter_definition_group_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voter_group.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    allowed_values: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relaciones
    group = relationship("VoterGroup", back_populates="filters")


class Contest(Base):
    __tablename__ = "contest"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voter_group.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    scope_level_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hierarchy_level.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    allow_blank: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_null: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relaciones
    group = relationship("VoterGroup", back_populates="contests")
    scope_level = relationship("HierarchyLevel")
    constituencies = relationship("Constituency", back_populates="contest", cascade="all, delete-orphan")
    breakdowns = relationship("ContestBreakdown", back_populates="contest", cascade="all, delete-orphan")


class ContestBreakdown(Base):
    __tablename__ = "contest_breakdown"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contest.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[BreakdownKind] = mapped_column(
        Enum(BreakdownKind, name="breakdown_kind_enum"), nullable=False
    )
    level_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hierarchy_level.id", ondelete="CASCADE"), nullable=True
    )
    filter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("filter_definition.id", ondelete="CASCADE"), nullable=True
    )
    label: Mapped[str] = mapped_column(String(150), nullable=False)

    # Relaciones
    contest = relationship("Contest", back_populates="breakdowns")
    level = relationship("HierarchyLevel")
    filter = relationship("FilterDefinition")


class Constituency(Base):
    __tablename__ = "constituency"
    __table_args__ = (
        UniqueConstraint("contest_id", "node_id", name="uq_constituency_contest_node"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contest.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("unit_node.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relaciones
    contest = relationship("Contest", back_populates="constituencies")
    node = relationship("UnitNode")
    candidates = relationship("Candidate", back_populates="constituency", cascade="all, delete-orphan")


class Candidate(Base):
    __tablename__ = "candidate"
    __table_args__ = (
        UniqueConstraint("constituency_id", "ballot_order", name="uq_candidate_constituency_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    constituency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("constituency.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    party_or_front: Mapped[str | None] = mapped_column(String(200), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ballot_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relaciones
    constituency = relationship("Constituency", back_populates="candidates")
