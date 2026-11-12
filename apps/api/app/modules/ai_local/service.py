"""
Servicio Unificado de Inteligencia Artificial Local (IA-L1, IA-L2b, IA-L3, IA-L5).
"""
import uuid
from typing import Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import LocalLlmEngine
from app.ai.fallbacks import fallback_answer_rag
from app.ai.schemas import (
    AnomalyScanResponse,
    BatchDuplicateAdjudicationResponse,
    DocumentCitation,
    DuplicateAdjudicationSuggestion,
    IdCardExtractionResponse,
    RagAssistantResponse,
)
from app.db.models.election import Election
from app.db.models.voter import ImportBatch, ImportIssue
from app.modules.ai_local.anomaly_detector import scan_election_anomalies
from app.modules.ai_local.duplicate_advisor import (
    adjudicate_batch_issues,
    adjudicate_duplicate_issue,
)
from app.modules.ai_local.ocr_extractor import extract_id_card_from_text
from app.modules.ai_local.rag_knowledge import (
    OFFICIAL_KB_CHUNKS,
    retrieve_relevant_chunks,
)


class AiLocalService:
    @staticmethod
    async def get_or_scan_anomalies(
        db: AsyncSession,
        election_id: uuid.UUID,
        simulate_if_clean: bool = False,
    ) -> AnomalyScanResponse:
        """
        IA-L1: Ejecuta el análisis estadístico de participación y genera la explicación en lenguaje natural.
        """
        election = await db.get(Election, election_id)
        if not election:
            raise ValueError(f"Elección no encontrada: {election_id}")

        return await scan_election_anomalies(
            db=db,
            election=election,
            simulate_if_clean=simulate_if_clean,
        )

    @staticmethod
    async def adjudicate_duplicate_issue_by_id(
        db: AsyncSession,
        issue_id: uuid.UUID,
    ) -> DuplicateAdjudicationSuggestion:
        """
        IA-L2b: Segunda opinión de LFM3-1.7B para un caso individual de posible duplicado.
        """
        issue = await db.get(ImportIssue, issue_id)
        if not issue:
            raise ValueError(f"ImportIssue no encontrado: {issue_id}")

        return await adjudicate_duplicate_issue(db, issue)

    @staticmethod
    async def adjudicate_duplicate_batch_by_id(
        db: AsyncSession,
        batch_id: uuid.UUID,
    ) -> BatchDuplicateAdjudicationResponse:
        """
        IA-L2b: Segunda opinión de LFM3-1.7B para todos los duplicados de un lote de importación.
        """
        batch = await db.get(ImportBatch, batch_id)
        if not batch:
            raise ValueError(f"ImportBatch no encontrado: {batch_id}")

        suggestions = await adjudicate_batch_issues(db, batch_id)
        return BatchDuplicateAdjudicationResponse(
            batch_id=str(batch_id),
            total_evaluated=len(suggestions),
            suggestions=suggestions,
            adjudicated_at=str(uuid.uuid4()),
        )

    @staticmethod
    async def extract_id_card_ocr(
        raw_ocr_text: str,
        election_id: Optional[uuid.UUID] = None,
        db: Optional[AsyncSession] = None,
    ) -> IdCardExtractionResponse:
        """
        IA-L3: Extrae los campos de cédula desde texto OCR sin almacenar imágenes (Invariante #15).
        """
        return await extract_id_card_from_text(
            raw_ocr_text=raw_ocr_text,
            election_id=election_id,
            db=db,
        )

    @staticmethod
    async def ask_rag_assistant(
        question: str,
        context_role: str = "VOTER",
        election_id: Optional[uuid.UUID] = None,
        db: Optional[AsyncSession] = None,
    ) -> RagAssistantResponse:
        """
        IA-L5: Asistente RAG oficial acotado a los manuales de VotoSeguro.
        """
        clean_q = question.strip()
        top_chunks = retrieve_relevant_chunks(clean_q, top_k=3, context_role=context_role)

        # Si no hay fragmentos relevantes o cae en temas políticos, fallback_answer_rag aplica el filtro estricto
        fallback_direct = fallback_answer_rag(clean_q, top_chunks)
        if not fallback_direct.answered_from_docs:
            return fallback_direct

        # Si hay fragmentos relevantes y no es partidaria, sintetizar mediante LFM3 con fallback garantizado
        chunks_context = "\n\n".join(
            f"[{c['doc_id']}: {c['title']}]\n{c['content']}" for c in top_chunks
        )
        prompt_text = (
            f"Consulta del usuario ({context_role}): \"{clean_q}\"\n\n"
            f"Fragmentos de los manuales oficiales de VotoSeguro:\n"
            f"{chunks_context}\n\n"
            f"Genera una respuesta en formato JSON estricto con los campos:\n"
            f"- question: \"{clean_q}\"\n"
            f"- answer: explicación clara y amable en español fundamentada exclusivamente en los fragmentos\n"
            f"- answered_from_docs: true\n"
            f"- citations: lista de objetos con doc_id, title y excerpt de los manuales citados\n"
            f"- escalate_to_support: false"
        )

        return await LocalLlmEngine.call_structured(
            prompt=prompt_text,
            schema_cls=RagAssistantResponse,
            fallback_fn=lambda: fallback_direct,
            system_instruction=(
                "Eres el Asistente Electoral Oficial de VotoSeguro. "
                "Responde únicamente con base en los fragmentos de manuales proporcionados. "
                "Sé objetivo, conciso y responde siempre en formato JSON."
            ),
            function_name="IA-L5_RAG_ASSISTANT",
            organization_id=None,
            election_id=election_id,
            db=db,
            sanitized_summary=f"Consulta de asistente documental RAG (rol={context_role})",
        )

    @staticmethod
    def get_official_docs_catalog() -> List[dict[str, Any]]:
        """Devuelve el catálogo de documentos oficiales para consulta administrativa."""
        return OFFICIAL_KB_CHUNKS
