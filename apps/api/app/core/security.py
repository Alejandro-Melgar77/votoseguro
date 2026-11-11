"""
Seguridad: Criptografía de contraseñas (Argon2 / Bcrypt) y manejo de JWT
"""
from datetime import datetime, timedelta, timezone
from typing import Any
import jwt
from passlib.context import CryptContext
from app.core.config import settings

# Contexto de contraseñas configurado preferentemente con Argon2id y fallback a Bcrypt
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__memory_cost=65536,
    argon2__time_cost=3,
    argon2__parallelism=4,
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña plana coincide con el hash almacenado."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Genera un hash seguro para la contraseña."""
    return pwd_context.hash(password)


def create_access_token(
    subject: str,
    role: str,
    organization_id: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Genera un token JWT firmado con subject, rol y tenant ID."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "org_id": organization_id,
        "iat": now,
        "exp": expire,
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_voter_token(
    voter_id: str,
    election_id: str,
    credential_id: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Genera un token JWT efímero para sesión de cabina de votación."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=60)

    payload: dict[str, Any] = {
        "sub": str(voter_id),
        "role": "VOTER",
        "election_id": str(election_id),
        "credential_id": str(credential_id),
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodifica y valida la firma y expiración de un token JWT."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
