"""
Modelos ORM: Bandeja de Notificaciones Despachadas (NotificationOutbox) - S2-09
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class NotificationOutbox(Base):
    """
    Bandeja persistente de auditoría y despacho de notificaciones a votantes.
    Registra avisos por cambios de cronograma, credenciales y alertas institucionales.
    """
    __tablename__ = "notification_outbox"

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
    schedule_change_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schedule_change.id", ondelete="SET NULL"),
        nullable=True,
    )
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(250), nullable=False)
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="STORED_DEMO_OUTBOX"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Relaciones
    organization = relationship("Organization")
    election = relationship("Election")
    schedule_change = relationship("ScheduleChange")
