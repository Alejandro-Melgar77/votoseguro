"""
Cliente Oficial hacia Google Gemini API (IA Externa - Sprint 3) y Salvaguardas Electorales.
Cubre:
- IA-E1: Informe Ejecutivo en Lenguaje Natural (métricas agregadas exclusivamente).
- IA-E2: Traducción e Internacionalización Dinámica (Quechua, Aymara, Guaraní).
- IA-E3: Verificación Facial Asistida Selfie vs. Cédula (en memoria RAM sin persistencia).
- Invariante #14: Trazabilidad en ai_call_log y audit_log estrictamente libre de PII/votos.
- Modo Degradado Determinista: Fallback automático ante ausencia de API Key o error de red.
"""
import json
import logging
import time
import uuid
from typing import Any, Callable, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import extract_first_json_object
from app.core.config import settings
from app.modules.audit.service import AuditService

logger = logging.getLogger("votoseguro.ai.gemini_client")

T = TypeVar("T", bound=BaseModel)


class GeminiExternalClient:
    """
    Cliente asíncrono para inferencia con modelos Gemini en Google Cloud / AI Studio.
    Implementa modo degradado determinista transparente ante fallas o entornos sin clave.
    """

    @staticmethod
    def is_configured() -> bool:
        """Verifica si la API Key de Gemini está configurada y no es un placeholder."""
        key = (getattr(settings, "GEMINI_API_KEY", "") or "").strip()
        if not key or "TU_GEMINI" in key or key.lower() == "none":
            return False
        return bool(getattr(settings, "AI_EXTERNAL_ENABLED", True))

    @staticmethod
    def get_api_endpoint(model_name: Optional[str] = None) -> str:
        """Genera el endpoint REST de la API de Google Gemini."""
        model = model_name or getattr(settings, "GEMINI_MODEL", "gemini-3.8-flash")
        api_key = (getattr(settings, "GEMINI_API_KEY", "") or "").strip()
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    @classmethod
    async def call_structured(
        cls,
        prompt: str,
        schema_cls: Type[T],
        fallback_fn: Callable[[], T],
        system_instruction: str = "",
        function_name: str = "IA-E1_EXECUTIVE_REPORT",
        organization_id: Optional[uuid.UUID] = None,
        election_id: Optional[uuid.UUID] = None,
        db: Optional[AsyncSession] = None,
        sanitized_summary: str = "Generación de informe ejecutivo agregado con Gemini",
        temperature: float = 0.2,
    ) -> T:
        """
        Ejecuta una llamada de texto estructurado JSON hacia Gemini API con fallback determinista.
        """
        if settings.AI_PROVIDER == 'ANTHROPIC' and settings.AI_EXTERNAL_ENABLED:
            from app.ai.anthropic_client import AnthropicClient
            return await AnthropicClient.call_structured(prompt=prompt,schema_cls=schema_cls,fallback_fn=fallback_fn,
                system_instruction=system_instruction,function_name=function_name,organization_id=organization_id,
                election_id=election_id,db=db,sanitized_summary=sanitized_summary)
        start_time = time.perf_counter()
        duration_ms = 0

        # 1. Comprobación de configuración y fallback temprano
        if not cls.is_configured():
            logger.info(
                f"[{function_name}] Gemini API no configurada o desactivada. "
                "Activando Modo Degradado Determinista."
            )
            fallback_res = fallback_fn()
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            cls._apply_telemetry_fields(fallback_res, "DETERMINISTIC_FALLBACK", "DETERMINISTIC_FALLBACK", duration_ms)
            if db:
                await cls._safe_log_ai(
                    db=db,
                    org_id=organization_id,
                    elec_id=election_id,
                    function_name=function_name,
                    model_name="DETERMINISTIC_FALLBACK",
                    duration_ms=duration_ms,
                    status="FALLBACK_DETERMINISTIC",
                    summary=sanitized_summary,
                )
            return fallback_res

        endpoint = cls.get_api_endpoint()
        model_name = getattr(settings, "GEMINI_MODEL", "gemini-3.8-flash")
        timeout_sec = getattr(settings, "GEMINI_TIMEOUT_SECONDS", 20.0)

        # Construcción del payload para Gemini
        contents_parts = []
        if system_instruction:
            contents_parts.append({"text": f"{system_instruction}\n\n{prompt}"})
        else:
            contents_parts.append({"text": prompt})

        payload = {
            "contents": [{"parts": contents_parts}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }

        call_status = "FALLBACK_DETERMINISTIC"
        model_reported = model_name

        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                resp = await client.post(
                    endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                duration_ms = int((time.perf_counter() - start_time) * 1000)

                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text_content = (
                            candidates[0]
                            .get("content", {})
                            .get("parts", [{}])[0]
                            .get("text", "")
                        )
                        clean_json = extract_first_json_object(text_content)
                        parsed = schema_cls.model_validate_json(clean_json)
                        call_status = "SUCCESS"
                        cls._apply_telemetry_fields(parsed, "GEMINI_EXTERNAL_API", model_name, duration_ms)
                        if db:
                            await cls._safe_log_ai(
                                db=db,
                                org_id=organization_id,
                                elec_id=election_id,
                                function_name=function_name,
                                model_name=model_name,
                                duration_ms=duration_ms,
                                status=call_status,
                                summary=sanitized_summary,
                            )
                        return parsed
                else:
                    logger.warning(
                        f"[{function_name}] Gemini API retornó HTTP {resp.status_code}: {resp.text[:300]}"
                    )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.warning(f"[{function_name}] Excepción llamando a Gemini API: {exc}")

        # Fallback determinista ante error o respuesta no parseable
        fallback_res = fallback_fn()
        cls._apply_telemetry_fields(fallback_res, "DETERMINISTIC_FALLBACK", "DETERMINISTIC_FALLBACK", duration_ms)
        if db:
            await cls._safe_log_ai(
                db=db,
                org_id=organization_id,
                elec_id=election_id,
                function_name=function_name,
                model_name="DETERMINISTIC_FALLBACK",
                duration_ms=duration_ms,
                status="FALLBACK_DETERMINISTIC",
                summary=f"{sanitized_summary} (Modo degradado activado)",
            )
        return fallback_res

    @classmethod
    async def call_multimodal_structured(
        cls,
        prompt: str,
        images_base64: list[dict[str, str]],  # [{"mime_type": "image/jpeg", "data": "b64..."}]
        schema_cls: Type[T],
        fallback_fn: Callable[[], T],
        system_instruction: str = "",
        function_name: str = "IA-E3_BIOMETRIC_VERIFY",
        organization_id: Optional[uuid.UUID] = None,
        election_id: Optional[uuid.UUID] = None,
        db: Optional[AsyncSession] = None,
        sanitized_summary: str = "Verificación facial multimodal selfie vs cédula",
        temperature: float = 0.1,
    ) -> T:
        """
        Ejecuta una llamada multimodal con imágenes en memoria RAM hacia Gemini API.
        Garantiza Invariante #15: Cero persistencia en disco o BD.
        """
        if settings.AI_PROVIDER == 'ANTHROPIC' and settings.AI_EXTERNAL_ENABLED:
            from app.ai.anthropic_client import AnthropicClient
            return await AnthropicClient.call_structured(prompt=prompt,images_base64=images_base64,
                schema_cls=schema_cls,fallback_fn=fallback_fn,system_instruction=system_instruction,
                function_name=function_name,organization_id=organization_id,election_id=election_id,
                db=db,sanitized_summary=sanitized_summary)
        start_time = time.perf_counter()
        duration_ms = 0

        if not cls.is_configured():
            logger.info(
                f"[{function_name}] Gemini API no configurada. Activando fallback determinista multimodal."
            )
            fallback_res = fallback_fn()
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            cls._apply_telemetry_fields(fallback_res, "DETERMINISTIC_FALLBACK", "DETERMINISTIC_FALLBACK", duration_ms)
            if db:
                await cls._safe_log_ai(
                    db=db,
                    org_id=organization_id,
                    elec_id=election_id,
                    function_name=function_name,
                    model_name="DETERMINISTIC_FALLBACK",
                    duration_ms=duration_ms,
                    status="FALLBACK_DETERMINISTIC",
                    summary=sanitized_summary,
                )
            return fallback_res

        endpoint = cls.get_api_endpoint()
        model_name = getattr(settings, "GEMINI_MODEL", "gemini-3.8-flash")
        timeout_sec = getattr(settings, "GEMINI_TIMEOUT_SECONDS", 20.0)

        parts = []
        if system_instruction:
            parts.append({"text": f"{system_instruction}\n\n{prompt}"})
        else:
            parts.append({"text": prompt})

        for img in images_base64:
            parts.append({
                "inline_data": {
                    "mime_type": img.get("mime_type", "image/jpeg"),
                    "data": img.get("data", ""),
                }
            })

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                resp = await client.post(
                    endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                duration_ms = int((time.perf_counter() - start_time) * 1000)

                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text_content = (
                            candidates[0]
                            .get("content", {})
                            .get("parts", [{}])[0]
                            .get("text", "")
                        )
                        clean_json = extract_first_json_object(text_content)
                        parsed = schema_cls.model_validate_json(clean_json)
                        cls._apply_telemetry_fields(parsed, "GEMINI_EXTERNAL_API", model_name, duration_ms)
                        if db:
                            await cls._safe_log_ai(
                                db=db,
                                org_id=organization_id,
                                elec_id=election_id,
                                function_name=function_name,
                                model_name=model_name,
                                duration_ms=duration_ms,
                                status="SUCCESS",
                                summary=sanitized_summary,
                            )
                        return parsed
                else:
                    logger.warning(
                        f"[{function_name}] Gemini API retornó HTTP {resp.status_code}: {resp.text[:300]}"
                    )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.warning(f"[{function_name}] Excepción multimodal Gemini: {exc}")

        # Fallback determinista
        fallback_res = fallback_fn()
        cls._apply_telemetry_fields(fallback_res, "DETERMINISTIC_FALLBACK", "DETERMINISTIC_FALLBACK", duration_ms)
        if db:
            await cls._safe_log_ai(
                db=db,
                org_id=organization_id,
                elec_id=election_id,
                function_name=function_name,
                model_name="DETERMINISTIC_FALLBACK",
                duration_ms=duration_ms,
                status="FALLBACK_DETERMINISTIC",
                summary=f"{sanitized_summary} (Modo degradado activado)",
            )
        return fallback_res

    @staticmethod
    def _apply_telemetry_fields(obj: Any, source: str, model: str, latency: int) -> None:
        """Asigna campos de telemetría si existen en el modelo Pydantic o dict."""
        for field, val in [
            ("ai_source", source),
            ("model_used", model),
            ("model_name", model),
            ("latency_ms", latency),
        ]:
            if hasattr(obj, field):
                try:
                    setattr(obj, field, val)
                except Exception:
                    pass

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
        """Registra la invocación en la bitácora unificada de auditoría e IA."""
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
            logger.error(f"Error registrando ai_call_log en GeminiExternalClient: {err}", exc_info=True)
