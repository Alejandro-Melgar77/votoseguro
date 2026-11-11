"""
Modelos ORM: Elección y Registro de Cambios de Cronograma (ScheduleChange)
"""
import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ElectionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    REGISTRATION_OPEN = "REGISTRATION_OPEN"
    REGISTRATION_CLOSED = "REGISTRATION_CLOSED"
    VOTING_OPEN = "VOTING_OPEN"
    VOTING_CLOSED = "VOTING_CLOSED"
    TALLIED = "TALLIED"
    CANCELLED = "CANCELLED"


class Election(Base):
    __tablename__ = "election"
    __table_args__ = (
        CheckConstraint(
            "registration_opens_at < registration_closes_at AND "
            "registration_closes_at <= voting_opens_at AND "
            "voting_opens_at < voting_closes_at",
            name="ck_election_schedule_order",
        ),
        CheckConstraint("k_anonymity >= 0", name="ck_election_k_non_negative"),
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
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="America/La_Paz")
    registration_opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registration_closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    voting_opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    voting_closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[ElectionStatus] = mapped_column(
        Enum(ElectionStatus, name="election_status_enum"),
        nullable=False,
        default=ElectionStatus.DRAFT,
    )
    k_anonymity: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    config_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    roll_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    registration_frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voting_closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relaciones
    organization = relationship("Organization", back_populates="elections")
    creator = relationship("User", foreign_keys=[created_by])
    schedule_changes = relationship("ScheduleChange", back_populates="election", cascade="all, delete-orphan")
    groups = relationship("VoterGroup", back_populates="election", cascade="all, delete-orphan")
    voters = relationship("Voter", back_populates="election", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="election", cascade="all, delete-orphan")


class ScheduleChange(Base):
    __tablename__ = "schedule_change"

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
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    new_value: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    election_status_at_change: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    changed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relaciones
    election = relationship("Election", back_populates="schedule_changes")
    author = relationship("User", foreign_keys=[changed_by])
