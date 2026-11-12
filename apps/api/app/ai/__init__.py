"""
Capa de Inteligencia Artificial Local (LFM3-1.7B) y Salvaguardas Deterministas.
"""
from app.ai.client import LocalLlmEngine
from app.ai.fallbacks import (
    fallback_explain_anomaly,
    fallback_adjudicate_duplicate,
    fallback_extract_id_card,
    fallback_answer_rag,
)
from app.ai.schemas import (
    AnomalyExplanationResponse,
    AnomalyScanResponse,
    DuplicateAdjudicationSuggestion,
    BatchDuplicateAdjudicationResponse,
    IdCardExtractionRequest,
    IdCardExtractionResponse,
    RagAssistantRequest,
    RagAssistantResponse,
    DocumentCitation,
)

__all__ = [
    "LocalLlmEngine",
    "fallback_explain_anomaly",
    "fallback_adjudicate_duplicate",
    "fallback_extract_id_card",
    "fallback_answer_rag",
    "AnomalyExplanationResponse",
    "AnomalyScanResponse",
    "DuplicateAdjudicationSuggestion",
    "BatchDuplicateAdjudicationResponse",
    "IdCardExtractionRequest",
    "IdCardExtractionResponse",
    "RagAssistantRequest",
    "RagAssistantResponse",
    "DocumentCitation",
]
