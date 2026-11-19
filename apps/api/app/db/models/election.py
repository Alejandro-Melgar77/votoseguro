"""
Modelos ORM: Elección, Registro de Cambios de Cronograma (ScheduleChange)
y Entidades Criptográficas del Sprint 3 (ElectoralTrusteeShare, HomomorphicTallyCell, ExecutiveReport, BiometricVerificationAudit)
"""
import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
    registration_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="LINK_ONLY"
    )
    k_anonymity: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    config_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    roll_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    merkle_root: Mapped[str | None] = mapped_column(String(64), nullable=True)
    votes_chain_head: Mapped[str | None] = mapped_column(String(64), nullable=True)
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

    # Extensiones Criptográficas y de Seguridad (Sprint 3)
    encryption_scheme: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PAILLIER_HOMOMORPHIC"
    )
    paillier_public_n: Mapped[str | None] = mapped_column(Text, nullable=True)
    paillier_public_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    paillier_key_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1024)
    shamir_threshold_k: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    shamir_total_n: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    shamir_prime_modulus: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_ceremony_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tally_ceremony_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    biometric_verification_mode: Mapped[str] = mapped_column(
        String(24), nullable=False, default="OPTIONAL"
    )

    # Relaciones
    organization = relationship("Organization", back_populates="elections")
    creator = relationship("User", foreign_keys=[created_by])
    schedule_changes = relationship("ScheduleChange", back_populates="election", cascade="all, delete-orphan")
    groups = relationship("VoterGroup", back_populates="election", cascade="all, delete-orphan")
    voters = relationship("Voter", back_populates="election", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="election", cascade="all, delete-orphan")
    trustee_shares = relationship("ElectoralTrusteeShare", back_populates="election", cascade="all, delete-orphan")
    tally_cells = relationship("HomomorphicTallyCell", back_populates="election", cascade="all, delete-orphan")
    executive_reports = relationship("ExecutiveReport", back_populates="election", cascade="all, delete-orphan")
    biometric_audits = relationship("BiometricVerificationAudit", back_populates="election", cascade="all, delete-orphan")


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


class ElectoralTrusteeShare(Base):
    """
    S3-02: Custodia y Compromiso Criptográfico de Fragmentos de Shamir (k de n).
    Registra a los vocales o autoridades de la Corte Electoral y el hash de compromiso
    de su fragmento privado para la apertura oficial del escrutinio.
    """
    __tablename__ = "electoral_trustee_share"
    __table_args__ = (
        UniqueConstraint("election_id", "share_index", name="uq_trustee_share_election_index"),
        CheckConstraint("demo_share_token IS NULL", name="ck_trustee_no_persisted_secret"),
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
    share_index: Mapped[int] = mapped_column(Integer, nullable=False)
    trustee_name: Mapped[str] = mapped_column(String(150), nullable=False)
    trustee_email: Mapped[str] = mapped_column(String(255), nullable=False)
    commitment_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    demo_share_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_for_tally: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relaciones
    election = relationship("Election", back_populates="trustee_shares")


class HomomorphicTallyCell(Base):
    """
    S3-01: Celdas de Suma Cifrada Homomórfica y Descifrado por Quórum.
    Almacena los acumuladores multiplicados E(m1) * E(m2) % n^2 para cada circunscripción
    y desglose jerárquico/filtro, manteniendo el secreto hasta la apertura con Shamir.
    """
    __tablename__ = "homomorphic_tally_cell"
    __table_args__ = (
        UniqueConstraint(
            "constituency_id", "cell_scope_type", "cell_key",
            name="uq_tally_cell_constituency_scope_key",
        ),
        Index("ix_tally_cell_election", "election_id"),
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
    contest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contest.id", ondelete="CASCADE"),
        nullable=False,
    )
    constituency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("constituency.id", ondelete="CASCADE"),
        nullable=False,
    )
    cell_scope_type: Mapped[str] = mapped_column(
        String(24), nullable=False
    )  # 'CONSTITUENCY_TOTAL', 'LEVEL_BREAKDOWN', 'FILTER_BREAKDOWN'
    breakdown_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contest_breakdown.id", ondelete="CASCADE"),
        nullable=True,
    )
    cell_key: Mapped[str] = mapped_column(String(512), nullable=False)
    cell_label: Mapped[str] = mapped_column(String(250), nullable=False)
    ballots_aggregated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    option_order_keys: Mapped[list] = mapped_column(JSONB, nullable=False)
    aggregated_ciphertexts: Mapped[list] = mapped_column(JSONB, nullable=False)
    decrypted_counts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    suppressed_by_k_anonymity: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cell_proof_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relaciones
    election = relationship("Election", back_populates="tally_cells")
    contest = relationship("Contest")
    constituency = relationship("Constituency")


class ExecutiveReport(Base):
    """
    IA-E1: Informes Ejecutivos Asistidos por Gemini API o Fallback Determinista.
    Garantiza el cumplimiento estricto de la Invariante #14: únicamente almacena
    y procesa métricas consolidadas libres de datos personales o votos individuales.
    """
    __tablename__ = "executive_report"

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
    generated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="es")
    model_used: Mapped[str] = mapped_column(String(80), nullable=False)
    ai_source: Mapped[str] = mapped_column(String(40), nullable=False)
    aggregated_input_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    key_highlights: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    integrity_certification: Mapped[str] = mapped_column(Text, nullable=False)
    recommendations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    report_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relaciones
    election = relationship("Election", back_populates="executive_reports")
    author = relationship("User", foreign_keys=[generated_by])


class BiometricVerificationAudit(Base):
    """
    IA-E3: Auditoría de Verificación Biométrica sin Almacenamiento de Imágenes.
    Invariante #15: Restricción check a nivel de motor de BD para garantizar
    que jamás se persisten fotos de selfie ni cédula de identidad.
    """
    __tablename__ = "biometric_verification_audit"
    __table_args__ = (
        CheckConstraint("images_persisted = false", name="chk_zero_biometric_image_persistence"),
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
    voter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voter.id", ondelete="SET NULL"),
        nullable=True,
    )
    document_id: Mapped[str] = mapped_column(String(64), nullable=False)
    explicit_consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False)
    verification_channel: Mapped[str] = mapped_column(String(32), nullable=False)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence_band: Mapped[str] = mapped_column(String(24), nullable=False)
    explanation_es: Mapped[str] = mapped_column(Text, nullable=False)
    images_persisted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ai_source: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relaciones
    election = relationship("Election", back_populates="biometric_audits")
