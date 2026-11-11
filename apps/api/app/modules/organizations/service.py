"""
Servicio para Gestión de Organizaciones y Solicitudes Públicas de Elección
"""
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import get_password_hash
from app.core.time import TimeProvider
from app.db.models.organization import (
    ElectionRequest,
    ElectionRequestStatus,
    Organization,
    OrganizationStatus,
)
from app.db.models.user import User, UserRole, UserStatus
from app.modules.audit.service import AuditService
from app.modules.organizations.schemas import (
    ApproveElectionRequest,
    ElectionRequestCreate,
    OrganizationCreateRequest,
    RejectElectionRequest,
)


class OrganizationService:
    @staticmethod
    async def create_organization_with_admin(
        db: AsyncSession,
        payload: OrganizationCreateRequest,
        creator: User,
        time_provider: TimeProvider,
        client_ip: str | None = None,
    ) -> Organization:
        db_now = await time_provider.now(db)

        # Verificar unicidad de slug
        stmt_slug = select(Organization).where(Organization.slug == payload.slug)
        existing_org = (await db.execute(stmt_slug)).scalar_one_or_none()
        if existing_org:
            raise ConflictException(f"El identificador institucional '{payload.slug}' ya está en uso.")

        # Verificar unicidad de email de admin
        stmt_user = select(User).where(User.email.ilike(payload.admin_user.email.strip()))
        existing_user = (await db.execute(stmt_user)).scalar_one_or_none()
        if existing_user:
            raise ConflictException(f"El correo electrónico '{payload.admin_user.email}' ya pertenece a otro usuario.")

        org = Organization(
            name=payload.name,
            slug=payload.slug,
            org_type=payload.org_type,
            status=OrganizationStatus.ACTIVE,
            contact_email=payload.contact_email,
            created_at=db_now,
            updated_at=db_now,
        )
        db.add(org)
        await db.flush()

        admin_user = User(
            organization_id=org.id,
            email=payload.admin_user.email.strip().lower(),
            full_name=payload.admin_user.full_name.strip(),
            password_hash=get_password_hash(payload.admin_user.password),
            role=UserRole.ADMIN_GENERAL,
            status=UserStatus.ACTIVE,
            created_at=db_now,
        )
        db.add(admin_user)
        await db.flush()

        await AuditService.log_event(
            db=db,
            action="ORGANIZATION_CREATED",
            entity_type="organization",
            entity_id=str(org.id),
            actor_role=creator.role.value,
            actor_id=creator.id,
            organization_id=org.id,
            payload={"name": org.name, "slug": org.slug, "admin_email": admin_user.email},
            ip_address=client_ip,
        )
        await db.commit()
        await db.refresh(org)
        return org

    @staticmethod
    async def list_organizations(db: AsyncSession) -> list[Organization]:
        stmt = select(Organization).order_by(Organization.name.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create_public_election_request(
        db: AsyncSession,
        payload: ElectionRequestCreate,
        time_provider: TimeProvider,
        client_ip: str | None = None,
    ) -> ElectionRequest:
        db_now = await time_provider.now(db)
        request_obj = ElectionRequest(
            organization_name=payload.organization_name.strip(),
            org_type=payload.org_type,
            requester_name=payload.requester_name.strip(),
            contact_email=payload.contact_email.strip().lower(),
            contact_phone=payload.contact_phone.strip() if payload.contact_phone else None,
            desired_date=payload.desired_date,
            description=payload.description,
            status=ElectionRequestStatus.PENDING,
            created_at=db_now,
        )
        db.add(request_obj)
        await db.flush()

        await AuditService.log_event(
            db=db,
            action="PUBLIC_ELECTION_REQUESTED",
            entity_type="election_request",
            entity_id=str(request_obj.id),
            actor_role="PUBLIC",
            payload={
                "organization_name": request_obj.organization_name,
                "contact_email": request_obj.contact_email,
            },
            ip_address=client_ip,
        )
        await db.commit()
        await db.refresh(request_obj)
        return request_obj

    @staticmethod
    async def list_election_requests(
        db: AsyncSession, status_filter: ElectionRequestStatus | None = None
    ) -> list[ElectionRequest]:
        stmt = select(ElectionRequest)
        if status_filter:
            stmt = stmt.where(ElectionRequest.status == status_filter)
        stmt = stmt.order_by(ElectionRequest.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def approve_election_request(
        db: AsyncSession,
        request_id: uuid.UUID,
        payload: ApproveElectionRequest,
        reviewer: User,
        time_provider: TimeProvider,
        client_ip: str | None = None,
    ) -> Organization:
        db_now = await time_provider.now(db)
        stmt = select(ElectionRequest).where(ElectionRequest.id == request_id)
        req = (await db.execute(stmt)).scalar_one_or_none()
        if not req:
            raise NotFoundException("La solicitud de elección indicada no existe.")

        if req.status != ElectionRequestStatus.PENDING:
            raise ConflictException(f"La solicitud ya se encuentra en estado '{req.status.value}'.")

        # Verificar unicidad de slug
        stmt_slug = select(Organization).where(Organization.slug == payload.organization_slug)
        existing_org = (await db.execute(stmt_slug)).scalar_one_or_none()
        if existing_org:
            raise ConflictException(f"El identificador institucional '{payload.organization_slug}' ya existe.")

        # Verificar unicidad de correo
        stmt_user = select(User).where(User.email.ilike(req.contact_email))
        existing_user = (await db.execute(stmt_user)).scalar_one_or_none()
        if existing_user:
            raise ConflictException(f"El correo '{req.contact_email}' ya está registrado con otro usuario.")

        org = Organization(
            name=req.organization_name,
            slug=payload.organization_slug,
            org_type=req.org_type,
            status=OrganizationStatus.ACTIVE,
            contact_email=req.contact_email,
            created_at=db_now,
            updated_at=db_now,
        )
        db.add(org)
        await db.flush()

        admin_user = User(
            organization_id=org.id,
            email=req.contact_email,
            full_name=req.requester_name,
            password_hash=get_password_hash(payload.admin_password),
            role=UserRole.ADMIN_GENERAL,
            status=UserStatus.ACTIVE,
            created_at=db_now,
        )
        db.add(admin_user)
        await db.flush()

        req.status = ElectionRequestStatus.APPROVED
        req.reviewed_by = reviewer.id
        req.reviewed_at = db_now
        req.approved_organization_id = org.id

        await AuditService.log_event(
            db=db,
            action="ELECTION_REQUEST_APPROVED",
            entity_type="election_request",
            entity_id=str(req.id),
            actor_role=reviewer.role.value,
            actor_id=reviewer.id,
            organization_id=org.id,
            payload={"organization_id": str(org.id), "admin_email": admin_user.email},
            ip_address=client_ip,
        )
        await db.commit()
        await db.refresh(org)
        return org

    @staticmethod
    async def reject_election_request(
        db: AsyncSession,
        request_id: uuid.UUID,
        payload: RejectElectionRequest,
        reviewer: User,
        time_provider: TimeProvider,
        client_ip: str | None = None,
    ) -> ElectionRequest:
        db_now = await time_provider.now(db)
        stmt = select(ElectionRequest).where(ElectionRequest.id == request_id)
        req = (await db.execute(stmt)).scalar_one_or_none()
        if not req:
            raise NotFoundException("La solicitud de elección indicada no existe.")

        if req.status != ElectionRequestStatus.PENDING:
            raise ConflictException(f"La solicitud ya se encuentra en estado '{req.status.value}'.")

        req.status = ElectionRequestStatus.REJECTED
        req.reviewed_by = reviewer.id
        req.reviewed_at = db_now
        req.rejection_reason = payload.rejection_reason.strip()

        await AuditService.log_event(
            db=db,
            action="ELECTION_REQUEST_REJECTED",
            entity_type="election_request",
            entity_id=str(req.id),
            actor_role=reviewer.role.value,
            actor_id=reviewer.id,
            payload={"rejection_reason": req.rejection_reason},
            ip_address=client_ip,
        )
        await db.commit()
        await db.refresh(req)
        return req
