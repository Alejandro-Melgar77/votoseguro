"""
Modelos ORM: Padrón Electoral, Lotes de Importación y Enlaces de Registro
"""
import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    DateTime,
    Enum,
    Float,
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


class VoterStatus(str, enum.Enum):
    IMPORTED = "IMPORTED"
    INVITED = "INVITED"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    PENDING_APPROVAL = "PENDING_APPROVAL"


class LinkStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class Voter(Base):
    __tablename__ = "voter"
    __table_args__ = (
        UniqueConstraint("election_id", "document_id", name="uq_voter_election_document"),
        Index("ix_voter_full_name_trgm", "full_name", postgresql_using="gin", postgresql_ops={"full_name": "gin_trgm_ops"}),
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
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voter_group.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("unit_node.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[str] = mapped_column(String(64), nullable=False)
    full_name: Mapped[str] = mapped_column(String(250), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[VoterStatus] = mapped_column(
        Enum(VoterStatus, name="voter_status_enum"), nullable=False, default=VoterStatus.IMPORTED
    )
    invited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relaciones
    election = relationship("Election", back_populates="voters")
    group = relationship("VoterGroup")
    node = relationship("UnitNode")


class ImportBatch(Base):
    __tablename__ = "import_batch"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    election_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("election.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_warnings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relaciones
    issues = relationship("ImportIssue", back_populates="batch", cascade="all, delete-orphan")


class ImportIssue(Base):
    __tablename__ = "import_issue"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_batch.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    issue_type: Mapped[str] = mapped_column(String(40), nullable=False)  # VALIDATION_ERROR, POSSIBLE_DUPLICATE
    document_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_full_name: Mapped[str | None] = mapped_column(String(250), nullable=True)
    candidate_voter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("voter.id", ondelete="SET NULL"), nullable=True
    )
    matched_voter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("voter.id", ondelete="SET NULL"), nullable=True
    )
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    edit_distance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolution: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Relaciones
    batch = relationship("ImportBatch", back_populates="issues")
    candidate_voter = relationship("Voter", foreign_keys=[candidate_voter_id])
    matched_voter = relationship("Voter", foreign_keys=[matched_voter_id])
    resolver = relationship("User", foreign_keys=[resolved_by])


class RegistrationLink(Base):
    __tablename__ = "registration_link"

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
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voter_group.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("unit_node.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    raw_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    label: Mapped[str | None] = mapped_column(String(150), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uses_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[LinkStatus] = mapped_column(
        Enum(LinkStatus, name="link_status_enum"), nullable=False, default=LinkStatus.ACTIVE
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relaciones
    group = relationship("VoterGroup")
    node = relationship("UnitNode")
