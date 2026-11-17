"""
Esquemas Pydantic v2 para IA Externa (IA-E1, IA-E2, IA-E3) - Sprint 3.
"""
import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# IA-E1: Informe Ejecutivo en Lenguaje Natural
# ---------------------------------------------------------------------------

class ExecutiveReportCreateRequest(BaseModel):
    election_id: uuid.UUID = Field(..., description="ID de la elección a auditar")
    tone: str = Field(
        default="FORMAL_COURT",
        description="Tono del informe: 'FORMAL_COURT' o 'EXECUTIVE_BRIEF'",
    )


class ExecutiveReportAiPayload(BaseModel):
    title: str = Field(..., description="Título oficial del informe")
    executive_summary: str = Field(..., description="Resumen narrativo en Markdown")
    participation_analysis: str = Field(..., description="Análisis de participación y dinámicas")
    integrity_and_audit_certification: str = Field(..., description="Certificación formal de sellos")
    results_highlights: List[str] = Field(default_factory=list, description="Puntos destacados")
    recommendations: List[str] = Field(default_factory=list, description="Recomendaciones")
    ai_source: str = Field(default="GEMINI_EXTERNAL_API")
    model_used: str = Field(default="gemini-3.8-flash")


class ExecutiveReportResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    election_id: uuid.UUID
    generated_by: uuid.UUID
    language: str
    model_used: str
    ai_source: str
    aggregated_input_payload: dict[str, Any]
    title: str
    summary_markdown: str
    key_highlights: List[str]
    integrity_certification: str
    recommendations: List[str]
    report_hash: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# IA-E3: Verificación Facial Asistida Selfie vs. Cédula
# ---------------------------------------------------------------------------

class BiometricVerifyRequest(BaseModel):
    election_id: uuid.UUID = Field(..., description="ID de la elección")
    document_id: str = Field(..., description="Cédula de identidad del votante")
    consent_accepted: Optional[bool] = Field(
        default=None,
        description="Consentimiento explícito conforme a ley de protección de datos",
    )
    explicit_consent: Optional[bool] = Field(
        default=None,
        description="Alias de consent_accepted",
    )
    selfie_base64: Optional[str] = Field(
        default=None,
        description="Fotografía selfie en Base64 (procesada en RAM, jamás guardada)",
    )
    id_card_base64: Optional[str] = Field(
        default=None,
        description="Fotografía de la cédula en Base64 (procesada en RAM, jamás guardada)",
    )
    use_fallback_code: bool = Field(
        default=False,
        description="Indica si el votante opta por verificación alternativa por código o mesa",
    )


class BiometricVerifyAiPayload(BaseModel):
    match_verdict: str = Field(
        ...,
        description="'MATCH_PROBABLE', 'MISMATCH' o 'INCONCLUSIVE'",
    )
    confidence_band: str = Field(
        default="HIGH",
        description="'HIGH', 'MEDIUM', 'LOW' o 'MANUAL'",
    )
    confidence_note: str = Field(default="", description="Nota de cotejo facial")
    liveness_disclaimer: str = Field(
        default="Verificación visual asistida en memoria; no sustituye la firma ni la mesa electoral.",
        description="Aviso de salvaguarda cívica",
    )
    requires_human_or_code_fallback: bool = Field(
        default=False,
        description="Indica si debe derivarse a revisión humana",
    )
    explanation_es: str = Field(default="", description="Explicación en español para el ciudadano")
    ai_source: str = Field(default="GEMINI_EXTERNAL_API")


class BiometricVerifyResponse(BaseModel):
    match_verdict: str
    verdict: str
    confidence_band: str
    confidence_note: str
    liveness_disclaimer: str
    requires_human_or_code_fallback: bool
    explanation_es: str
    images_persisted: bool = False
    ai_source: str
    audit_id: Optional[uuid.UUID] = None


# ---------------------------------------------------------------------------
# IA-E2: Auditoría y Traducción Multi-idioma
# ---------------------------------------------------------------------------

class TranslationAuditRequest(BaseModel):
    target_lang: str = Field(..., description="'qu', 'ay', 'gn'")
    keys_to_translate: dict[str, str] = Field(..., description="Diccionario clave -> texto español")


class TranslationAuditResponse(BaseModel):
    target_lang: str
    translations: dict[str, str]
    reviewed_by_native_speaker: bool = False
    ai_source: str
