"""
Modelos ORM: Credencial de Votación, Participación y Voto (Sin voter_id - Invariante #9)
"""
import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class VoteChoiceType(str, enum.Enum):
    CANDIDATE = "CANDIDATE"
    BLANK = "BLANK"
    NULL = "NULL"


class VotingCredential(Base):
    __tablename__ = "voting_credential"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    election_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("election.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    voter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voter.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relaciones
    voter = relationship("Voter")
    election = relationship("Election")


class VoterParticipation(Base):
    __tablename__ = "voter_participation"
    __table_args__ = (
        UniqueConstraint("election_id", "voter_id", name="uq_voter_participation_election_voter"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    election_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("election.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    voter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voter.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voter_group.id", ondelete="RESTRICT"),
        nullable=False,
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("unit_node.id", ondelete="RESTRICT"),
        nullable=False,
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class Vote(Base):
    """
    Entidad de Voto Seguro.
    REGLA INVARIANTE #9: ESTA TABLA NO CONTIENE voter_id NI CLAVE FORÁNEA ALGUNA HACIA EL VOTANTE.
    EL ANONIMATO SE GARANTIZA POR DESVINCULACIÓN FÍSICA EN LA BASE DE DATOS.
    """
    __tablename__ = "vote"
    __table_args__ = (
        CheckConstraint(
            "(choice_type = 'CANDIDATE' AND candidate_id IS NOT NULL) OR "
            "(choice_type IN ('BLANK', 'NULL') AND candidate_id IS NULL)",
            name="ck_vote_candidate_consistency",
        ),
        Index("ix_vote_election_constituency", "election_id", "constituency_id"),
        Index("ix_vote_segment_path", "segment_path", postgresql_using="btree"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    election_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("election.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    constituency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("constituency.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    choice_type: Mapped[VoteChoiceType] = mapped_column(
        Enum(VoteChoiceType, name="vote_choice_type_enum"), nullable=False
    )
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate.id", ondelete="RESTRICT"),
        nullable=True,
    )
    encoded_payload: Mapped[str] = mapped_column(Text, nullable=False)
    segment_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    filters_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    nullifier: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    receipt_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vote_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relaciones
    election = relationship("Election", back_populates="votes")
    constituency = relationship("Constituency")
    candidate = relationship("Candidate")
