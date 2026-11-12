"""
Cliente de Inferencia Local y Salvaguardas para LiquidAI/LFM3-1.7B (GGUF Q4_K_M).
Cumple la Sección 7.4 del Plan Maestro:
- Invocación estructurada asíncrona hacia LLM_BASE_URL (/v1/chat/completions)
- Timeout estricto de 8 segundos y temperatura 0.05
- Validación Pydantic v2 estricta de salida JSON
- Fallback determinista garantizado en caso de timeout, caída de red o error de validación
- Registro en ai_call_log y audit_log SIN datos personales sensibles (Invariante #14)
"""
import logging
import time
import uuid
from typing import Any, Callable, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.audit.service import AuditService

logger = logging.getLogger("votoseguro.ai.client")

T = TypeVar("T", bound=BaseModel)


class LocalLlmEngine:
    """
    Motor de inferencia local con salvaguardas y fallback determinista obligatorio.
    """

    @staticmethod
    async def call_structured(
        prompt: str,
        schema_cls: Type[T],
        fallback_fn: Callable[[], T],
        system_instruction: str = "Eres el asistente electoral de VotoSeguro. Responde estrictamente en formato JSON válido según el esquema solicitado.",
        function_name: str = "IA_LOCAL_GENERIC",
        organization_id: Optional[uuid.UUID] = None,
        election_id: Optional[uuid.UUID] = None,
        db: Optional[AsyncSession] = None,
        sanitized_summary: str = "Inferencia asistida de IA Local",
    ) -> T:
        """
        Ejecuta la llamada a LFM3-1.7B con timeout de 8 segundos y validación JSON Pydantic.
        Si falla por cualquier motivo, ejecuta fallback_fn() sin interrumpir el flujo.
        """
        start_time = time.perf_counter()
        status_result = "FALLBACK_DETERMINISTIC"
        parsed_result: Optional[T] = None
        duration_ms = 0

        # Si la IA local está deshabilitada por configuración, recurrir de inmediato al fallback
        if not settings.AI_LOCAL_ENABLED:
            logger.info(f"[{function_name}] IA Local deshabilitada por configuración. Activando fallback determinista.")
            result = fallback_fn()
            if hasattr(result, "ai_source"):
                setattr(result, "ai_source", "DETERMINISTIC_FALLBACK")
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            if db:
                await LocalLlmEngine._safe_log_ai(
                    db=db,
                    org_id=organization_id,
                    elec_id=election_id,
                    function_name=function_name,
                    model_name="DETERMINISTIC_FALLBACK",
                    duration_ms=duration_ms,
                    status=status_result,
                    summary=sanitized_summary,
                )
            return result

        # Intentar llamar al servidor OpenAI-compatible (llama.cpp u Ollama en red interna)
        url = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
        payload = {
            "model": settings.LLM_MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.05,
            "max_tokens": 350,
            "response_format": {"type": "json_object"},
        }

        try:
            async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices and "message" in choices[0] and "content" in choices[0]["message"]:
                        content_str = choices[0]["message"]["content"]
                        # Validación estricta con Pydantic
                        parsed_result = schema_cls.model_validate_json(content_str)
                        if hasattr(parsed_result, "ai_source"):
                            setattr(parsed_result, "ai_source", "LFM3-1.7B")
                        status_result = "SUCCESS_LLM"
                        logger.info(f"[{function_name}] Respuesta exitosa de LFM3-1.7B validada con Pydantic.")
                else:
                    logger.warning(
                        f"[{function_name}] LFM3 devolvió status HTTP {response.status_code}. Activando fallback determinista."
                    )
        except httpx.TimeoutException:
            logger.warning(
                f"[{function_name}] Timeout de {settings.LLM_TIMEOUT_SECONDS}s excedido llamando a LFM3. Activando fallback determinista."
            )
        except httpx.ConnectError:
            logger.info(
                f"[{function_name}] Servidor LLM local inalcanzable en {url}. Operando en modo degradado con fallback determinista."
            )
        except Exception as exc:
            logger.warning(
                f"[{function_name}] Error en llamada a LLM local ({exc}). Activando fallback determinista."
            )

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Si no se obtuvo una respuesta válida del LLM, ejecutar el fallback determinista
        if parsed_result is None:
            parsed_result = fallback_fn()
            if hasattr(parsed_result, "ai_source"):
                setattr(parsed_result, "ai_source", "DETERMINISTIC_FALLBACK")
            status_result = "FALLBACK_DETERMINISTIC"

        # Registrar trazabilidad en ai_call_log y audit_log SIN PII
        if db:
            model_used = settings.LLM_MODEL_NAME if status_result == "SUCCESS_LLM" else "DETERMINISTIC_FALLBACK"
            await LocalLlmEngine._safe_log_ai(
                db=db,
                org_id=organization_id,
                elec_id=election_id,
                function_name=function_name,
                model_name=model_used,
                duration_ms=duration_ms,
                status=status_result,
                summary=sanitized_summary,
            )

        return parsed_result

    @staticmethod
    async def _safe_log_ai(
        db: AsyncSession,
        org_id: Optional[uuid.UUID],
        elec_id: Optional[uuid.UUID],
        function_name: str,
        model_name: str,
        duration_ms: int,
        status: str,
        summary: str,
    ) -> None:
        try:
            await AuditService.log_ai_call(
                db=db,
                organization_id=org_id,
                election_id=elec_id,
                function_name=function_name,
                model_name=model_name,
                duration_ms=duration_ms,
                status=status,
                summary=summary,
            )
        except Exception as err:
            logger.error(f"Error registrando ai_call_log: {err}", exc_info=True)
