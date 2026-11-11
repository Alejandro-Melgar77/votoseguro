"""
Configuración de Rate Limiting con SlowAPI (S2-06)
Protege endpoints críticos contra fuerza bruta y ataques DoS,
devolviendo HTTP 429 Too Many Requests con cabecera Retry-After y respuesta en español.
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings


def custom_key_func(request: Request) -> str:
    """
    Obtiene la IP remota respetando cabeceras de proxy (X-Forwarded-For).
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(
    key_func=custom_key_func,
    enabled=settings.RATE_LIMIT_ENABLED,
    default_limits=["120/minute"],
    headers_enabled=False,
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Manejador personalizado para RateLimitExceeded que devuelve HTTP 429 en español
    con la cabecera estándar Retry-After.
    """
    retry_after = 60
    if hasattr(exc, "detail") and exc.detail:
        detail_msg = f"Límite de tasa excedido ({exc.detail}). Por favor, espere antes de reintentar."
    else:
        detail_msg = "Demasiadas solicitudes. Límite de tasa excedido. Por favor, espere antes de reintentar."

    headers = {"Retry-After": str(retry_after)}
    return JSONResponse(
        status_code=429,
        content={
            "error_code": "RATE_LIMIT_EXCEEDED",
            "detail": detail_msg,
            "retry_after_seconds": retry_after,
        },
        headers=headers,
    )
