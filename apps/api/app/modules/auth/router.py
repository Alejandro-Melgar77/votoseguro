"""
Router API para Autenticación de Usuarios
"""
from typing import Annotated
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_time_provider
from app.core.rate_limit import limiter
from app.core.time import TimeProvider
from app.db.models.user import User
from app.db.session import get_db_session
from app.modules.auth.schemas import LoginRequest, TokenResponse, UserResponse
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    credentials: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    time_provider: Annotated[TimeProvider, Depends(get_time_provider)],
):
    """Inicia sesión con credenciales, generando un token JWT con aislamiento de tenant."""
    client_ip = request.client.host if request.client else None
    return await AuthService.authenticate_user(
        db=db,
        time_provider=time_provider,
        credentials=credentials,
        client_ip=client_ip,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Retorna la información del usuario autenticado."""
    return UserResponse.model_validate(current_user)
