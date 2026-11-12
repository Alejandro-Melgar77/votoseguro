"""
Base de Conocimiento Curada y Recuperador Semántico para el Asistente Electoral RAG (IA-L5).
Contiene 12 fragmentos oficiales (DOC-01 a DOC-12) que documentan la operativa de VotoSeguro.
"""
import math
import re
import unicodedata
from typing import Any, List, Tuple

OFFICIAL_KB_CHUNKS: List[dict[str, Any]] = [
    {
        "doc_id": "DOC-01",
        "slug": "registro-activacion-enlace",
        "title": "Activación del Elector con Enlace de Registro y Solución si el CI no figura",
        "audience": "VOTER",
        "keywords": "registro activacion enlace token ci carnet padron no aparezco error",
        "content": (
            "Para activarse en la elección, el votante debe acceder al enlace oficial único recibido por correo o proveído "
            "por su institución (con formato /register/:token). En la pantalla de activación, debe ingresar su Cédula de Identidad "
            "(CI) exactamente como figura en su documento físico. Si el sistema indica que el CI no figura en el padrón, "
            "verifique no haber incluido espacios ni caracteres adicionales. Si persiste el error, debe acudir a la Comisión "
            "Electoral de su institución para verificar si fue incluido en el padrón cerrado o si debe solicitar autoinscripción."
        ),
    },
    {
        "doc_id": "DOC-02",
        "slug": "autoinscripcion-abierta-aprobacion",
        "title": "Procedimiento de Autoinscripción Ciudadana (OPEN_WITH_APPROVAL)",
        "audience": "VOTER",
        "keywords": "autoinscripcion registro abierto solicitud aprobacion rechazo pendiente",
        "content": (
            "Cuando una elección se configura en modo de Registro Abierto con Aprobación (OPEN_WITH_APPROVAL), los ciudadanos "
            "pueden registrarse desde la página pública /self-register proporcionando su CI, nombre completo, correo, estamento "
            "y unidad de pertenencia. La solicitud queda en estado PENDING_APPROVAL y es analizada por el Administrador General, "
            "quien verifica la validez del documento antes de aprobar o rechazar la solicitud de empadronamiento."
        ),
    },
    {
        "doc_id": "DOC-03",
        "slug": "credencial-votacion-un-solo-uso",
        "title": "Credencial de Votación de Un Solo Uso (Formato VS-XXXX-XXXX-XXXX)",
        "audience": "VOTER",
        "keywords": "credencial un solo uso codigo vs token secreto extravio",
        "content": (
            "Al completar la activación del registro, el votante recibe una credencial de votación única y secreta con el formato "
            "VS-XXXX-XXXX-XXXX. Esta credencial es de un solo uso y se destruye criptográficamente tras emitir el sufragio "
            "mediante la generación de un nullifier ciego. Si el votante pierde su credencial antes de votar, debe solicitar "
            "la revocación y reemisión formal ante el Administrador General antes de que cierre la fase de votación."
        ),
    },
    {
        "doc_id": "DOC-04",
        "slug": "papeleta-automatica-segmento",
        "title": "Generación Automática de la Papeleta según Grupo y Jerarquía Territorial",
        "audience": "VOTER",
        "keywords": "papeleta automatica cargos circunscripcion facultad carrera nodo path",
        "content": (
            "La papeleta de sufragio se ensambla de forma 100% automática en el momento en que el votante ingresa a la cabina. "
            "El sistema evalúa el estamento del elector (VoterGroup) y la ruta jerárquica de su unidad (node_path) para determinar "
            "exactamente qué cargos y circunscripciones le corresponden sufragar (ej. Rector a nivel universitario, Decano "
            "a nivel de Facultad y Director a nivel de Carrera)."
        ),
    },
    {
        "doc_id": "DOC-05",
        "slug": "voto-blanco-nulo",
        "title": "Opciones Democráticas: Significado del Voto en Blanco y Voto Nulo",
        "audience": "VOTER",
        "keywords": "voto blanco nulo abstencion opciones validez escrutinio",
        "content": (
            "En toda papeleta oficial de VotoSeguro, el elector dispone por norma democrática de las opciones 'Voto en Blanco' "
            "y 'Voto Nulo' para cada cargo en disputa. El voto en blanco indica neutralidad o conformidad sin inclinación "
            "por un candidato particular. El voto nulo expresa desacuerdo formal con las candidaturas propuestas. Ambas opciones "
            "se registran y computan de forma íntegra e inmutable en el escrutinio oficial."
        ),
    },
    {
        "doc_id": "DOC-06",
        "slug": "garantia-secreto-voto",
        "title": "Garantías Criptográficas del Secreto del Voto (Invariantes #8, #9 y #17)",
        "audience": "PUBLIC",
        "keywords": "secreto anonimato privacidad nullifier hmac tabla vote sin voter_id",
        "content": (
            "VotoSeguro garantiza el secreto absoluto del sufragio por diseño: la tabla 'vote' en la base de datos no contiene "
            "ninguna columna voter_id. La unicidad del voto se asegura mediante un nullifier ciego calculado con HMAC-SHA256, "
            "imposible de revertir a la identidad del votante. Además, las marcas de tiempo se truncan al minuto para impedir "
            "ataques de correlación temporal con los registros del servidor web."
        ),
    },
    {
        "doc_id": "DOC-07",
        "slug": "verificacion-recibo-comprobante",
        "title": "Verificación del Comprobante Criptográfico (receipt_hash en /verify-receipt)",
        "audience": "VOTER",
        "keywords": "recibo comprobante receipt_hash verificar urna cadena hashes",
        "content": (
            "Al depositar su papeleta, el votante recibe un código de comprobante criptográfico (receipt_hash). Desde el portal "
            "público /verify-receipt, cualquier elector puede introducir su comprobante para confirmar matemáticamente que su voto "
            "forma parte de la cadena de hashes de la urna (chain_sequence y vote_hash), sin que la plataforma revele jamás "
            "por quién sufragó."
        ),
    },
    {
        "doc_id": "DOC-08",
        "slug": "arbol-merkle-padron",
        "title": "Comprobación de Inclusión en el Padrón con el Árbol de Merkle (Invariante #18)",
        "audience": "PUBLIC",
        "keywords": "arbol merkle inclusion prueba logaritmica merkle_root padron congelado",
        "content": (
            "Al cerrarse la fase de registro, el padrón electoral se congela y se calcula un Árbol de Merkle determinista sobre "
            "todos los votantes habilitados, publicando el merkle_root en el Centro de Integridad. Cualquier ciudadano puede "
            "generar su prueba logarítmica de inclusión O(log2 N) para validar que su registro está contemplado en la elección "
            "sin comprometer la lista completa ni los datos de otros empadronados."
        ),
    },
    {
        "doc_id": "DOC-09",
        "slug": "k-anonimato-resultados",
        "title": "Protección de Privacidad con k-Anonimato en Resultados Desglosados",
        "audience": "PUBLIC",
        "keywords": "k-anonimato privacidad desgloses supresion celdas umbral resultados",
        "content": (
            "Para impedir que un cruce detallado de variables revele la preferencia de un elector en segmentos pequeños, "
            "VotoSeguro aplica un umbral estricto de k-anonimato (por defecto k=5). Si una celda o subunidad territorial tiene "
            "menos de 5 votantes, el recuento individual se suprime o etiqueta como '< k votos' tanto en los reportes web "
            "como en las exportaciones a PDF y Excel."
        ),
    },
    {
        "doc_id": "DOC-10",
        "slug": "accesibilidad-voz-local",
        "title": "Modo de Cabina Accesible por Voz Local (TTS y STT 100% en el Dispositivo)",
        "audience": "VOTER",
        "keywords": "accesibilidad voz tts stt comandos discapacidad visual ceguera cabina",
        "content": (
            "Para votantes con discapacidad visual o motriz, la cabina incluye un modo de accesibilidad por voz. El sistema lee "
            "en voz alta las instrucciones y opciones mediante síntesis TTS local y acepta comandos como 'leer opciones', "
            "'seleccionar opción uno', 'siguiente cargo', 'voto en blanco' o 'confirmar voto'. Todos los comandos se procesan "
            "100% en el dispositivo del usuario mediante una gramática determinista; ningún audio ni transcripción se envía a la red."
        ),
    },
    {
        "doc_id": "DOC-11",
        "slug": "ocr-cedula-sin-guardar-imagenes",
        "title": "Escaneo OCR de Cédula de Identidad con Cero Persistencia de Imágenes",
        "audience": "VOTER",
        "keywords": "ocr cedula carnet camara imagen privacidad invariante 15 descartar",
        "content": (
            "El escáner de cédula de VotoSeguro ejecuta el reconocimiento óptico de caracteres (OCR) de forma local en el navegador "
            "o app móvil. El buffer de la fotografía se descarta inmediatamente de la memoria y nunca se transmite ni guarda en "
            "servidores o bases de datos (cumplimiento de la Invariante #15). Únicamente se envía el texto plano extraído al "
            "backend para normalizar los campos sintácticos."
        ),
    },
    {
        "doc_id": "DOC-12",
        "slug": "cronograma-notificaciones-outbox",
        "title": "Reglas de Reprogramación del Cronograma y Notificaciones a Votantes",
        "audience": "ADMIN",
        "keywords": "cronograma fechas reprogramacion schedule notificaciones correo outbox",
        "content": (
            "El cronograma electoral puede ser modificado por el Administrador General durante las fases permitidas, siempre que "
            "se ingrese un motivo formal y se respete la secuencia lógica de fechas. Toda reprogramación genera una bitácora "
            "de auditoría y despacha notificaciones automáticas por correo electrónico a todos los electores activos, las cuales "
            "quedan registradas con fines de fiscalización en la bandeja notification_outbox."
        ),
    },
]


def _tokenize(text: str) -> List[str]:
    """Tokeniza y normaliza un texto eliminando tildes y símbolos."""
    nfkd = unicodedata.normalize("NFKD", text)
    clean = "".join(c for c in nfkd if not unicodedata.combining(c)).lower()
    tokens = re.findall(r"\b[a-z0-9_]{3,}\b", clean)
    return tokens


def retrieve_relevant_chunks(
    query: str,
    top_k: int = 3,
    context_role: str = "VOTER",
) -> List[dict[str, Any]]:
    """
    Recupera los fragmentos más relevantes de la base de conocimiento curada usando
    similitud léxica ponderada (TF-IDF aproximado con bonus de título y palabras clave).
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    scored_chunks: List[Tuple[float, dict[str, Any]]] = []

    for chunk in OFFICIAL_KB_CHUNKS:
        content_tokens = _tokenize(chunk["content"])
        title_tokens = _tokenize(chunk["title"])
        keyword_tokens = _tokenize(chunk["keywords"])

        # Ponderación por campo
        score = 0.0
        matched_tokens = 0

        for q_tok in query_tokens:
            tok_matches = 0
            if q_tok in keyword_tokens:
                score += 3.0
                tok_matches += 1
            if q_tok in title_tokens:
                score += 2.5
                tok_matches += 1
            if q_tok in content_tokens:
                freq = content_tokens.count(q_tok)
                score += 1.0 + min(freq * 0.2, 1.0)
                tok_matches += 1

            if tok_matches > 0:
                matched_tokens += 1

        # Si no hubo ninguna coincidencia
        if matched_tokens == 0:
            continue

        # Normalizar por longitud de la consulta para evitar sesgos
        normalized_score = score / (len(query_tokens) * 3.5)

        # Ajuste de audiencia
        if chunk.get("audience") == context_role or chunk.get("audience") == "PUBLIC":
            normalized_score *= 1.15

        scored_chunks.append((
            min(normalized_score, 1.0),
            {
                "doc_id": chunk["doc_id"],
                "slug": chunk["slug"],
                "title": chunk["title"],
                "content": chunk["content"],
                "score": round(normalized_score, 4),
            }
        ))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored_chunks[:top_k]]
