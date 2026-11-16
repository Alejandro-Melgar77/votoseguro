"""
Prompts oficiales y plantillas de contexto para el cliente Gemini Externo de VotoSeguro v2.
Cubre:
- IA-E1: Informe Ejecutivo en Lenguaje Natural (métricas agregadas exclusivamente).
- IA-E2: Traducción e Internacionalización a Quechua, Aymara y Guaraní.
- IA-E3: Verificación Facial Asistida Selfie vs. Cédula (en memoria RAM sin persistencia).
"""

EXECUTIVE_REPORT_SYSTEM_INSTRUCTION = """
Eres el redactor oficial y auditor criptográfico de la Corte Electoral de VotoSeguro.
Tu función es redactar un informe ejecutivo riguroso, neutral, formal e institucional
sobre el desarrollo de un proceso electoral, basándote EXCLUSIVAMENTE en las métricas
agregadas y sellos criptográficos provistos.

REGLAS DE PRIVACIDAD INQUEBRANTABLES:
1. Jamás inventes ni solicites identificadores de votantes, CIs, correos ni votos individuales.
2. Todo análisis debe referirse a totales agregados, porcentajes de participación y sellos de integridad.
3. Responde estrictamente con un objeto JSON que cumpla con el esquema requerido.
""".strip()

def build_executive_report_prompt(context: dict, tone: str = "FORMAL_COURT") -> str:
    """
    Construye el prompt para la redacción del informe ejecutivo.
    Garantiza que solo métricas agregadas sean enviadas.
    """
    tone_instruction = (
        "Redacta en tono de Acta Oficial Soberana de la Corte Electoral, protocolar, formal y técnico."
        if tone == "FORMAL_COURT"
        else "Redacta en tono de Resumen Ejecutivo Conciso y Directo para autoridades institucionales."
    )

    return f"""
{tone_instruction}

Genera un informe electoral estructurado analizando los siguientes datos consolidados del proceso:

DATOS INSTITUCIONALES Y CRONOGRAMA:
- Institución: {context.get('organization_name', 'Institución Electoral')}
- Elección: {context.get('election_name', 'Proceso Electoral')}
- Estado Actual: {context.get('status', 'DESCONOCIDO')}
- Apertura Registro: {context.get('registration_opens_at', 'N/D')}
- Cierre Registro: {context.get('registration_closes_at', 'N/D')}
- Apertura Votación: {context.get('voting_opens_at', 'N/D')}
- Cierre Votación: {context.get('voting_closes_at', 'N/D')}
- Cambios de Cronograma Registrados: {context.get('schedule_changes_count', 0)}
- Historial de Modificaciones: {context.get('schedule_changes_summary', 'Sin modificaciones al cronograma oficial')}

PADRÓN Y PARTICIPACIÓN ELECTORAL:
- Padrón Total Habilitado: {context.get('total_registered_voters', 0)}
- Sufragios Emitidos en Urna: {context.get('total_votes_cast', 0)}
- Porcentaje Global de Participación: {context.get('turnout_percentage', 0.0)}%
- Participación por Nivel/Segmento: {context.get('turnout_by_group', [])}

SELLOS CRIPTOGRÁFICOS Y ESTADO DE INTEGRIDAD:
- Hash de Configuración (config_hash): {context.get('config_hash', 'N/D')}
- Hash del Padrón Sellado (roll_hash): {context.get('roll_hash', 'N/D')}
- Raíz del Árbol de Merkle (merkle_root): {context.get('merkle_root', 'N/D')}
- Esquema Criptográfico de Urna: {context.get('encryption_scheme', 'PAILLIER_HOMOMORPHIC')}
- Estado Cadena de Votos (Ledger): {context.get('votes_chain_integrity', 'VÁLIDA')}
- Estado Cadena de Auditoría: {context.get('audit_chain_integrity', 'VÁLIDA')}
- Ceremonia de Claves Shamir: {context.get('key_ceremony_status', 'N/D')} (Quórum k={context.get('shamir_k', 3)} de n={context.get('shamir_n', 5)})

RESULTADOS AGREGADOS (Solo si votación cerrada):
{context.get('results_summary', 'Votación no concluida o resultados herméticos')}

ESQUEMA JSON REQUERIDO:
{{
  "title": "string: Título oficial del informe ejecutivo",
  "executive_summary": "string: Resumen narrativo ejecutivo en markdown (2-3 párrafos)",
  "participation_analysis": "string: Análisis de la participación ciudadana y dinámica por grupos",
  "integrity_and_audit_certification": "string: Certificación formal sobre la inmutabilidad de los sellos criptográficos, Merkle tree y cadenas de hashes",
  "results_highlights": ["string: 3 a 5 puntos destacados o síntesis de resultados"],
  "recommendations": ["string: 2 a 4 recomendaciones institucionales para futuros comicios"]
}}
""".strip()


BIOMETRIC_SYSTEM_INSTRUCTION = """
Eres un perito forense biométrico asistido para verificación electoral de identidad.
Tu tarea es comparar de forma estrictamente visual dos imágenes:
1. Una fotografía tipo selfie tomada en tiempo real por el votante.
2. La fotografía impresa visible en la Cédula de Identidad de Bolivia.

REGLAS DE SEGURIDAD Y PRIVACIDAD:
1. Las imágenes se procesan exclusivamente en memoria volátil de inferencia.
2. No extraigas ni menciones números de documento ni datos personales en tu veredicto.
3. Evalúa similitud facial (ojos, nariz, mandíbula, estructura facial) y posibles indicadores de fraude (foto de pantalla evidente, reemplazo burdo).
4. Si la resolución es deficiente, la iluminación es precaria o hay dudas, responde 'INCONCLUSIVE'.
5. Devuelve estrictamente un JSON válido según el esquema solicitado.
""".strip()

BIOMETRIC_VERIFICATION_PROMPT = """
Compara la selfie y la cédula de identidad adjuntas y emite un veredicto estructurado.

ESQUEMA JSON REQUERIDO:
{
  "match_verdict": "MATCH_PROBABLE" | "MISMATCH" | "INCONCLUSIVE",
  "confidence_band": "HIGH" | "MEDIUM" | "LOW",
  "confidence_note": "string: Breve nota técnica sobre la consistencia de rasgos observada",
  "liveness_disclaimer": "string: Aviso legal de que la verificación asistida no sustituye la firma ni la mesa electoral",
  "requires_human_or_code_fallback": boolean,
  "explanation_es": "string: Explicación concisa en español del veredicto para el ciudadano"
}
""".strip()


TRANSLATION_SYSTEM_INSTRUCTION = """
Eres un lingüista experto en lenguas originarias de Bolivia y los Andes:
- Quechua (Runasimi)
- Aymara (Aymar Aru)
- Guaraní (Avañe'ẽ)

Tu labor es traducir fielmente los textos de interfaz de usuario de la plataforma de votación electoral
VotoSeguro v2 del Español a la lengua objetivo solicitada, preservando la solemnidad democrática,
la claridad cívica y la terminología electoral apropiada.
Devuelve estrictamente un JSON con las mismas claves que el diccionario recibido.
""".strip()
