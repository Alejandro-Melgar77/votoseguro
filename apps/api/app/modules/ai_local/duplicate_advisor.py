"""
Arbitraje Asistido de Posibles Duplicados del Padrón Electoral con LFM3-1.7B (IA-L2b).
Segunda opinión objetiva sobre pares marcados por pg_trgm / fuzzystrmatch.
Salvaguarda: NUNCA fusiona, bloquea ni altera la resolución de forma automática (Humano en el circuito).
"""
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.client import LocalLlmEngine
from app.ai.fallbacks import fallback_adjudicate_duplicate
from app.ai.schemas import DuplicateAdjudicationSuggestion
from app.db.models.voter import ImportBatch, ImportIssue, Voter


async def adjudicate_duplicate_issue(
    db: AsyncSession,
    issue: ImportIssue,
) -> DuplicateAdjudicationSuggestion:
    """
    Evalúa un ImportIssue de tipo POSSIBLE_DUPLICATE y guarda la sugerencia de IA en la BD.
    """
    # Cargar datos de los dos registros comparados
    cand_name = issue.raw_full_name or ""
    cand_doc = issue.document_id or ""
    cand_node = "Nodo sin especificar"

    match_name = ""
    match_doc = ""
    match_node = "Nodo sin especificar"

    if issue.candidate_voter_id:
        cand_voter = await db.get(Voter, issue.candidate_voter_id)
        if cand_voter:
            cand_name = cand_voter.full_name
            cand_doc = cand_voter.document_id

    if issue.matched_voter_id:
        match_voter = await db.get(Voter, issue.matched_voter_id)
        if match_voter:
            match_name = match_voter.full_name
            match_doc = match_voter.document_id

    # Si no había matched_voter_id, intentar extraer de details
    if not match_name and isinstance(issue.details, dict):
        match_name = issue.details.get("matched_name", "")
        match_doc = issue.details.get("matched_doc", "")

    candidate_dict = {"full_name": cand_name, "document_id": cand_doc, "node_code": cand_node}
    matched_dict = {"full_name": match_name, "document_id": match_doc, "node_code": match_node}
    sim_score = issue.similarity_score
    edit_dist = issue.edit_distance

    prompt_text = (
        f"Evalúa si los siguientes dos registros de votantes corresponden a la misma persona o a personas distintas:\n"
        f"Registro A: Nombre=\"{cand_name}\", Documento=\"{cand_doc}\"\n"
        f"Registro B: Nombre=\"{match_name}\", Documento=\"{match_doc}\"\n"
        f"Métricas léxicas: similitud trigramática={sim_score}, distancia de edición={edit_dist}\n\n"
        f"Responde con un JSON estricto:\n"
        f"- verdict: \"mismo\" | \"distinto\" | \"dudoso\"\n"
        f"- confidence_label: \"ALTA\" | \"MEDIA\" | \"BAJA\"\n"
        f"- short_reason: explicación breve en español de máximo 200 caracteres\n"
        f"- human_action_required: true"
    )

    batch = await db.get(ImportBatch, issue.batch_id)
    org_id = batch.organization_id if batch else None
    elec_id = batch.election_id if batch else None

    suggestion = await LocalLlmEngine.call_structured(
        prompt=prompt_text,
        schema_cls=DuplicateAdjudicationSuggestion,
        fallback_fn=lambda: fallback_adjudicate_duplicate(
            candidate=candidate_dict,
            matched=matched_dict,
            similarity_score=sim_score,
            edit_distance=edit_dist,
            issue_id=str(issue.id),
        ),
        system_instruction=(
            "Eres el evaluador de duplicados de VotoSeguro. Dictamina si dos registros son la misma persona, "
            "personas distintas o dudoso. Responde únicamente en JSON con verdict, confidence_label, short_reason y human_action_required."
        ),
        function_name="IA-L2b_DUPLICATE_ADJUDICATE",
        organization_id=org_id,
        election_id=elec_id,
        db=db,
        sanitized_summary="Segunda opinión asistida de posible duplicado en padrón electoral",
    )

    suggestion.issue_id = str(issue.id)

    # Persistir la sugerencia en import_issue sin alterar resolution (Humano en el circuito)
    issue.ai_verdict = suggestion.verdict
    issue.ai_reason = suggestion.short_reason
    issue.ai_model = suggestion.ai_source
    issue.ai_evaluated_at = datetime.now(timezone.utc)

    await db.flush()
    return suggestion


async def adjudicate_batch_issues(
    db: AsyncSession,
    batch_id: uuid.UUID,
) -> List[DuplicateAdjudicationSuggestion]:
    """
    Evalúa todos los casos de POSSIBLE_DUPLICATE pendientes de un lote de importación.
    """
    stmt = (
        select(ImportIssue)
        .where(
            ImportIssue.batch_id == batch_id,
            ImportIssue.issue_type == "POSSIBLE_DUPLICATE",
        )
        .order_by(ImportIssue.row_number.asc())
    )
    issues = list((await db.execute(stmt)).scalars().all())

    results: List[DuplicateAdjudicationSuggestion] = []
    for issue in issues:
        sugg = await adjudicate_duplicate_issue(db, issue)
        results.append(sugg)

    await db.commit()
    return results
