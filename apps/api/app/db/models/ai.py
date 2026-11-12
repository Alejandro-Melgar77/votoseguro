"""
Modelos ORM para Inteligencia Artificial Local (IA-L1 y IA-L5):
- AnomalyAlert: Registro persistente de alertas de anomalías estadísticas de participación y explicación asistida.
- KbDocumentChunk: Base documental curada para el Asistente Electoral RAG.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class AnomalyAlert(Base):
    """
    Alertas estadísticas de participación explicadas por IA Local (IA-L1).
    Solo almacena métricas agregadas y jamás votos por candidato (Invariante #11 y #14).
    """
    __tablename__ = "anomaly_alert"

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
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voter_group.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("unit_node.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    anomaly_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(24), nullable=False, default="MEDIUM")
    metric_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    metrics_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ai_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    ai_suggested_checks: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    ai_source: Mapped[str] = mapped_column(String(40), nullable=False, default="DETERMINISTIC_FALLBACK")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="OPEN")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Relaciones
    election = relationship("Election")
    organization = relationship("Organization")
    group = relationship("VoterGroup")
    node = relationship("UnitNode")
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class KbDocumentChunk(Base):
    """
    Fragmentos de manuales oficiales de VotoSeguro para RAG Asistente (IA-L5).
    """
    __tablename__ = "kb_document_chunk"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    doc_slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    section_title: Mapped[str] = mapped_column(String(200), nullable=False)
    audience: Mapped[str] = mapped_column(String(32), nullable=False, default="VOTER")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
