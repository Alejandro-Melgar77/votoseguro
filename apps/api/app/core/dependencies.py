"""
Dependencias de FastAPI: Inyección de Sesión, Autenticación, RBAC y Aislamiento Multi-Tenant
"""
import uuid
from dataclasses import dataclass
from typing import Annotated, AsyncGenerator
import jwt
from fastapi import Depends, Header, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.security import decode_access_token
from app.core.time import TimeProvider, default_time_provider
from app.db.models.election import Election
from app.db.models.user import AdminAssignment, User, UserRole, UserStatus
from app.db.models.voter import Voter, VoterStatus
from app.db.models.voting import VotingCredential
from app.db.session import get_db_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@dataclass
class TenantContext:
    organization_id: uuid.UUID
    user: User
    assignments: list[AdminAssignment]

    def is_segment_admin(self) -> bool:
        return self.user.role == UserRole.ADMIN_SEGMENT

    def is_general_admin(self) -> bool:
        return self.user.role == UserRole.ADMIN_GENERAL


def get_time_provider() -> TimeProvider:
    """Retorna el proveedor de tiempo actual (invariable o simulado en tests)."""
    return default_time_provider


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """Valida el JWT y carga el usuario autenticado activo."""
    try:
        payload = decode_access_token(token)
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise UnauthorizedException("El token no contiene un identificador de usuario válido.")
        user_id = uuid.UUID(user_id_str)
    except (jwt.PyJWTError, ValueError):
        raise UnauthorizedException("Token inválido o expirado.")

    stmt = (
        select(User)
        .options(selectinload(User.assignments))
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException("Usuario no encontrado en la plataforma.")
    if user.status != UserStatus.ACTIVE:
        raise ForbiddenException("El usuario se encuentra bloqueado o deshabilitado.")

    return user


async def get_tenant_context(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> TenantContext:
    """
    Regla Invariante #1: Aislamiento Multi-Tenant Estricto.
    Determina el organization_id del contexto institucional.
    Los usuarios con ADMIN_SEGMENT tienen acceso de SOLO LECTURA.
    """
    if current_user.role == UserRole.PLATFORM_ADMIN:
        raise ForbiddenException(
            "El operador de plataforma no opera dentro del contexto de una organización específica."
        )

    if not current_user.organization_id:
        raise ForbiddenException("El usuario no tiene una organización asignada.")

    # Invariante #2: Restricción absoluta de escritura para administradores delegados (ADMIN_SEGMENT)
    if current_user.role == UserRole.ADMIN_SEGMENT and request.method in ("POST", "PUT", "PATCH", "DELETE"):
        raise ForbiddenException(
            "Los administradores delegados (ADMIN_SEGMENT) disponen únicamente de permisos de SOLO LECTURA."
        )

    return TenantContext(
        organization_id=current_user.organization_id,
        user=current_user,
        assignments=list(current_user.assignments),
    )


def require_platform_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Exige rol PLATFORM_ADMIN."""
    if current_user.role != UserRole.PLATFORM_ADMIN:
        raise ForbiddenException("Esta acción requiere privilegios de Operador de Plataforma (PLATFORM_ADMIN).")
    return current_user


def require_admin_general(
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
) -> TenantContext:
    """Exige rol ADMIN_GENERAL dentro del Tenant."""
    if tenant.user.role != UserRole.ADMIN_GENERAL:
        raise ForbiddenException(
            "Esta operación solo puede ser efectuada por el Administrador General (ADMIN_GENERAL) de la institución."
        )
    return tenant


@dataclass
class VoterSessionContext:
    voter_id: uuid.UUID
    election_id: uuid.UUID
    credential_id: uuid.UUID
    voter: "Voter"
    election: "Election"
    credential: "VotingCredential"


async def get_current_voter_session(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> VoterSessionContext:
    """Valida el JWT de sesión de votante en cabina electoral."""
    from app.db.models.election import Election
    from app.db.models.voter import Voter, VoterStatus
    from app.db.models.voting import VotingCredential

    try:
        payload = decode_access_token(token)
        if payload.get("role") != "VOTER":
            raise UnauthorizedException("El token no corresponde a una sesión de votación válida.")
        voter_id = uuid.UUID(payload.get("sub"))
        election_id = uuid.UUID(payload.get("election_id"))
        credential_id = uuid.UUID(payload.get("credential_id"))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise UnauthorizedException("Token de votante inválido o expirado.")

    # Cargar votante con grupo y nodo
    stmt_voter = (
        select(Voter)
        .options(selectinload(Voter.group), selectinload(Voter.node))
        .where(Voter.id == voter_id, Voter.election_id == election_id)
    )
    voter = (await db.execute(stmt_voter)).scalar_one_or_none()
    if not voter:
        raise UnauthorizedException("Votante no empadronado en esta elección.")
    if voter.status != VoterStatus.ACTIVE:
        raise ForbiddenException("El votante no se encuentra en estado ACTIVO.")

    # Cargar elección
    stmt_election = select(Election).where(Election.id == election_id)
    election = (await db.execute(stmt_election)).scalar_one_or_none()
    if not election:
        raise NotFoundException("Elección no encontrada.")

    # Cargar credencial
    stmt_cred = select(VotingCredential).where(
        VotingCredential.id == credential_id,
        VotingCredential.voter_id == voter_id,
        VotingCredential.election_id == election_id,
    )
    credential = (await db.execute(stmt_cred)).scalar_one_or_none()
    if not credential:
        raise UnauthorizedException("Credencial de votación no válida.")

    return VoterSessionContext(
        voter_id=voter_id,
        election_id=election_id,
        credential_id=credential_id,
        voter=voter,
        election=election,
        credential=credential,
    )
