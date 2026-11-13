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
    ai_source: str = Field(
        default="DETERMINISTIC_FALLBACK",
        description="Origen de la inferencia: LFM3-1.7B_NEURAL_TUNNEL, LFM3-1.7B o DETERMINISTIC_FALLBACK."
    )
    model_name: Optional[str] = Field(default="votoseguro-lfm3", description="Nombre del modelo que procesó la solicitud.")
    latency_ms: Optional[int] = Field(default=None, description="Latencia en milisegundos de la inferencia.")


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
    ai_source: str = Field(
        default="DETERMINISTIC_FALLBACK",
        description="Origen de la inferencia: LFM3-1.7B_NEURAL_TUNNEL, LFM3-1.7B o DETERMINISTIC_FALLBACK."
    )
    model_name: Optional[str] = Field(default="votoseguro-lfm3", description="Nombre del modelo.")
    latency_ms: Optional[int] = Field(default=None, description="Latencia en ms.")


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
    ai_source: str = Field(
        default="DETERMINISTIC_FALLBACK",
        description="Origen de la inferencia: LFM3-1.7B_NEURAL_TUNNEL, LFM3-1.7B o DETERMINISTIC_FALLBACK."
    )
    model_name: Optional[str] = Field(default="votoseguro-lfm3", description="Nombre del modelo.")
    latency_ms: Optional[int] = Field(default=None, description="Latencia en ms.")


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
    ai_source: str = Field(
        default="DETERMINISTIC_FALLBACK",
        description="Origen de la inferencia: LFM3-1.7B_NEURAL_TUNNEL, LFM3-1.7B o DETERMINISTIC_FALLBACK."
    )
    model_name: Optional[str] = Field(default="votoseguro-lfm3", description="Nombre del modelo.")
    latency_ms: Optional[int] = Field(default=None, description="Latencia en ms.")


# ==========================================
# Sprint 2.5: Diagnóstico y Control de Túnel Estático
# ==========================================

class AiNodeStatusResponse(BaseModel):
    online: bool
    llm_base_url: str
    model_name: str
    provider: str
    strict_neural_mode: bool
    latency_ms: Optional[float] = None
    available_models: List[str] = Field(default_factory=list)
    status_label: str
    last_ping_at: Optional[str] = None


class AiNodeConfigUpdateRequest(BaseModel):
    llm_base_url: Optional[str] = None
    model_name: Optional[str] = None
    provider: Optional[str] = None
    strict_neural_mode: Optional[bool] = None
    timeout_seconds: Optional[float] = None


class AiNodeTestInferenceRequest(BaseModel):
    prompt: Optional[str] = Field(
        default=None,
        description="Prompt electoral de prueba. Si no se provee, se usa uno estándar."
    )
    task_type: Optional[str] = Field(
        default="IA-L1",
        description="Tipo de tarea para prueba: IA-L1, IA-L2b, IA-L3 o IA-L5."
    )


class AiNodeTestInferenceResponse(BaseModel):
    success: bool
    ai_source: str
    model_name: str
    latency_ms: float
    raw_response: dict[str, Any] = Field(default_factory=dict)
    audit_logged: bool = True
    error_message: Optional[str] = None


class AiNodePingRequest(BaseModel):
    node_status: str = Field(..., description="ONLINE o OFFLINE")
    llm_base_url: Optional[str] = None
    model_name: Optional[str] = None
    provider: Optional[str] = None
    tunnel_domain: Optional[str] = None
    local_latency_ms: Optional[float] = None
    timestamp: Optional[str] = None


class AiNodePingResponse(BaseModel):
    acknowledged: bool
    received_at: str
    current_strict_mode: bool

