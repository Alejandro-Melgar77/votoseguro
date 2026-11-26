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
    {
        "doc_id": "DOC-13",
        "slug": "pasos-para-votar-cliente",
        "title": "Cómo Emitir el Voto Paso a Paso (Cliente / Votante)",
        "audience": "VOTER",
        "keywords": "votar voto boto botar sufragar emitir paso a paso cabina papeleta credencial cliente votante",
        "content": (
            "Pasos para emitir su voto como Votante en VotoSeguro:\n"
            "1. Active su registro mediante el enlace único (/register/:token) o autoinscripción (/elections/:id/self-register) si está habilitada, y obtenga su credencial secreta de un solo uso (formato VS-XXXX-XXXX-XXXX).\n"
            "2. Cuando la elección esté en estado VOTING_OPEN, ingrese a la Cabina de Votación en /vote.\n"
            "3. Introduzca su Cédula de Identidad (CI) y su Código de Credencial Secreto.\n"
            "4. Revise la papeleta generada automáticamente según su grupo y unidad, y seleccione por cada cargo a su candidato, 'Voto en Blanco' o 'Voto Nulo' (puede activar el Modo Voz Asistida si lo requiere).\n"
            "5. Presione 'Confirmar y Emitir Mi Voto'. El navegador cifra su papeleta con Paillier sin vincular su identidad.\n"
            "6. Guarde o descargue su código de comprobante (receipt_hash) para verificar su inclusión en /verify-receipt."
        ),
    },
    {
        "doc_id": "DOC-14",
        "slug": "guia-encargado-delegado-segmento",
        "title": "Guía Operativa del Encargado / Delegado de Segmento (ADMIN_SEGMENT)",
        "audience": "OPERATOR",
        "keywords": "encargado operador delegado segmento admin_segment padron votantes monitoreo resultados",
        "content": (
            "Funciones y pasos para el Encargado / Delegado de Segmento (rol ADMIN_SEGMENT):\n"
            "1. Inicie sesión en /login y acceda al espacio institucional /workspace para seleccionar la elección asignada.\n"
            "2. Gestión del Padrón (/elections/:id/voters): importe listas CSV de votantes, revise duplicados, apruebe o rechace solicitudes de autoinscripción (PENDING_APPROVAL) y envíe enlaces de activación.\n"
            "3. Cronograma y Fases (/elections/:id/schedule): consulte o gestione las ventanas operativas autorizadas para su alcance.\n"
            "4. Monitoreo en Vivo (/elections/:id/live): supervise la participación en tiempo real sin ver resultados parciales mientras la urna esté abierta.\n"
            "5. Resultados e Integridad (/elections/:id/results y /elections/:id/integrity): consulte el escrutinio tras el cierre y verifique los sellos criptográficos."
        ),
    },
    {
        "doc_id": "DOC-15",
        "slug": "guia-admin-general-configuracion",
        "title": "Guía del Administrador General (ADMIN_GENERAL): Estructura, Candidatos y Ceremonia",
        "audience": "ADMIN",
        "keywords": "admin administrador general configurar candidatos cargos estructura nodos ceremonia llaves publicar delegados",
        "content": (
            "Pasos para configurar una elección como Administrador General (rol ADMIN_GENERAL):\n"
            "1. Ingrese en /login y abra su espacio institucional en /workspace para crear o seleccionar la elección.\n"
            "2. Estructura y Nodos (/elections/:id/structure): defina los grupos de votantes (estamentos), niveles jerárquicos y nodos organizacionales.\n"
            "3. Cargos y Candidatos (/elections/:id/candidates): cree los cargos electorales, circunscripciones y registre a los candidatos con su orden oficial en papeleta.\n"
            "4. Delegados (/elections/:id/delegates): asigne encargados o delegados de segmento (ADMIN_SEGMENT) y observadores si corresponde.\n"
            "5. Ceremonia Criptográfica (/elections/:id/ceremony): genere el par de llaves Paillier y reparta los fragmentos de Shamir (k de n) entre los custodios.\n"
            "6. Publique la elección para sellar el config_hash y pasar a estado SCHEDULED."
        ),
    },
    {
        "doc_id": "DOC-16",
        "slug": "abrir-cerrar-registro-votacion-escrutinio",
        "title": "Cómo Abrir y Cerrar Registro, Votación y Escrutinio (Admin / Encargado)",
        "audience": "ADMIN",
        "keywords": "abrir cerrar iniciar finalizar registro padron votacion urna escrutinio shamir tallied",
        "content": (
            "Pasos para controlar las fases de una elección en VotoSeguro (ADMIN_GENERAL / ADMIN_SEGMENT según permisos):\n"
            "1. Abrir Registro (REGISTRATION_OPEN): desde /elections/:id/voters o /elections/:id/schedule inicie el período de empadronamiento.\n"
            "2. Cerrar Padrón (REGISTRATION_CLOSED): en /elections/:id/voters pulse 'Cerrar Registro Ahora' para congelar la lista ACTIVE y sellar roll_hash y merkle_root.\n"
            "3. Abrir Votación (VOTING_OPEN): habilite la jornada de sufragio desde /elections/:id/voters o /elections/:id/schedule para emitir credenciales y abrir /vote.\n"
            "4. Cerrar Urnas (VOTING_CLOSED): al concluir la jornada, cierre la votación desde el panel de control.\n"
            "5. Desbloqueo y Escrutinio (TALLIED): en el módulo de escrutinio/ceremonia, reúna al menos k fragmentos válidos de Shamir de los custodios para descifrar los totales homomórficos y publicar los resultados en /elections/:id/results."
        ),
    },
    {
        "doc_id": "DOC-17",
        "slug": "portal-publico-auditoria-observador",
        "title": "Portal Público de Auditoría e Integridad (/audit-portal)",
        "audience": "PUBLIC",
        "keywords": "auditoria observador observer portal publico sellos hash ledger integridad verificar",
        "content": (
            "Pasos para auditar una elección sin requerir credenciales especiales (Observador o Ciudadano):\n"
            "1. Ingrese a /audit-portal (o /elections/:id/integrity si tiene rol autenticado).\n"
            "2. Seleccione la elección publicada o finalizada.\n"
            "3. Verifique los sellos criptográficos públicos: ConfigHash, RollHash, MerkleRoot, KeyCeremonyHash y TallyCeremonyHash.\n"
            "4. Ejecute la verificación de cadena de hashes del ledger y revise el historial de cambios de cronograma.\n"
            "5. Si emitió un voto, puede validar su comprobante individual en /verify-receipt."
        ),
    },
    {
        "doc_id": "DOC-18",
        "slug": "consola-platform-admin",
        "title": "Consola de Administrador de Plataforma (PLATFORM_ADMIN)",
        "audience": "ADMIN",
        "keywords": "platform_admin plataforma consola organizaciones solicitudes inquilinos ia nodo",
        "content": (
            "Pasos para el Administrador de Plataforma (rol PLATFORM_ADMIN):\n"
            "1. Inicie sesión en /login con su cuenta de plataforma para acceder a /platform/console.\n"
            "2. Revise y apruebe o rechace las solicitudes institucionales de nuevas elecciones enviadas desde /request-election.\n"
            "3. Supervise las organizaciones registradas y la configuración global del motor de IA cuando corresponda."
        ),
    },
]

_STOPWORDS = {
    "de", "en", "la", "el", "mi", "su", "tu", "un", "al", "lo", "se", "es",
    "si", "no", "ya", "me", "te", "le", "os", "ni", "ha", "va", "ir",
    "como", "puedo", "hacer", "quiero", "tengo", "para", "donde", "cual", "cuales",
    "quien", "cuando", "sobre", "entre", "desde", "hasta", "esta", "este", "esto",
    "esos", "esas", "algo", "unos", "unas", "pero", "porque", "por", "con",
    "sin", "del", "las", "los", "una", "uno", "que", "soy", "hay", "son", "ser",
    "estoy", "hago", "hacen", "debo", "debe", "mas", "muy", "esa", "ese",
    "sistema", "plataforma", "pagina", "web", "app", "votoseguro",
}

_SYNONYM_MAP = {
    "boto": "voto",
    "botar": "votar",
    "botacion": "votacion",
    "sufrago": "voto",
    "sufragar": "votar",
    "sufragio": "voto",
    "eleccion": "votacion",
    "boleta": "papeleta",
    "tarjeton": "papeleta",
    "ticket": "comprobante",
    "recibo": "comprobante",
    "codigo": "credencial",
    "clave": "credencial",
    "carnet": "cedula",
    "dni": "cedula",
    "identidad": "cedula",
    "encargado": "delegado",
    "operador": "delegado",
    "moderador": "delegado",
    "responsable": "delegado",
    "admin": "administrador",
    "administradora": "administrador",
    "cliente": "votante",
    "usuario": "votante",
    "elector": "votante",
    "ciudadano": "votante",
    "configuro": "configurar",
    "configura": "configurar",
    "configuracion": "configurar",
    "crear": "configurar",
    "creo": "configurar",
    "agregar": "configurar",
    "agrego": "configurar",
    "poner": "configurar",
    "pongo": "configurar",
    "subir": "importar",
    "subo": "importar",
    "abro": "abrir",
    "iniciar": "abrir",
    "inicio": "abrir",
    "empezar": "abrir",
    "cierro": "cerrar",
    "finalizar": "cerrar",
    "terminar": "cerrar",
    "verifico": "verificar",
    "revisar": "verificar",
    "reviso": "verificar",
    "chequear": "verificar",
    "comprobar": "verificar",
    "entiendo": "verificar",
    "audio": "voz",
    "hablar": "voz",
    "ciego": "accesibilidad",
    "discapacidad": "accesibilidad",
    "fechas": "cronograma",
    "horario": "cronograma",
    "plazo": "cronograma",
    "lista": "padron",
    "inscritos": "padron",
    "empadronamiento": "registro",
    "inscripcion": "registro",
    "conteo": "escrutinio",
    "contar": "escrutinio",
    "ganador": "resultados",
    "fragmento": "shamir",
    "llave": "ceremonia",
    "llaves": "ceremonia",
}


def _normalize_text(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _tokenize(text: str, remove_stopwords: bool = False) -> List[str]:
    """Tokeniza y normaliza un texto eliminando tildes, signos y opcionalmente stopwords."""
    clean = _normalize_text(text)
    raw_tokens = re.findall(r"[a-z0-9_]{2,}", clean)
    tokens: List[str] = []
    for tok in raw_tokens:
        if remove_stopwords and tok in _STOPWORDS:
            continue
        mapped = _SYNONYM_MAP.get(tok, tok)
        tokens.append(mapped)
    return tokens


def detect_query_roles(query: str, default_role: str = "VOTER") -> List[str]:
    """Detecta los roles mencionados explícita o implícitamente en la consulta."""
    q_norm = _normalize_text(query)
    roles: List[str] = []
    if any(w in q_norm for w in ["votante", "cliente", "elector", "mi voto", "quiero votar", "como boto", "como voto", "comprobante", "papeleta", "cabina"]):
        roles.append("VOTER")
    if any(w in q_norm for w in ["encargado", "operador", "delegado", "segmento"]):
        roles.append("OPERATOR")
    if any(w in q_norm for w in ["admin", "administrador", "plataforma", "candidato", "ceremonia", "estructura", "configur"]):
        roles.append("ADMIN")
    if not roles:
        roles.append(default_role)
    return roles


def is_followup_query(query: str) -> bool:
    """Detecta si el mensaje es una repregunta corta o dependiente del turno anterior."""
    q_norm = _normalize_text(query).strip()
    followup_markers = [
        "despues", "luego", "siguiente", "y si", "y que", "y como", "y donde",
        "y para", "y eso", "de eso", "ahi que", "entonces", "paso siguiente",
        "como asi", "no entendi", "explica", "mas detalle",
    ]
    tokens = _tokenize(query, remove_stopwords=True)
    return len(tokens) <= 2 or any(m in q_norm for m in followup_markers)


def _token_matches(q_tok: str, target_tokens: List[str]) -> bool:
    if q_tok in target_tokens:
        return True
    if len(q_tok) >= 4:
        prefix = q_tok[:5] if len(q_tok) >= 5 else q_tok[:4]
        for t in target_tokens:
            if len(t) >= 4 and (t.startswith(prefix) or q_tok.startswith(t[:4])):
                return True
    return False


def retrieve_relevant_chunks(
    query: str,
    top_k: int = 3,
    context_role: str = "VOTER",
) -> List[dict[str, Any]]:
    """
    Recupera los fragmentos más relevantes de la base de conocimiento usando
    normalización de sinónimos/typos, coincidencia por raíz y filtro de stopwords.
    """
    query_tokens = _tokenize(query, remove_stopwords=True)
    if not query_tokens:
        query_tokens = _tokenize(query, remove_stopwords=False)
    if not query_tokens:
        return []

    inferred_roles = detect_query_roles(query, default_role=context_role)
    scored_chunks: List[Tuple[float, dict[str, Any]]] = []

    for chunk in OFFICIAL_KB_CHUNKS:
        content_tokens = _tokenize(chunk["content"])
        title_tokens = _tokenize(chunk["title"])
        keyword_tokens = _tokenize(chunk["keywords"])

        score = 0.0
        matched_tokens = 0

        for q_tok in query_tokens:
            tok_matches = 0
            if _token_matches(q_tok, keyword_tokens):
                score += 3.0
                tok_matches += 1
            if _token_matches(q_tok, title_tokens):
                score += 2.5
                tok_matches += 1
            if _token_matches(q_tok, content_tokens):
                freq = sum(1 for ct in content_tokens if _token_matches(q_tok, [ct]))
                score += 1.0 + min(freq * 0.2, 1.0)
                tok_matches += 1

            if tok_matches > 0:
                matched_tokens += 1

        if matched_tokens == 0:
            continue

        normalized_score = score / (len(query_tokens) * 3.0)

        audience = chunk.get("audience")
        if audience in inferred_roles or audience == "PUBLIC":
            normalized_score *= 1.2

        scored_chunks.append((
            min(normalized_score, 1.0),
            {
                "doc_id": chunk["doc_id"],
                "slug": chunk["slug"],
                "title": chunk["title"],
                "content": chunk["content"],
                "audience": audience,
                "score": round(min(normalized_score, 1.0), 4),
            }
        ))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored_chunks[:top_k]]
