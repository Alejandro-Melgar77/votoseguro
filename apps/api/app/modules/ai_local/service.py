"""
Servicio Unificado de Inteligencia Artificial Local (IA-L1, IA-L2b, IA-L3, IA-L5).
"""
import uuid
from typing import Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import LocalLlmEngine
from app.ai.fallbacks import check_rag_guardrails, fallback_answer_rag
from app.ai.schemas import (
    AnomalyScanResponse,
    AssistantConversationTurn,
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
    is_followup_query,
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
        history: Optional[List[AssistantConversationTurn]] = None,
    ) -> RagAssistantResponse:
        """
        IA-L5: Agente conversacional oficial acotado estrictamente al uso de VotoSeguro
        y sus manuales/procedimientos auditados, con comprensión en lenguaje natural y memoria activa.
        """
        clean_q = question.strip()
        recent_history = (history or [])[-8:]

        # 1. Guardrails estrictos de neutralidad política y privacidad (sin depender de signos o formato)
        guardrail_hit = check_rag_guardrails(clean_q)
        if guardrail_hit is not None:
            return guardrail_hit

        # 2. Enriquecer la recuperación si es una repregunta natural dependiente del turno anterior
        retrieval_query = clean_q
        if recent_history and is_followup_query(clean_q):
            prev_user_msgs = [t.content for t in recent_history if t.role == "user"]
            if prev_user_msgs:
                retrieval_query = f"{prev_user_msgs[-1]} {clean_q}"

        top_chunks = retrieve_relevant_chunks(retrieval_query, top_k=5, context_role=context_role)

        # Fallback determinista inteligente (usado si el LLM está offline o deshabilitado)
        fallback_direct = fallback_answer_rag(clean_q, top_chunks)

        # 3. Contexto documental completo + fragmentos prioritarios para comprensión semántica real del LLM
        kb_catalog_summary = "\n".join(
            f"- [{c['doc_id']} | {c['audience']}] {c['title']}: {c['content']}"
            for c in OFFICIAL_KB_CHUNKS
        )
        priority_context = (
            "\n\n".join(f"[{c['doc_id']}: {c['title']}]\n{c['content']}" for c in top_chunks)
            if top_chunks
            else "No hubo coincidencia léxica directa; evalúa la intención semántica contra la base documental completa."
        )
        history_block = (
            "\n".join(
                f"{'Usuario' if t.role == 'user' else 'Asistente'}: {t.content}"
                for t in recent_history
            )
            if recent_history
            else "Sin turnos previos."
        )

        prompt_text = (
            f"Rol reportado por la interfaz: {context_role}\n"
            f"Historial reciente de la conversación:\n{history_block}\n\n"
            f"Mensaje actual del usuario (puede venir sin signos ¿?, sin tildes, con errores tipográficos o como repregunta):\n"
            f"\"{clean_q}\"\n\n"
            f"Fragmentos prioritarios recuperados:\n{priority_context}\n\n"
            f"Base documental oficial completa de VotoSeguro (DOC-01 a DOC-18):\n{kb_catalog_summary}\n\n"
            f"Instrucciones de respuesta:\n"
            f"1. Comprende la intención real en lenguaje natural aunque falten signos de interrogación, tildes o haya errores leves (ej. 'como boto', 'soy encargado que hago', 'y despues de eso que hago?').\n"
            f"2. Responde EXCLUSIVAMENTE sobre el uso del software VotoSeguro y sus procedimientos oficiales.\n"
            f"3. Si el usuario pregunta cómo realizar una acción, responde con una lista numerada de pasos claros, concretos y accionables basados únicamente en la documentación oficial.\n"
            f"4. Adapta o aclara el rol cuando corresponda: Cliente/Votante, Encargado/Delegado (ADMIN_SEGMENT), Administrador (ADMIN_GENERAL / PLATFORM_ADMIN) u Observador.\n"
            f"5. Nunca inventes botones, rutas ni funciones que no estén en la documentación. Nunca pidas ni muestres contraseñas, tokens, claves privadas ni votos individuales.\n"
            f"6. Si la consulta es ajena a VotoSeguro, política, predicción o datos privados, responde con answered_from_docs=false, citations=[], escalate_to_support=true y comienza diciendo 'No lo sé con base en los manuales oficiales de VotoSeguro.' redirigiendo cordialmente al uso del sistema.\n\n"
            f"Devuelve estrictamente JSON válido con:\n"
            f"- question: \"{clean_q}\"\n"
            f"- answer: respuesta en español clara (con pasos numerados si aplica)\n"
            f"- answered_from_docs: boolean\n"
            f"- citations: lista de objetos {{doc_id, title, excerpt}} usados\n"
            f"- escalate_to_support: boolean"
        )

        return await LocalLlmEngine.call_structured(
            prompt=prompt_text,
            schema_cls=RagAssistantResponse,
            fallback_fn=lambda: fallback_direct,
            system_instruction=(
                "Eres el Asistente Conversacional Oficial de VotoSeguro (IA-L5). "
                "Comprendes lenguaje natural libre sin exigir formato rígido. "
                "Respondes únicamente sobre el uso del software VotoSeguro con base en su documentación oficial, "
                "respetando neutralidad política y privacidad absoluta. Responde siempre en JSON válido."
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
