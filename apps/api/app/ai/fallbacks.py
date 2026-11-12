"""
Motores deterministas de respaldo (Fallback) para la suite de IA Local de VotoSeguro.
Garantiza el 100% de disponibilidad en modo degradado (Render Free, timeouts o caída del LLM).
Cumple las Invariantes de Privacidad #11, #14 y #15.
"""
import re
import unicodedata
from typing import Any, List, Optional
from app.ai.schemas import (
    AnomalyExplanationResponse,
    DocumentCitation,
    DuplicateAdjudicationSuggestion,
    IdCardExtractionResponse,
    RagAssistantResponse,
)


def _strip_accents(text: str) -> str:
    """Elimina tildes y normaliza a minúsculas para comparaciones semánticas deterministas."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).strip().lower()


# ==========================================
# 1. Fallback IA-L1: Explicación de Anomalías
# ==========================================

def fallback_explain_anomaly(anomaly: dict[str, Any]) -> AnomalyExplanationResponse:
    anomaly_id = str(anomaly.get("anomaly_id", "anom-001"))
    code = str(anomaly.get("code", "PARTICIPATION_ANOMALY"))
    severity = anomaly.get("severity", "MEDIUM")
    if severity not in ("LOW", "MEDIUM", "HIGH"):
        severity = "MEDIUM"

    target_name = anomaly.get("target_name", "Segmento electoral")
    metric_value = float(anomaly.get("metric_value", 0.0))
    baseline = anomaly.get("baseline_value")
    sample_size = int(anomaly.get("sample_size", 0))
    extra = anomaly.get("extra_data", {})

    if code == "PARTICIPATION_ZSCORE_OUTLIER":
        z_val = f"{metric_value:.2f}"
        base_pct = f"{baseline:.1f}%" if baseline is not None else "promedio general"
        explanation = (
            f"La unidad '{target_name}' presenta una tasa de participación estadísticamente atípica "
            f"con una desviación z-score de {z_val} respecto a la media ({base_pct}). "
            f"Esta concentración inusual de electores activos amerita verificación de presencia en recinto."
        )
        checks = [
            f"Verificar registros de conectividad y accesos simultáneos en la unidad '{target_name}'.",
            "Inspeccionar si se realizaron campañas masivas presenciales de asistencia al voto en ese segmento.",
            "Auditar la bitácora de rate-limiting para descartar tráfico automatizado o proxy concentrado.",
        ]
    elif code == "HOURLY_VELOCITY_SPIKE":
        pct_val = f"{metric_value:.1f}%"
        explanation = (
            f"Se detectó un pico abrupto de emisión: el {pct_val} de todos los votos emitidos en la elección "
            f"se concentraron en una única ventana horaria ({target_name}), superando ampliamente la velocidad media esperada."
        )
        checks = [
            "Revisar la bitácora de auditoría para verificar la distribución de direcciones IP durante esa hora.",
            "Comprobar si coincidió con un receso institucional, asamblea o recordatorio por correo masivo.",
            "Certificar la integridad de la cadena de hashes de votos en dicho bloque temporal.",
        ]
    elif code == "ACTIVATION_VS_CAST_GAP":
        explanation = (
            f"En la unidad '{target_name}' se observa una marcada asimetría operativa: alta tasa de activación "
            f"de credenciales ({metric_value:.1f}%) pero una participación efectiva de sufragio significativamente rezagada."
        )
        checks = [
            "Comprobar si los votantes experimentaron dificultades técnicas tras ingresar a la cabina.",
            "Verificar si la elección aún está en curso temprano o si hubo problemas de enlace al depositar la papeleta.",
            "Contactar al delegado de segmento para evaluar el soporte presencial a los electores.",
        ]
    else:
        explanation = (
            f"Desviación estadística identificada en '{target_name}' con valor de métrica {metric_value:.2f}. "
            f"El comportamiento se aparta de la distribución esperada y requiere revisión preventiva."
        )
        checks = [
            "Examinar el historial de eventos en la bitácora de auditoría.",
            "Confirmar la estabilidad operativa de la infraestructura.",
            "Mantener la mesa abierta bajo observación del administrador electoral.",
        ]

    return AnomalyExplanationResponse(
        anomaly_id=anomaly_id,
        code=code,
        severity=severity,
        metrics_summary={
            "target_name": target_name,
            "metric_value": metric_value,
            "baseline_value": baseline,
            "sample_size": sample_size,
            **extra,
        },
        explanation_es=explanation,
        recommended_checks=checks,
        requires_human_decision=True,
        ai_source="DETERMINISTIC_FALLBACK",
    )


# ==========================================
# 2. Fallback IA-L2b: Segunda Opinión Duplicados
# ==========================================

def fallback_adjudicate_duplicate(
    candidate: dict[str, Any],
    matched: dict[str, Any],
    similarity_score: Optional[float] = None,
    edit_distance: Optional[int] = None,
    issue_id: Optional[str] = None,
) -> DuplicateAdjudicationSuggestion:
    cand_name = str(candidate.get("full_name") or candidate.get("raw_full_name") or "")
    match_name = str(matched.get("full_name") or matched.get("raw_full_name") or "")
    cand_doc = str(candidate.get("document_id") or "").strip().upper()
    match_doc = str(matched.get("document_id") or "").strip().upper()

    norm_cand = _strip_accents(cand_name)
    norm_match = _strip_accents(match_name)

    sim = similarity_score if similarity_score is not None else 0.0
    ed = edit_distance if edit_distance is not None else 99

    # Mismo documento exacto
    if cand_doc and match_doc and cand_doc == match_doc:
        verdict = "mismo"
        confidence = "ALTA"
        reason = (
            f"Mismo número de documento '{cand_doc}' con nombres fonéticamente análogos ('{cand_name}' y '{match_name}'). "
            f"Probable doble registro de la misma persona."
        )
    # Nombres casi idénticos con leves diferencias ortográficas / tildes / abreviaturas
    elif norm_cand == norm_match or (sim >= 0.85 and ed <= 2):
        verdict = "mismo"
        confidence = "ALTA" if sim >= 0.90 else "MEDIA"
        reason = (
            f"Similitud léxica muy alta ({sim:.2f}) entre '{cand_name}' y '{match_name}' con variación mínima "
            f"en tildes o iniciales. Muy probable homonimia o registro duplicado."
        )
    # Uno es prefijo o versión abreviada del otro (ej. "José Rodríguez" vs "Jose Rodriguez S.")
    elif norm_cand.startswith(norm_match) or norm_match.startswith(norm_cand) or sim >= 0.70:
        verdict = "dudoso"
        confidence = "MEDIA"
        reason = (
            f"Coincidencia sustancial en nombres principales ('{cand_name}' vs '{match_name}', sim={sim:.2f}), "
            f"posible variación de segundo apellido o inicial. Se sugiere verificación manual de cédula."
        )
    # Documentos marcadamente distintos o nombres con baja coincidencia
    elif sim < 0.50 and ed > 5:
        verdict = "distinto"
        confidence = "MEDIA"
        reason = (
            f"Baja similitud trigramática ({sim:.2f}) y distancia de edición considerable entre '{cand_name}' "
            f"y '{match_name}'. Probablemente personas distintas con nombres parcialmente compartidos."
        )
    else:
        verdict = "dudoso"
        confidence = "BAJA"
        reason = (
            f"Pares con similitud intermedia ({sim:.2f}). No existe certeza automática determinista. "
            f"El Administrador General debe dirimir examinando documentos de soporte."
        )

    # Recortar reason a máximo 250 caracteres
    if len(reason) > 250:
        reason = reason[:247] + "..."

    return DuplicateAdjudicationSuggestion(
        issue_id=issue_id,
        verdict=verdict,
        confidence_label=confidence,
        short_reason=reason,
        human_action_required=True,
        ai_source="DETERMINISTIC_FALLBACK",
    )


# ==========================================
# 3. Fallback IA-L3: Extracción OCR de Cédula
# ==========================================

_RE_CI_PATTERNS = [
    re.compile(r"(?:CI|C\.I\.|CEDULA|N[°oº]|NUMERO)?[:\s#]*([0-9]{5,10}(?:-[0-9A-Z]{1,2})?)", re.IGNORECASE),
    re.compile(r"\b([0-9]{6,9})\s*(?:SC|LP|CB|OR|PT|TJ|CH|BE|PA)\b", re.IGNORECASE),
]

_RE_NAMES = [
    re.compile(r"NOMBRES?[:\s]+([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{2,50})", re.IGNORECASE),
    re.compile(r"NOMBRE(?: COMPLETO)?[:\s]+([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{2,50})", re.IGNORECASE),
]

_RE_SURNAMES = [
    re.compile(r"APELLIDOS?[:\s]+([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{2,50})", re.IGNORECASE),
    re.compile(r"APELLIDO PATERNO[:\s]+([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{2,50})", re.IGNORECASE),
]

_RE_BIRTHDATE = [
    re.compile(r"(?:FECHA DE NACIMIENTO|F\.? NACIMIENTO|NAC\.?)[:\s]*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})", re.IGNORECASE),
    re.compile(r"\b([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{4})\b"),
    re.compile(r"\b([0-9]{4}[/-][0-9]{1,2}[/-][0-9]{1,2})\b"),
]


def fallback_extract_id_card(raw_ocr_text: str) -> IdCardExtractionResponse:
    text = raw_ocr_text.strip()
    if not text:
        return IdCardExtractionResponse(
            ci="",
            nombres="",
            apellidos="",
            fecha_nacimiento=None,
            regex_valid=False,
            confidence_note="El texto OCR provisto está vacío.",
            requires_voter_confirmation=True,
            ai_source="DETERMINISTIC_FALLBACK",
        )

    # 1. Extraer CI
    found_ci = ""
    for pat in _RE_CI_PATTERNS:
        match = pat.search(text)
        if match:
            raw_ci = match.group(1).strip()
            # Limpiar guiones redundantes y normalizar
            found_ci = re.sub(r"[^\w-]", "", raw_ci).upper()
            if not found_ci.startswith("CI-") and found_ci.isdigit():
                found_ci = f"CI-{found_ci}"
            break

    if not found_ci:
        # Fallback de búsqueda de secuencia numérica continua típica de CI
        nums = re.findall(r"\b\d{6,10}\b", text)
        if nums:
            found_ci = f"CI-{nums[0]}"
        else:
            found_ci = "CI-PENDIENTE"

    # 2. Extraer Nombres
    found_nombres = ""
    for pat in _RE_NAMES:
        match = pat.search(text)
        if match:
            found_nombres = match.group(1).strip()
            # Si hay salto de línea en el nombre, tomar solo la línea relevante
            found_nombres = found_nombres.split("\n")[0].strip()
            break

    # 3. Extraer Apellidos
    found_apellidos = ""
    for pat in _RE_SURNAMES:
        match = pat.search(text)
        if match:
            found_apellidos = match.group(1).strip()
            found_apellidos = found_apellidos.split("\n")[0].strip()
            break

    # 4. Extraer Fecha de Nacimiento
    found_birth: Optional[str] = None
    for pat in _RE_BIRTHDATE:
        match = pat.search(text)
        if match:
            found_birth = match.group(1).strip()
            # Normalizar separador a -
            found_birth = found_birth.replace("/", "-")
            break

    # Heurística si no encontró etiquetas formales (ej. plantillas compactas de demostración)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not found_nombres and not found_apellidos and len(lines) >= 2:
        for line in lines:
            if "NOMBRES:" in line.upper():
                found_nombres = line.split(":", 1)[1].strip()
            elif "APELLIDOS:" in line.upper():
                found_apellidos = line.split(":", 1)[1].strip()
            elif "CI:" in line.upper() and not found_ci:
                found_ci = line.split(":", 1)[1].strip()

    # Si aún no hay nombres, buscar nombres en mayúsculas
    if not found_nombres and lines:
        for line in lines:
            if re.match(r"^[A-ZÁÉÍÓÚÑ\s]{4,40}$", line) and not any(kw in line for kw in ["REPUBLICA", "ESTADO", "CEDULA", "IDENTIDAD", "BOLIVIA"]):
                parts = line.split()
                if len(parts) >= 2 and not found_nombres:
                    found_nombres = parts[0]
                    found_apellidos = " ".join(parts[1:])
                    break

    # Normalizar mayúsculas/minúsculas legibles
    found_nombres = " ".join(w.capitalize() for w in found_nombres.split())
    found_apellidos = " ".join(w.capitalize() for w in found_apellidos.split())

    # Validar coherencia por expresiones regulares
    ci_valid = bool(re.match(r"^(?:CI-)?[0-9]{5,10}(?:-[0-9A-Z]{1,2})?$", found_ci, re.IGNORECASE))
    names_valid = bool(found_nombres and len(found_nombres) >= 2)
    apellidos_valid = bool(found_apellidos and len(found_apellidos) >= 2)
    regex_valid = ci_valid and (names_valid or apellidos_valid)

    confidence_note = (
        "Datos de cédula extraídos exitosamente mediante reglas deterministas. "
        "Verifique y confirme que coincidan fielmente con su documento físico."
    )
    if not regex_valid:
        confidence_note = (
            "No se pudieron validar todos los campos de la cédula con certeza sintáctica. "
            "Por favor revise y complete manualmente los campos antes de confirmar."
        )

    return IdCardExtractionResponse(
        ci=found_ci,
        nombres=found_nombres or "VOTANTE",
        apellidos=found_apellidos or "REGISTRADO",
        fecha_nacimiento=found_birth,
        regex_valid=regex_valid,
        confidence_note=confidence_note,
        requires_voter_confirmation=True,
        ai_source="DETERMINISTIC_FALLBACK",
    )


# ==========================================
# 4. Fallback IA-L5: Asistente RAG Documental
# ==========================================

_POLITICAL_INTENT_KEYWORDS = [
    "por quien votar",
    "por quien voto",
    "candidato me recomiendas",
    "quien deberia ganar",
    "quien va ganando",
    "partido",
    "favorito",
    "rector preferido",
    "propuesta politica",
    "deberia votar por",
]


def fallback_answer_rag(
    question: str,
    top_chunks: List[dict[str, Any]],
    min_score_threshold: float = 0.18,
) -> RagAssistantResponse:
    q_norm = _strip_accents(question)

    # Guardrail de Neutralidad Política e Invariante de Privacidad
    if any(kw in q_norm for kw in _POLITICAL_INTENT_KEYWORDS):
        return RagAssistantResponse(
            question=question,
            answer=(
                "No lo sé con base en los manuales oficiales de VotoSeguro. "
                "El Asistente Electoral es estrictamente neutral y solo responde consultas operativas documentadas. "
                "Bajo ningún concepto emite recomendaciones políticas ni información sobre preferencias de voto. "
                "Por favor contacte a la mesa de soporte o al comité electoral institucional."
            ),
            answered_from_docs=False,
            citations=[],
            escalate_to_support=True,
            ai_source="DETERMINISTIC_FALLBACK",
        )

    if not top_chunks:
        return RagAssistantResponse(
            question=question,
            answer=(
                "No lo sé con base en los manuales oficiales de VotoSeguro. "
                "No se encontró documentación oficial que responda a esta consulta operativa. "
                "Por favor, contacte a la mesa de soporte electoral de su institución."
            ),
            answered_from_docs=False,
            citations=[],
            escalate_to_support=True,
            ai_source="DETERMINISTIC_FALLBACK",
        )

    best_chunk = top_chunks[0]
    best_score = float(best_chunk.get("score", 0.0))

    if best_score < min_score_threshold:
        return RagAssistantResponse(
            question=question,
            answer=(
                "No lo sé con base en los manuales oficiales de VotoSeguro. "
                "La consulta no guarda suficiente relación con los procedimientos operativos documentados. "
                "Por favor, contacte a la mesa de soporte de su institución."
            ),
            answered_from_docs=False,
            citations=[],
            escalate_to_support=True,
            ai_source="DETERMINISTIC_FALLBACK",
        )

    # Construir respuesta extractiva limpia fundamentada en los mejores chunks
    citations = []
    excerpts_text = []
    for c in top_chunks[:2]:
        doc_id = str(c.get("doc_id", "DOC-01"))
        title = str(c.get("title", "Manual Oficial VotoSeguro"))
        content = str(c.get("content", ""))
        snippet = content[:160] + "..." if len(content) > 160 else content
        citations.append(DocumentCitation(doc_id=doc_id, title=title, excerpt=snippet))
        excerpts_text.append(content)

    combined_summary = (
        f"Según los manuales oficiales de VotoSeguro ({citations[0].doc_id}: {citations[0].title}):\n\n"
        f"{best_chunk.get('content')}"
    )

    return RagAssistantResponse(
        question=question,
        answer=combined_summary,
        answered_from_docs=True,
        citations=citations,
        escalate_to_support=False,
        ai_source="DETERMINISTIC_FALLBACK",
    )
