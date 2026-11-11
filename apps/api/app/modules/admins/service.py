"""
Servicio para Administradores Delegados de Solo Lectura (S1-11)
"""
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import get_password_hash
from app.core.time import TimeProvider
from app.db.models.election import Election
from app.db.models.user import AdminAssignment, User, UserRole, UserStatus
from app.modules.admins.schemas import AdminSegmentCreateRequest
from app.modules.audit.service import AuditService


class AdminAssignmentService:
    @staticmethod
    async def create_delegated_admin(
        db: AsyncSession,
        election_id: uuid.UUID,
        payload: AdminSegmentCreateRequest,
        creator: User,
        time_provider: TimeProvider,
        client_ip: str | None = None,
    ) -> AdminAssignment:
        db_now = await time_provider.now(db)

        # Verificar que la elección pertenezca a la organización
        stmt_el = select(Election).where(
            Election.id == election_id,
            Election.organization_id == creator.organization_id,
        )
        election = (await db.execute(stmt_el)).scalar_one_or_none()
        if not election:
            raise NotFoundException("La elección indicada no existe en su organización.")

        # Buscar si ya existe el usuario por correo
        stmt_user = select(User).where(User.email.ilike(payload.email.strip()))
        user = (await db.execute(stmt_user)).scalar_one_or_none()

        if user:
            if user.organization_id != creator.organization_id:
                raise ConflictException("El correo ya pertenece a un usuario de otra organización.")
            if user.role not in (UserRole.ADMIN_SEGMENT, UserRole.OBSERVER):
                raise ConflictException("El usuario ya tiene un rol administrativo superior.")
        else:
            user = User(
                organization_id=creator.organization_id,
                email=payload.email.strip().lower(),
                full_name=payload.full_name.strip(),
                password_hash=get_password_hash(payload.password),
                role=UserRole.ADMIN_SEGMENT,
                status=UserStatus.ACTIVE,
                created_at=db_now,
            )
            db.add(user)
            await db.flush()

        assignment = AdminAssignment(
            organization_id=creator.organization_id,
            user_id=user.id,
            election_id=election_id,
            group_id=payload.group_id,
            node_id=payload.node_id,
            permission="READ",
            created_at=db_now,
        )
        db.add(assignment)
        await db.flush()

        await AuditService.log_event(
            db=db,
            action="DELEGATED_ADMIN_ASSIGNED",
            entity_type="admin_assignment",
            entity_id=str(assignment.id),
            actor_role=creator.role.value,
            actor_id=creator.id,
            organization_id=creator.organization_id,
            election_id=election_id,
            payload={
                "delegated_user_id": str(user.id),
                "group_id": str(payload.group_id) if payload.group_id else None,
                "node_id": str(payload.node_id) if payload.node_id else None,
            },
            ip_address=client_ip,
        )
        await db.commit()
        await db.refresh(assignment)
        return assignment

    @staticmethod
    async def list_delegates(
        db: AsyncSession,
        election_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> list[AdminAssignment]:
        stmt = (
            select(AdminAssignment)
            .options(selectinload(AdminAssignment.user))
            .where(
                AdminAssignment.election_id == election_id,
                AdminAssignment.organization_id == organization_id,
            )
            .order_by(AdminAssignment.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def revoke_delegate(
        db: AsyncSession,
        election_id: uuid.UUID,
        assignment_id: uuid.UUID,
        revoker: User,
        client_ip: str | None = None,
    ) -> None:
        stmt = select(AdminAssignment).where(
            AdminAssignment.id == assignment_id,
            AdminAssignment.election_id == election_id,
            AdminAssignment.organization_id == revoker.organization_id,
        )
        assignment = (await db.execute(stmt)).scalar_one_or_none()
        if not assignment:
            raise NotFoundException("La asignación de delegado no fue encontrada.")

        await db.delete(assignment)
        await AuditService.log_event(
            db=db,
            action="DELEGATED_ADMIN_REVOKED",
            entity_type="admin_assignment",
            entity_id=str(assignment_id),
            actor_role=revoker.role.value,
            actor_id=revoker.id,
            organization_id=revoker.organization_id,
            election_id=election_id,
            ip_address=client_ip,
        )
        await db.commit()
