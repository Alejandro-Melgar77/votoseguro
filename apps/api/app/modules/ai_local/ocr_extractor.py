"""
Extractor Estructurado de Campos de Cédula desde Texto OCR con LFM3-1.7B (IA-L3).
Cumple estrictamente la Invariante #15: CERO persistencia o subida de imágenes al servidor.
El OCR se ejecuta en el dispositivo cliente y este módulo recibe exclusivamente texto plano.
"""
import re
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import LocalLlmEngine
from app.ai.fallbacks import fallback_extract_id_card
from app.ai.schemas import IdCardExtractionResponse


async def extract_id_card_from_text(
    raw_ocr_text: str,
    election_id: Optional[uuid.UUID] = None,
    db: Optional[AsyncSession] = None,
) -> IdCardExtractionResponse:
    """
    Convierte el texto OCR bruto en un JSON estructurado y validado por regex.
    """
    # Salvaguarda Invariante #15: Si se detecta un Data URI o base64 masivo de imagen, descartar inmediatamente
    if "data:image" in raw_ocr_text or ";base64," in raw_ocr_text:
        # Extraer solo caracteres de texto plano legibles y descartar el payload binario
        raw_ocr_text = re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", "", raw_ocr_text)

    cleaned_text = raw_ocr_text.strip()
    if not cleaned_text:
        return fallback_extract_id_card("")

    prompt_text = (
        f"Del siguiente texto bruto extraído mediante OCR de una cédula de identidad boliviana/latinoamericana, "
        f"extrae los campos en formato JSON estricto:\n\n"
        f"--- TEXTO OCR ---\n"
        f"{cleaned_text}\n"
        f"-----------------\n\n"
        f"Responde con este esquema JSON:\n"
        f"- ci: número de carnet/cédula normalizado (ej. \"CI-8001002\" o \"8001002\")\n"
        f"- nombres: nombres de pila en mayúsculas/título\n"
        f"- apellidos: apellidos paterno y materno\n"
        f"- fecha_nacimiento: fecha en formato DD/MM/YYYY o YYYY-MM-DD (o null si no figura)\n"
        f"- regex_valid: true si ci y nombres tienen formato verosímil, false si está incompleto\n"
        f"- confidence_note: breve nota de calidad del texto extraído\n"
        f"- requires_voter_confirmation: true"
    )

    result = await LocalLlmEngine.call_structured(
        prompt=prompt_text,
        schema_cls=IdCardExtractionResponse,
        fallback_fn=lambda: fallback_extract_id_card(cleaned_text),
        system_instruction=(
            "Eres el analizador sintáctico de cédulas de VotoSeguro. "
            "Convierte texto plano en JSON estructurado de identidad. "
            "Nunca almacenes ni persistas datos personales fuera del resultado transitorio en memoria."
        ),
        function_name="IA-L3_ID_CARD_EXTRACT",
        organization_id=None,
        election_id=election_id,
        db=db,
        sanitized_summary="Extracción estructurada de campos de texto OCR de cédula (cero imágenes persistidas)",
    )

    # Verificación final de integridad regex determinista
    fallback_res = fallback_extract_id_card(cleaned_text)
    if not result.ci or result.ci == "CI-PENDIENTE":
        if fallback_res.ci and fallback_res.ci != "CI-PENDIENTE":
            result.ci = fallback_res.ci

    if not result.fecha_nacimiento and fallback_res.fecha_nacimiento:
        result.fecha_nacimiento = fallback_res.fecha_nacimiento

    # Validar coherencia por expresiones regulares de forma determinista
    ci_clean = re.sub(r"[^\w-]", "", result.ci or "").upper()
    ci_ok = bool(re.search(r"[0-9]{5,10}", ci_clean))
    names_ok = bool(result.nombres and len(result.nombres.strip()) >= 2)
    result.regex_valid = bool(ci_ok and names_ok)

    result.requires_voter_confirmation = True
    return result
