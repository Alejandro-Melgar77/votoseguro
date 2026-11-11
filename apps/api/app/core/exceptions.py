"""
Excepciones de dominio y errores HTTP estandarizados para VotoSeguro
"""
from fastapi import HTTPException, status


class UnauthorizedException(HTTPException):
    def __init__(self, detail: str = "Credenciales inválidas o sesión expirada"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenException(HTTPException):
    def __init__(self, detail: str = "No cuenta con los permisos necesarios para realizar esta acción"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class AccountLockedException(HTTPException):
    def __init__(self, minutes_remaining: int):
        super().__init__(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Cuenta bloqueada temporalmente por reiterados intentos fallidos. Intente de nuevo en {minutes_remaining} minutos.",
        )


class NotFoundException(HTTPException):
    def __init__(self, detail: str = "El recurso solicitado no fue encontrado"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictException(HTTPException):
    def __init__(self, detail: str = "Conflicto con el estado actual del recurso"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class UnprocessableEntityException(HTTPException):
    def __init__(self, detail: str = "Los datos proporcionados no cumplen con las reglas de validación"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)
