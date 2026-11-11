"""
Modelos ORM: Organización y Solicitud Pública de Elección
"""
import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class OrganizationType(str, enum.Enum):
    UNIVERSITY = "UNIVERSITY"
    MUNICIPALITY = "MUNICIPALITY"
    NATIONAL = "NATIONAL"
    CORPORATE = "CORPORATE"
    COOPERATIVE = "COOPERATIVE"
    OTHER = "OTHER"


class OrganizationStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class ElectionRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Organization(Base):
    __tablename__ = "organization"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    org_type: Mapped[OrganizationType] = mapped_column(
        Enum(OrganizationType, name="org_type_enum"),
        nullable=False,
        default=OrganizationType.UNIVERSITY,
    )
    status: Mapped[OrganizationStatus] = mapped_column(
        Enum(OrganizationStatus, name="org_status_enum"),
        nullable=False,
        default=OrganizationStatus.ACTIVE,
    )
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
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
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    elections = relationship("Election", back_populates="organization", cascade="all, delete-orphan")


class ElectionRequest(Base):
    __tablename__ = "election_request"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_name: Mapped[str] = mapped_column(String(200), nullable=False)
    org_type: Mapped[OrganizationType] = mapped_column(
        Enum(OrganizationType, name="election_request_org_type_enum"),
        nullable=False,
        default=OrganizationType.UNIVERSITY,
    )
    requester_name: Mapped[str] = mapped_column(String(150), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    desired_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ElectionRequestStatus] = mapped_column(
        Enum(ElectionRequestStatus, name="election_request_status_enum"),
        nullable=False,
        default=ElectionRequestStatus.PENDING,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organization.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
