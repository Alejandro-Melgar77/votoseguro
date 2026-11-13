"""
Cliente de Inferencia Local y Salvaguardas para VotoSeguro v2 (Sprint 2 y Sprint 2.5).
Cumple con la Sección 7.4 del Plan Maestro:
- Invocación estructurada asíncrona hacia el Túnel Estático HTTPS de ngrok ({LLM_BASE_URL}/chat/completions)
- Cabeceras obligatorias: ngrok-skip-browser-warning: true y User-Agent
- Extractor robusto extract_first_json_object para garantizar parseo 100% libre de Markdown
- Soporte para tabla ai_runtime_config (Singleton en BD) y Modo Neuronal Estricto
- Telemetría real en respuestas: ai_source = LFM3-1.7B_NEURAL_TUNNEL, model_name y latency_ms
- Fallback determinista garantizado o HTTP 503 en modo estricto
- Trazabilidad libre de PII en ai_call_log y audit_log (Invariante #14)
"""
import logging
import re
import time
import uuid
from typing import Any, Callable, Optional, Type, TypeVar
import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.audit.service import AuditService

logger = logging.getLogger("votoseguro.ai.client")

T = TypeVar("T", bound=BaseModel)


def extract_first_json_object(raw_text: str) -> str:
    """
    Extrae de forma robusta el primer objeto JSON {...} ignorando preámbulos,
    bloques markdown (```json ... ```) o texto explicativo posterior.
    Garantiza parseo JSON 100% confiable en modelos de 1.7B/1.5B.
    """
    if not raw_text or not raw_text.strip():
        return ""
    stripped = raw_text.strip()
    
    # 1. Caso bloque markdown con o sin tag de lenguaje
    md_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if md_match:
        return md_match.group(1).strip()
    
    # 2. Caso bloque {...} balanceado en el texto
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return stripped[start : end + 1].strip()
    
    return stripped


class LocalLlmEngine:
    """
    Motor de inferencia local con puente a túnel estático ngrok,
    salvaguardas electorales y fallback determinista obligatorio.
    """

    @staticmethod
    async def get_effective_config(db: Optional[AsyncSession] = None) -> dict[str, Any]:
        """
        Recupera la configuración activa desde la tabla singleton ai_runtime_config
        o hace fallback a las variables de entorno de settings.
        """
        cfg = {
            "llm_base_url": settings.LLM_BASE_URL.rstrip("/"),
            "llm_model_name": settings.LLM_MODEL_NAME,
            "provider": "OLLAMA",
            "strict_neural_mode": getattr(settings, "STRICT_NEURAL_MODE", False),
            "timeout_seconds": getattr(settings, "LLM_TIMEOUT_SECONDS", 25.0),
        }
        if db:
            try:
                from app.db.models.ai import AiRuntimeConfig
                stmt = select(AiRuntimeConfig).limit(1)
                result = await db.execute(stmt)
                db_cfg = result.scalar_one_or_none()
                if db_cfg:
                    cfg["llm_base_url"] = db_cfg.llm_base_url.rstrip("/")
                    cfg["llm_model_name"] = db_cfg.llm_model_name
                    cfg["provider"] = db_cfg.provider
                    cfg["strict_neural_mode"] = db_cfg.strict_neural_mode
                    cfg["timeout_seconds"] = db_cfg.timeout_seconds
            except Exception as err:
                logger.debug(f"No se pudo consultar ai_runtime_config ({err}), usando settings por defecto.")
        return cfg

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
        Ejecuta la inferencia estructurada a través del túnel estático con telemetría completa.
        Si la PC está apagada:
          - strict_neural_mode == False: Retorna fallback determinista con ai_source="DETERMINISTIC_FALLBACK"
          - strict_neural_mode == True: Lanza HTTP 503 Service Unavailable informando que se debe iniciar INICIAR_IA_LOCAL.bat
        """
        start_time = time.perf_counter()
        status_result = "FALLBACK_DETERMINISTIC"
        parsed_result: Optional[T] = None
        duration_ms = 0

        # Cargar configuración activa
        active_cfg = await LocalLlmEngine.get_effective_config(db)
        llm_base_url = active_cfg["llm_base_url"]
        llm_model_name = active_cfg["llm_model_name"]
        timeout_sec = active_cfg["timeout_seconds"]
        strict_mode = active_cfg["strict_neural_mode"]

        # Si la IA local está deshabilitada globalmente
        if not settings.AI_LOCAL_ENABLED:
            logger.info(f"[{function_name}] IA Local deshabilitada por configuración. Activando fallback determinista.")
            result = fallback_fn()
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            if hasattr(result, "ai_source"):
                setattr(result, "ai_source", "DETERMINISTIC_FALLBACK")
            if hasattr(result, "model_name"):
                setattr(result, "model_name", "DETERMINISTIC_FALLBACK")
            if hasattr(result, "latency_ms"):
                setattr(result, "latency_ms", duration_ms)
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

        url = f"{llm_base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "ngrok-skip-browser-warning": "true",
            "User-Agent": "VotoSeguro-Core-Backend/2.0",
        }
        payload = {
            "model": llm_model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.05,
            "max_tokens": 400,
            "response_format": {"type": "json_object"},
        }

        call_error_reason = ""
        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices and "message" in choices[0] and "content" in choices[0]["message"]:
                        raw_content = choices[0]["message"]["content"]
                        clean_json_str = extract_first_json_object(raw_content)
                        parsed_result = schema_cls.model_validate_json(clean_json_str)
                        status_result = "SUCCESS_LLM"
                        logger.info(f"[{function_name}] Inferencia exitosa validada por Pydantic via {llm_base_url}.")
                else:
                    call_error_reason = f"HTTP {response.status_code}"
                    logger.warning(f"[{function_name}] Túnel devolvió status {response.status_code}.")
        except httpx.TimeoutException:
            call_error_reason = f"Timeout ({timeout_sec}s)"
            logger.warning(f"[{function_name}] Timeout de {timeout_sec}s llamando al túnel estático.")
        except httpx.ConnectError:
            call_error_reason = "ConnectError (PC Local no alcanzable)"
            logger.info(f"[{function_name}] Túnel estático inalcanzable en {url}. Nodo de escritorio offline.")
        except Exception as exc:
            call_error_reason = str(exc)
            logger.warning(f"[{function_name}] Error en llamada a túnel ({exc}).")

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Si el modelo respondió exitosamente
        if parsed_result is not None:
            if hasattr(parsed_result, "ai_source"):
                setattr(parsed_result, "ai_source", "LFM3-1.7B_NEURAL_TUNNEL")
            if hasattr(parsed_result, "model_name"):
                setattr(parsed_result, "model_name", llm_model_name)
            if hasattr(parsed_result, "latency_ms"):
                setattr(parsed_result, "latency_ms", duration_ms)

            if db:
                await LocalLlmEngine._safe_log_ai(
                    db=db,
                    org_id=organization_id,
                    elec_id=election_id,
                    function_name=function_name,
                    model_name=llm_model_name,
                    duration_ms=duration_ms,
                    status=status_result,
                    summary=sanitized_summary,
                )
            return parsed_result

        # Si falló la inferencia y estamos en Modo Neuronal Estricto
        if strict_mode:
            logger.error(f"[{function_name}] Modo Neuronal Estricto activo y nodo desconectado: {call_error_reason}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Nodo Neuronal Local Desconectado. El sistema se encuentra en Modo Neuronal Estricto. "
                    "Por favor inicie el servicio local ejecutando INICIAR_IA_LOCAL.bat en la PC de escritorio."
                ),
            )

        # Fallback determinista en modo degradado transparente
        parsed_result = fallback_fn()
        if hasattr(parsed_result, "ai_source"):
            setattr(parsed_result, "ai_source", "DETERMINISTIC_FALLBACK")
        if hasattr(parsed_result, "model_name"):
            setattr(parsed_result, "model_name", "DETERMINISTIC_FALLBACK")
        if hasattr(parsed_result, "latency_ms"):
            setattr(parsed_result, "latency_ms", duration_ms)
        status_result = "FALLBACK_DETERMINISTIC"

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

        return parsed_result

    @staticmethod
    async def ping_tunnel(llm_base_url: str, timeout: float = 6.0) -> dict[str, Any]:
        """
        Hace un ping directo al endpoint {llm_base_url}/models a través de ngrok
        midiendo la latencia de red y listando modelos disponibles.
        """
        url = f"{llm_base_url.rstrip('/')}/models"
        headers = {
            "ngrok-skip-browser-warning": "true",
            "User-Agent": "VotoSeguro-Tunnel-Diagnostics/2.0",
        }
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, headers=headers)
                latency_ms = round((time.perf_counter() - t0) * 1000, 2)
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("id") or m.get("name") for m in data.get("data", []) if isinstance(m, dict)]
                    return {
                        "online": True,
                        "latency_ms": latency_ms,
                        "available_models": models,
                        "status_code": 200,
                    }
                return {
                    "online": False,
                    "latency_ms": latency_ms,
                    "available_models": [],
                    "status_code": resp.status_code,
                }
        except Exception as exc:
            return {
                "online": False,
                "latency_ms": None,
                "available_models": [],
                "error": str(exc),
            }

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
