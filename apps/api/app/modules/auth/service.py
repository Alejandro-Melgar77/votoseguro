"""
Servicio de Autenticación con Protección contra Fuerza Bruta y Aislamiento Institucional
"""
import math
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    AccountLockedException,
    ForbiddenException,
    UnauthorizedException,
)
from app.core.security import create_access_token, verify_password
from app.core.time import TimeProvider
from app.db.models.organization import Organization
from app.db.models.user import User, UserStatus
from app.modules.audit.service import AuditService
from app.modules.auth.schemas import (
    LoginRequest,
    OrganizationBriefResponse,
    TokenResponse,
    UserResponse,
)


class AuthService:
    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        time_provider: TimeProvider,
        credentials: LoginRequest,
        client_ip: str | None = None,
    ) -> TokenResponse:
        db_now = await time_provider.now(db)

        # Buscar usuario insensible a mayúsculas
        stmt = (
            select(User)
            .options(selectinload(User.organization))
            .where(User.email.ilike(credentials.email.strip()))
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            # Registrar intento fallido para cuenta inexistente sin revelar existencia
            await AuditService.log_event(
                db=db,
                action="USER_LOGIN_FAILED_UNKNOWN_EMAIL",
                entity_type="user",
                entity_id="unknown",
                actor_role="ANONYMOUS",
                payload={"email": credentials.email},
                ip_address=client_ip,
            )
            await db.commit()
            raise UnauthorizedException("Correo electrónico o contraseña incorrectos.")

        # Verificar si la cuenta está deshabilitada administrativamente
        if user.status == UserStatus.DISABLED:
            raise ForbiddenException("Esta cuenta de usuario ha sido deshabilitada por el administrador.")

        # Verificar bloqueo temporal por fuerza bruta
        if user.locked_until and user.locked_until > db_now:
            remaining_seconds = (user.locked_until - db_now).total_seconds()
            remaining_minutes = max(1, math.ceil(remaining_seconds / 60))
            raise AccountLockedException(minutes_remaining=remaining_minutes)

        # Si el bloqueo ya expiró, rehabilitar estado
        if user.locked_until and user.locked_until <= db_now:
            user.locked_until = None
            user.failed_attempts = 0
            if user.status == UserStatus.LOCKED:
                user.status = UserStatus.ACTIVE

        # Verificar contraseña
        if not verify_password(credentials.password, user.password_hash):
            user.failed_attempts += 1
            action_name = "USER_LOGIN_FAILED"

            # Umbral de fuerza bruta: 5 intentos fallidos
            if user.failed_attempts >= 5:
                user.locked_until = db_now + timedelta(minutes=15)
                user.status = UserStatus.LOCKED
                action_name = "USER_LOCKED_BRUTE_FORCE"

                await AuditService.log_event(
                    db=db,
                    action=action_name,
                    entity_type="user",
                    entity_id=str(user.id),
                    actor_role=user.role.value,
                    actor_id=user.id,
                    organization_id=user.organization_id,
                    payload={"failed_attempts": user.failed_attempts, "locked_until": user.locked_until.isoformat()},
                    ip_address=client_ip,
                )
                await db.commit()
                raise AccountLockedException(minutes_remaining=15)

            await AuditService.log_event(
                db=db,
                action=action_name,
                entity_type="user",
                entity_id=str(user.id),
                actor_role=user.role.value,
                actor_id=user.id,
                organization_id=user.organization_id,
                payload={"failed_attempts": user.failed_attempts},
                ip_address=client_ip,
            )
            await db.commit()
            raise UnauthorizedException("Correo electrónico o contraseña incorrectos.")

        # Autenticación exitosa: reiniciar contadores
        user.failed_attempts = 0
        user.locked_until = None
        user.status = UserStatus.ACTIVE
        user.last_login_at = db_now

        await AuditService.log_event(
            db=db,
            action="USER_LOGIN_SUCCESS",
            entity_type="user",
            entity_id=str(user.id),
            actor_role=user.role.value,
            actor_id=user.id,
            organization_id=user.organization_id,
            payload={"email": user.email},
            ip_address=client_ip,
        )
        await db.commit()

        token = create_access_token(
            subject=str(user.id),
            role=user.role.value,
            organization_id=str(user.organization_id) if user.organization_id else None,
        )

        org_dto = None
        if user.organization:
            org_dto = OrganizationBriefResponse.model_validate(user.organization)

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
            organization=org_dto,
        )
