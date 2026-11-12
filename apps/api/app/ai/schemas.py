"""
Esquemas Pydantic v2 estrictos para la capa de Inteligencia Artificial Local (LFM3-1.7B)
Cumple la Sección 7.4 del Plan Maestro y las especificaciones de IA-L1 a IA-L5.
"""
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field


# ==========================================
# IA-L1: Detector y Explicador de Anomalías
# ==========================================

class AnomalyMetricSummary(BaseModel):
    anomaly_type: str
    target_name: str
    metric_label: str
    metric_value: float
    baseline_value: Optional[float] = None
    sample_size: int = 0
    extra_data: dict[str, Any] = Field(default_factory=dict)


class AnomalyExplanationResponse(BaseModel):
    anomaly_id: str
    code: str
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    metrics_summary: dict[str, Any]
    explanation_es: str = Field(
        ...,
        description="Explicación clara en español de la anomalía estadística para el administrador humano."
    )
    recommended_checks: List[str] = Field(
        default_factory=list,
        description="2 a 3 verificaciones recomendadas a realizar por el administrador."
    )
    requires_human_decision: bool = Field(
        default=True,
        description="Garantía de salvaguarda: la decisión final siempre es humana."
    )
    ai_source: Literal["LFM3-1.7B", "DETERMINISTIC_FALLBACK"] = "DETERMINISTIC_FALLBACK"


class AnomalyScanResponse(BaseModel):
    election_id: str
    election_status: str
    total_active_voters: int
    total_ballots_cast: int
    participation_rate_pct: float
    anomalies_found_count: int
    anomalies: List[AnomalyExplanationResponse]
    scanned_at_utc: str
    is_simulation: bool = False


# ==========================================
# IA-L2b: Segunda Opinión de Duplicados
# ==========================================

class DuplicateAdjudicationSuggestion(BaseModel):
    issue_id: Optional[str] = None
    verdict: Literal["mismo", "distinto", "dudoso"]
    confidence_label: Literal["ALTA", "MEDIA", "BAJA"]
    short_reason: str = Field(
        ...,
        max_length=250,
        description="Motivo conciso en español de la sugerencia (máximo 250 caracteres)."
    )
    human_action_required: bool = Field(
        default=True,
        description="Invariante: la IA nunca fusiona, borra ni bloquea de forma autónoma."
    )
    ai_source: Literal["LFM3-1.7B", "DETERMINISTIC_FALLBACK"] = "DETERMINISTIC_FALLBACK"


class BatchDuplicateAdjudicationResponse(BaseModel):
    batch_id: str
    total_evaluated: int
    suggestions: List[DuplicateAdjudicationSuggestion]
    adjudicated_at: str


# ==========================================
# IA-L3: Extracción OCR de Cédula de Identidad
# ==========================================

class IdCardExtractionRequest(BaseModel):
    raw_ocr_text: str = Field(
        ...,
        min_length=1,
        description="Texto bruto extraído en el cliente (Invariante #15: CERO imágenes persistidas)."
    )
    election_id: Optional[str] = None


class IdCardExtractionResponse(BaseModel):
    ci: str = Field(
        ...,
        description="Número de cédula de identidad normalizado y limpio."
    )
    nombres: str = Field(
        ...,
        description="Nombres extraídos del documento."
    )
    apellidos: str = Field(
        ...,
        description="Apellidos extraídos del documento."
    )
    fecha_nacimiento: Optional[str] = Field(
        default=None,
        description="Fecha de nacimiento en formato YYYY-MM-DD o DD/MM/YYYY."
    )
    regex_valid: bool = Field(
        default=True,
        description="Indica si los campos principales superan las reglas sintácticas oficiales."
    )
    confidence_note: str = Field(
        default="",
        description="Nota de calidad o advertencia sobre el texto OCR."
    )
    requires_voter_confirmation: bool = Field(
        default=True,
        description="Invariante: el votante debe confirmar visualmente los campos extraídos."
    )
    ai_source: Literal["LFM3-1.7B", "DETERMINISTIC_FALLBACK"] = "DETERMINISTIC_FALLBACK"


# ==========================================
# IA-L5: Asistente RAG sobre Manuales Oficiales
# ==========================================

class DocumentCitation(BaseModel):
    doc_id: str
    title: str
    excerpt: str


class RagAssistantRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        description="Consulta del votante o administrador."
    )
    context_role: Literal["VOTER", "ADMIN", "PUBLIC"] = "VOTER"
    election_id: Optional[str] = None


class RagAssistantResponse(BaseModel):
    question: str
    answer: str
    answered_from_docs: bool = Field(
        ...,
        description="Indica si la respuesta proviene estrictamente de los manuales oficiales de VotoSeguro."
    )
    citations: List[DocumentCitation] = Field(
        default_factory=list,
        description="Citas documentales de los manuales oficiales."
    )
    escalate_to_support: bool = Field(
        default=False,
        description="Indica si se aconseja contactar al soporte electoral humano."
    )
    ai_source: Literal["LFM3-1.7B", "DETERMINISTIC_FALLBACK"] = "DETERMINISTIC_FALLBACK"
