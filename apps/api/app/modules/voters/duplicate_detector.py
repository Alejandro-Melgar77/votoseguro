"""
Detector de Posibles Duplicados en Padrón Electoral (Historia IA-L2a)
Implementa similitud por trigramas y distancia Levenshtein con compatibilidad
tanto para PostgreSQL (pg_trgm + fuzzystrmatch) como fallback in-memory determinista para SQLite.
"""
import unicodedata
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.voter import Voter


def normalize_text(val: str) -> str:
    """Normaliza texto eliminando acentos, diacríticos, mayúsculas y espacios sobrantes."""
    if not val:
        return ""
    normalized = unicodedata.normalize("NFKD", val)
    ascii_bytes = normalized.encode("ASCII", "ignore")
    cleaned = ascii_bytes.decode("ascii").lower().strip()
    return " ".join(cleaned.split())


def compute_trigrams(text_val: str) -> set[str]:
    """Genera el conjunto de trigramas de una cadena."""
    padded = f"  {text_val} "
    return {padded[i : i + 3] for i in range(len(padded) - 2)}


def trigram_similarity(s1: str, s2: str) -> float:
    """Calcula el coeficiente de similitud de Jaccard sobre trigramas (0.0 a 1.0)."""
    t1 = compute_trigrams(s1)
    t2 = compute_trigrams(s2)
    if not t1 or not t2:
        return 0.0
    intersection = len(t1 & t2)
    union = len(t1 | t2)
    return intersection / union if union > 0 else 0.0


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calcula la distancia de edición de Levenshtein entre dos cadenas."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


async def find_potential_duplicates(
    db: AsyncSession,
    election_id: uuid.UUID,
    candidate_doc: str,
    candidate_name: str,
    candidate_voter_id: uuid.UUID | None = None,
) -> list[tuple[uuid.UUID, str, str, float, int]]:
    """
    Busca posibles duplicados en la misma elección:
    Retorna lista de tuplas: (matched_voter_id, matched_doc, matched_name, similarity_score, edit_distance).
    """
    bind = db.bind
    dialect_name = bind.dialect.name if bind else "postgresql"
    norm_candidate_name = normalize_text(candidate_name)
    norm_candidate_doc = candidate_doc.strip().upper()

    matches: list[tuple[uuid.UUID, str, str, float, int]] = []

    # 1. Intentar ejecución acelerada por PostgreSQL pg_trgm + fuzzystrmatch si estamos en postgres
    if dialect_name == "postgresql":
        try:
            sql = text("""
                SELECT 
                    id, 
                    document_id, 
                    full_name,
                    similarity(lower(full_name), :cand_name) AS sim_score,
                    levenshtein(lower(full_name), :cand_name) AS edit_dist
                FROM voter
                WHERE election_id = :election_id
                  AND (:voter_id IS NULL OR id != :voter_id)
                  AND document_id != :cand_doc
                  AND (
                      similarity(lower(full_name), :cand_name) >= 0.45
                      OR levenshtein(lower(full_name), :cand_name) <= 3
                      OR (levenshtein(document_id, :cand_doc) <= 1 AND similarity(lower(full_name), :cand_name) >= 0.35)
                  )
                ORDER BY sim_score DESC
                LIMIT 10;
            """)
            result = await db.execute(
                sql,
                {
                    "election_id": election_id,
                    "voter_id": candidate_voter_id,
                    "cand_name": norm_candidate_name,
                    "cand_doc": norm_candidate_doc,
                },
            )
            for row in result.fetchall():
                v_id, d_id, f_name, sim, dist = row
                matches.append((v_id, d_id, f_name, float(sim or 0.0), int(dist or 0)))
            return matches
        except Exception:
            # Fallback a motor in-memory si la extensión no está disponible o falla
            matches.clear()

    # 2. Motor determinista en memoria (para SQLite y tests unitarios)
    from sqlalchemy import select
    stmt = select(Voter).where(
        Voter.election_id == election_id,
        Voter.document_id != norm_candidate_doc,
    )
    if candidate_voter_id:
        stmt = stmt.where(Voter.id != candidate_voter_id)

    existing_voters = (await db.execute(stmt)).scalars().all()

    for v in existing_voters:
        norm_v_name = normalize_text(v.full_name)
        norm_v_doc = v.document_id.strip().upper()

        name_sim = trigram_similarity(norm_candidate_name, norm_v_name)
        name_dist = levenshtein_distance(norm_candidate_name, norm_v_name)
        doc_dist = levenshtein_distance(norm_candidate_doc, norm_v_doc)

        is_match = (
            name_sim >= 0.45
            or name_dist <= 3
            or (doc_dist <= 1 and name_sim >= 0.35)
        )

        if is_match:
            matches.append((v.id, v.document_id, v.full_name, round(name_sim, 3), name_dist))

    # Ordenar por similitud descendente
    matches.sort(key=lambda m: m[3], reverse=True)
    return matches[:10]
