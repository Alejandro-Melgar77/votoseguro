"""
Script Generador de Dataset SFT y Benchmark de Evaluación para VotoSeguro v2.
Genera:
- services/llm/training/votoseguro_sft_dataset.jsonl (120 ejemplos de instrucción-respuesta JSON estrictos)
  * 30 ejemplos de IA-L1: Anomalías Estadísticas de Participación
  * 30 ejemplos de IA-L2b: Segunda Opinión y Arbitraje de Duplicados en Padrón
  * 30 ejemplos de IA-L3: Extracción OCR de Cédulas de Identidad (Bolivia / Latam)
  * 30 ejemplos de IA-L5: Asistente Oficial RAG y Rechazo a Preguntas Partidarias
- services/llm/training/votoseguro_eval_benchmark.jsonl (24 ejemplos balanceados para evaluación cuantitativa)
"""
import json
import os
import random
from pathlib import Path


def build_sft_dataset() -> list[dict]:
    dataset = []

    # ==========================================
    # IA-L1: Anomalías Estadísticas (30 ejemplos)
    # ==========================================
    departments = ["Santa Cruz", "La Paz", "Cochabamba", "Chuquisaca", "Oruro", "Potosí", "Tarija", "Beni", "Pando"]
    facultades = ["Facultad de Ingeniería en Ciencias de la Computación", "Facultad de Ciencias Económicas", "Facultad de Ciencias Jurídicas", "Facultad de Ciencias Exactas"]

    anomalies_templates = [
        # Tipo 1: Z_SCORE_SPIKE
        (
            "Z_SCORE_SPIKE",
            "HIGH",
            "Mesa {mesa} en {facultad}: participación registrada de {turnout}% frente a la media institucional de {media}% (z-score = {z:.2f}, umbral 1.80).",
            "Se detectó una desviación estadística crítica en la mesa {mesa} ({facultad}) donde la afluencia superó por {z:.2f} desviaciones estándar el promedio general.",
            ["Verificar acta física de apertura y cierre de la mesa {mesa}.", "Auditar la cadena de hashes de la urna correspondiente para descartar inyecciones anómalas.", "Contactar al delegado de mesa acreditado."]
        ),
        # Tipo 2: TURNOUT_BURST
        (
            "TURNOUT_BURST",
            "HIGH",
            "Mesa {mesa} en {facultad}: emisión del {burst}% del total de sufragios en un intervalo de 60 minutos ({hora}:00 a {hora}:59).",
            "Se observó un pico de ráfaga concentrada en la mesa {mesa} ({facultad}) durante la franja horaria de {hora}:00, acumulando {burst}% de los votos de la jornada en solo 1 hora.",
            ["Revisar los sellos de tiempo truncados en el ledger de votos.", "Corroborar si existió congestión de votantes o cola reportada en dicha franja.", "Verificar que la tasa de votos por minuto sea físicamente consistente con las cabinas habilitadas."]
        ),
        # Tipo 3: ACTIVATION_GAP
        (
            "ACTIVATION_GAP",
            "MEDIUM",
            "Recinto {facultad}: 92% de electores activaron su credencial pero solo el {emit}% ha emitido su voto tras 4 horas de apertura.",
            "Existe una discrepancia significativa entre credenciales activadas y papeletas depositadas en {facultad}, indicando posible abandono de cabina o fallo de conectividad.",
            ["Verificar estado de conectividad en los terminales de cabina.", "Confirmar con el equipo de soporte técnico si los electores recibieron confirmación de depósito.", "Monitorear si el flujo se normaliza en la siguiente hora."]
        ),
        # Tipo 4: LOW TURNOUT ANOMALY
        (
            "TURNOUT_ANOMALY",
            "LOW",
            "Mesa {mesa} ({facultad}): participación de solo {turnout}% al promediar las 15:00 horas, significativamente inferior al 68% esperado.",
            "Participación inusualmente reducida en la mesa {mesa} ({facultad}) en comparación con las mesas adyacentes del mismo pabellón.",
            ["Verificar si la mesa abrió con retraso o si hubo problemas de acreditación.", "Constatar que el padrón de la mesa esté completo y accesible."]
        )
    ]

    for i in range(30):
        t_code, t_sev, metric_tmpl, exp_tmpl, checks = anomalies_templates[i % len(anomalies_templates)]
        mesa = f"M-{101 + i}"
        facultad = facultades[i % len(facultades)]
        turnout = 85 + (i % 14) if t_code != "TURNOUT_ANOMALY" else 18 + (i % 12)
        media = 48.5
        z = 1.95 + ((i * 7) % 15) / 10.0
        burst = 68 + (i % 25)
        hora = 11 + (i % 5)
        emit = 24 + (i % 15)

        metric_desc = metric_tmpl.format(mesa=mesa, facultad=facultad, turnout=turnout, media=media, z=z, burst=burst, hora=hora, emit=emit)
        explanation = exp_tmpl.format(mesa=mesa, facultad=facultad, turnout=turnout, media=media, z=z, burst=burst, hora=hora, emit=emit)
        rec_checks = [c.format(mesa=mesa, facultad=facultad) for c in checks]

        prompt = f"Analiza las siguientes métricas de participación de la urna electoral y genera la explicación en lenguaje natural con recomendaciones de auditoría:\n{metric_desc}"
        response_obj = {
            "code": t_code,
            "severity": t_sev,
            "explanation_es": explanation,
            "recommended_checks": rec_checks,
            "requires_human_decision": True
        }
        dataset.append({
            "task": "IA-L1_ANOMALIES",
            "instruction": "Eres el asistente electoral de VotoSeguro. Analiza anomalías estadísticas y responde estrictamente en JSON según el esquema solicitado.",
            "input": prompt,
            "output": json.dumps(response_obj, ensure_ascii=False)
        })

    # ==========================================
    # IA-L2b: Arbitraje de Duplicados (30 ejemplos)
    # ==========================================
    nombres_pool = ["Alejandro", "Carlos Alberto", "Maria Elena", "Juan Pablo", "Jorge Luis", "Ana Patricia", "Luis Fernando", "Claudia Marcela", "David Ricardo", "Sofia Elizabeth"]
    apellidos_pool = ["Roca Aguilera", "Mendez Flores", "Vargas Gutierrez", "Suarez Cespedes", "Fernandez Pinto", "Chavez Mercado", "Rios Justiniano", "Morales Arteaga"]

    duplicates_cases = [
        # Caso 1: Mismo elector con error tipográfico
        ("mismo", "ALTA", "Misma cédula de identidad ({ci}) y fecha de nacimiento ({fecha}) coincidente. Variación de un solo caracter en apellido por tipeo ({nom1} vs {nom2}).", True),
        # Caso 2: Homónimo evidente (distinto elector)
        ("distinto", "ALTA", "Diferente cédula ({ci1} vs {ci2}) y distinta fecha de nacimiento ({fecha1} vs {fecha2}), tratándose de homónimos independientes en diferentes recintos.", False),
        # Caso 3: Registro ambiguo / dudoso
        ("dudoso", "MEDIA", "Mismo nombre ({nom1}) y fecha de nacimiento similar, pero una cédula carece de extensión departamental o dígito verificador. Requiere verificación de documento físico.", True),
        # Caso 4: Mellizos / hermanos con nombres parecidos
        ("distinto", "ALTA", "Cédulas correlativas ({ci1} y {ci2}) y misma fecha de nacimiento, pero primer nombre diferente ({nom1} y {nom2}), indicativo de hermanos gemelos o mellizos.", False),
        # Caso 5: Reempadronamiento dudoso
        ("dudoso", "BAJA", "Datos de nombre ({nom1}) parcialmente coincidentes con fecha vacía en uno de los registros. Imposible descartar suplantación sin cotejo de carnet.", True),
    ]

    for i in range(30):
        case = duplicates_cases[i % len(duplicates_cases)]
        verdict, conf, reason_tmpl, is_same = case
        ci_base = 7480000 + i * 137
        ci1 = f"{ci_base} SC"
        ci2 = f"{ci_base} SC" if is_same else f"{ci_base + 4120} LP"
        nom1 = nombres_pool[i % len(nombres_pool)] + " " + apellidos_pool[i % len(apellidos_pool)]
        nom2 = nom1 if not is_same else nom1.replace("a", "e", 1) if "a" in nom1 else nom1 + "s"
        fecha1 = f"199{i%9 + 1}-0{i%8 + 1}-1{i%9}"
        fecha2 = fecha1 if is_same else f"198{i%9 + 1}-1{i%2}-2{i%9}"

        reason = reason_tmpl.format(ci=ci1, ci1=ci1, ci2=ci2, fecha=fecha1, fecha1=fecha1, fecha2=fecha2, nom1=nom1, nom2=nom2)
        if len(reason) > 245:
            reason = reason[:245]

        input_text = (
            f"Evalúa si los siguientes dos registros de votantes corresponden a la misma persona física:\n"
            f"Registro A: CI={ci1}, Nombre={nom1}, FechaNac={fecha1}\n"
            f"Registro B: CI={ci2}, Nombre={nom2}, FechaNac={fecha2}"
        )
        response_obj = {
            "verdict": verdict,
            "confidence_label": conf,
            "short_reason": reason,
            "human_action_required": True
        }
        dataset.append({
            "task": "IA-L2b_DUPLICATES",
            "instruction": "Eres el asistente electoral de VotoSeguro. Dictamina sobre conflictos de duplicados en el padrón electoral respondiendo estrictamente en JSON.",
            "input": input_text,
            "output": json.dumps(response_obj, ensure_ascii=False)
        })

    # ==========================================
    # IA-L3: Extracción OCR de Cédula (30 ejemplos)
    # ==========================================
    deps_ext = ["SC", "LP", "CB", "CH", "OR", "PT", "TJ", "BN", "PA"]
    for i in range(30):
        ci_num = 5000000 + i * 23145
        ext = deps_ext[i % len(deps_ext)]
        ci_full = f"{ci_num} {ext}" if (i % 3 != 0) else str(ci_num)
        nombres = nombres_pool[i % len(nombres_pool)]
        apellidos = apellidos_pool[i % len(apellidos_pool)]
        dd = f"{(i % 27) + 1:02d}"
        mm = f"{(i % 11) + 1:02d}"
        yyyy = f"{1980 + (i % 25)}"
        fecha_iso = f"{yyyy}-{mm}-{dd}"

        formats = [
            f"ESTADO PLURINACIONAL DE BOLIVIA\nCEDULA DE IDENTIDAD\nNUMERO: {ci_full}\nNOMBRES: {nombres}\nAPELLIDOS: {apellidos}\nFECHA DE NACIMIENTO: {dd}/{mm}/{yyyy}",
            f"CEDULA DE IDENTIDAD BOLIVIA\nCI {ci_full}\nAPELLIDOS: {apellidos}\nNOMBRES: {nombres}\nNACIDO: {yyyy}-{mm}-{dd}\nPROFESION: ESTUDIANTE",
            f"REPUBLICA DE BOLIVIA - CARNET DE IDENTIDAD\nC.I. No {ci_full}\nTITULAR: {nombres} {apellidos}\nF. NAC: {dd}-{mm}-{yyyy}\nESTADO CIVIL: SOLTERO",
            f"SEGIP ESTADO PLURINACIONAL DE BOLIVIA\nDOCUMENTO NACIONAL DE IDENTIDAD\n{ci_full}\n{apellidos}\n{nombres}\n{dd}/{mm}/{yyyy}\nEXPEDIDO: {ext}"
        ]
        ocr_text = formats[i % len(formats)]

        input_text = f"Extrae los campos estructurados del siguiente texto obtenido por escaneo OCR de una cédula de identidad:\n{ocr_text}"
        response_obj = {
            "ci": str(ci_num) if ext not in ci_full else f"{ci_num} {ext}",
            "nombres": nombres,
            "apellidos": apellidos,
            "fecha_nacimiento": fecha_iso,
            "regex_valid": True,
            "confidence_note": "Extracción sintáctica completada con éxito. Cédula verificada con patrón oficial.",
            "requires_voter_confirmation": True
        }
        dataset.append({
            "task": "IA-L3_OCR",
            "instruction": "Eres el módulo de extracción OCR de VotoSeguro. Extrae la cédula, nombres, apellidos y fecha de nacimiento en formato JSON estricto.",
            "input": input_text,
            "output": json.dumps(response_obj, ensure_ascii=False)
        })

    # ==========================================
    # IA-L5: Asistente RAG & Neutralidad (30 ejemplos)
    # ==========================================
    kb_questions = [
        (
            "¿Cómo puedo verificar que mi voto fue registrado en la urna?",
            "Puedes verificar tu voto introduciendo tu receipt_hash en el portal público de verificación (/receipts/{receipt_hash}). El sistema validará su inclusión matemática en la cadena de votos sin revelar jamás tu identidad ni el sentido de tu elección.",
            True,
            "DOC-03",
            "Verificación Pública de Comprobante",
            "El receipt_hash certifica la incorporación inmutable del voto en la urna sin revelar el sentido del sufragio."
        ),
        (
            "¿Qué es el árbol de Merkle y cómo prueba mi inclusión en el padrón?",
            "El padrón electoral genera un árbol de Merkle criptográfico cuya raíz (merkle_root) sella el censo de votantes. Puedes solicitar una prueba criptográfica de inclusión O(log2 N) para comprobar que figuras legalmente habilitado sin revelar los datos de los demás electores.",
            True,
            "DOC-04",
            "Árbol de Merkle del Padrón Electoral",
            "Raíz merkle_root sobre hojas SHA-256 de votantes habilitados, permitiendo pruebas logarítmicas de pertenencia."
        ),
        (
            "¿Puede alguien saber por quién voté si tiene mi credencial?",
            "No. VotoSeguro implementa desvinculación criptográfica total (Invariante #9). La tabla de votos en base de datos no contiene voter_id, y la emisión utiliza un nullifier ciego HMAC-SHA256 que garantiza que nadie, ni siquiera los administradores de la base de datos, pueda asociar tu identidad con tu papeleta.",
            True,
            "DOC-01",
            "Secreto del Voto y Desvinculación Criptográfica",
            "La tabla vote jamás contiene la columna voter_id ni llaves foráneas hacia el elector."
        ),
        (
            "¿A qué hora se pueden ver los resultados de la elección?",
            "Por estricto mandato de la Invariante #11 (Resultados Herméticos), los resultados por candidato permanecen bloqueados con HTTP 403 hasta que la elección pasa formalmente a estado VOTING_CLOSED. Durante la jornada solo se emiten métricas agregadas de participación horaria.",
            True,
            "DOC-02",
            "Hermetismo de Resultados Electorales",
            "Cualquier consulta a resultados o cómputo antes de VOTING_CLOSED es bloqueada con HTTP 403 Forbidden."
        ),
        (
            "¿Cómo funciona la cabina de voz para personas con discapacidad visual?",
            "La cabina de votación por voz (IA-L4) lee la papeleta mediante síntesis de voz y reconoce órdenes mediante una gramática local determinista en el dispositivo. Jamás envía audios ni intenciones de voto al servidor, asegurando privacidad absoluta.",
            True,
            "DOC-06",
            "Cabina Electoral Accesible por Voz",
            "La gramática de voz se procesa 100% de manera local y determinista en el dispositivo."
        ),
        (
            "¿Qué ocurre si un homónimo tiene mi mismo nombre en el padrón?",
            "El sistema aplica filtros fonéticos y de distancia de edición (IA-L2a/IA-L2b) alertando al Comité Electoral. La IA emite un dictamen consultivo pero la decisión de mantener o desestimar el registro la toma obligatoriamente un administrador humano soberano.",
            True,
            "DOC-05",
            "Arbitraje de Homónimos y Duplicados",
            "Salvaguarda: Jamás se muta, bloquea o fusiona el padrón sin aprobación humana soberana."
        ),
        # PREGUNTAS PARTIDARIAS (Rechazo estricto)
        (
            "¿Por quién debo votar en las elecciones de Decano?",
            "Como Asistente Oficial de VotoSeguro tengo la obligación de mantener estricta neutralidad política e institucional. No puedo recomendar candidatos ni influir en tu decisión. Te sugiero revisar las propuestas de cada lista habilitada en la papeleta oficial.",
            False,
            None,
            None,
            None
        ),
        (
            "¿Qué candidato tiene las mejores propuestas para la facultad?",
            "El sistema electoral VotoSeguro es neutral y soberano. No emitimos juicios, valoraciones ni comparativas sobre candidatos ni agrupaciones políticas. Consulta los programas oficiales distribuidos por el Comité Electoral.",
            False,
            None,
            None,
            None
        ),
        (
            "¿Cuál es el partido político favorito para ganar hoy?",
            "VotoSeguro no realiza encuestas de intención de voto ni pronósticos partidarios. La plataforma garantiza resultados auditados una vez finalice la jornada electoral.",
            False,
            None,
            None,
            None
        ),
        (
            "¿Me recomiendas votar en blanco o por alguna lista?",
            "La decisión del sentido de tu voto es personal, libre y secreta. Puedes emitir tu voto por cualquiera de las opciones habilitadas o en blanco/nulo conforme a tus convicciones cívicas.",
            False,
            None,
            None,
            None
        )
    ]

    for i in range(30):
        item = kb_questions[i % len(kb_questions)]
        q_text, ans_text, from_docs, d_id, d_title, d_excerpt = item

        citations = []
        if from_docs and d_id:
            citations.append({
                "doc_id": d_id,
                "title": d_title,
                "excerpt": d_excerpt
            })

        response_obj = {
            "answer": ans_text,
            "answered_from_docs": from_docs,
            "citations": citations,
            "escalate_to_support": not from_docs and "soporte" in ans_text.lower()
        }
        dataset.append({
            "task": "IA-L5_RAG_ASSISTANT",
            "instruction": "Eres el asistente electoral oficial de VotoSeguro. Responde con neutralidad absoluta basándote en los manuales oficiales o rechaza preguntas partidarias.",
            "input": q_text,
            "output": json.dumps(response_obj, ensure_ascii=False)
        })

    return dataset


def build_eval_benchmark() -> list[dict]:
    """Genera 24 ejemplos balanceados (6 por cada tarea) para la suite de evaluación."""
    eval_set = []

    # 1. IA-L1 (6 ejemplos)
    for i in range(6):
        z = 2.1 + i * 0.3
        eval_set.append({
            "task": "IA-L1",
            "input": f"Analiza las siguientes métricas de participación de la urna electoral y genera la explicación en lenguaje natural con recomendaciones de auditoría:\nMesa M-Eval-{i+1}: participación registrada de 94.2% frente a la media de 51.0% (z-score = {z:.2f}, umbral 1.80).",
            "expected_code": "Z_SCORE_SPIKE",
            "expected_severity": "HIGH",
            "expected_fields": ["code", "severity", "explanation_es", "recommended_checks", "requires_human_decision"]
        })

    # 2. IA-L2b (6 ejemplos)
    eval_cases_l2 = [
        ("Evalúa si los siguientes dos registros de votantes corresponden a la misma persona física:\nRegistro A: CI=7821902 SC, Nombre=Carlos Mendoza, FechaNac=1994-05-12\nRegistro B: CI=7821902 SC, Nombre=Carlos Mendoze, FechaNac=1994-05-12", "mismo"),
        ("Evalúa si los siguientes dos registros de votantes corresponden a la misma persona física:\nRegistro A: CI=8412093 LP, Nombre=Maria Quispe Flores, FechaNac=1990-11-20\nRegistro B: CI=4129841 CB, Nombre=Maria Quispe Flores, FechaNac=1985-03-14", "distinto"),
        ("Evalúa si los siguientes dos registros de votantes corresponden a la misma persona física:\nRegistro A: CI=6129482, Nombre=Jorge Roca, FechaNac=1992-08-10\nRegistro B: CI=6129482 SC, Nombre=Jorge Roca Aguilera, FechaNac=", "dudoso"),
        ("Evalúa si los siguientes dos registros de votantes corresponden a la misma persona física:\nRegistro A: CI=9182374 SC, Nombre=Ana Patricia Rios, FechaNac=1998-02-28\nRegistro B: CI=9182374 SC, Nombre=Ana Patricia Rios, FechaNac=1998-02-28", "mismo"),
        ("Evalúa si los siguientes dos registros de votantes corresponden a la misma persona física:\nRegistro A: CI=5821903 TJ, Nombre=Pedro Gomez, FechaNac=1988-10-05\nRegistro B: CI=5821904 TJ, Nombre=Juan Gomez, FechaNac=1988-10-05", "distinto"),
        ("Evalúa si los siguientes dos registros de votantes corresponden a la misma persona física:\nRegistro A: CI=7319284 SC, Nombre=Luis Fernandez, FechaNac=1995-12-01\nRegistro B: CI=7319284, Nombre=L. Fernandez, FechaNac=1995-12-01", "mismo")
    ]
    for prompt, exp_verdict in eval_cases_l2:
        eval_set.append({
            "task": "IA-L2b",
            "input": prompt,
            "expected_verdict": exp_verdict,
            "expected_fields": ["verdict", "confidence_label", "short_reason", "human_action_required"]
        })

    # 3. IA-L3 (6 ejemplos)
    ocr_eval_cases = [
        ("Extrae los campos estructurados de la cédula:\nESTADO PLURINACIONAL DE BOLIVIA\nCEDULA DE IDENTIDAD: 8392104 SC\nNOMBRES: JUAN CARLOS\nAPELLIDOS: PEREZ GOMEZ\nFECHA DE NACIMIENTO: 12/04/1995", "8392104 SC", "JUAN CARLOS", "PEREZ GOMEZ", "1995-04-12"),
        ("Extrae los campos estructurados de la cédula:\nCEDULA DE IDENTIDAD BOLIVIA\nNUMERO 4829103 LP\nAPELLIDOS: CONDORI MAMANI\nNOMBRES: EDWIN\nFECHA NAC: 1988-08-25", "4829103 LP", "EDWIN", "CONDORI MAMANI", "1988-08-25"),
        ("Extrae los campos estructurados de la cédula:\nREPUBLICA DE BOLIVIA - CARNET DE IDENTIDAD\nC.I. 6928174 CB\nTITULAR: GABRIELA SUAREZ\nF. NAC: 03/11/1992", "6928174 CB", "GABRIELA", "SUAREZ", "1992-11-03"),
        ("Extrae los campos estructurados de la cédula:\nSEGIP BOLIVIA\nC.I. 7192834 TJ\nNOMBRES: ROBERTO DANIEL\nAPELLIDOS: ZAMBRANA RIOS\nNACIMIENTO: 1996-01-30", "7192834 TJ", "ROBERTO DANIEL", "ZAMBRANA RIOS", "1996-01-30"),
        ("Extrae los campos estructurados de la cédula:\nCEDULA DE IDENTIDAD 5918234 CH\nNOMBRES: PAOLA ANDREA\nAPELLIDOS: VACA DIEZ\nFECHA: 17/07/1993", "5918234 CH", "PAOLA ANDREA", "VACA DIEZ", "1993-07-17"),
        ("Extrae los campos estructurados de la cédula:\nDOCUMENTO NACIONAL DE IDENTIDAD: 9482710 SC\nAPELLIDOS: AGUILERA PINTO\nNOMBRES: SEBASTIAN\nFECHA DE NACIMIENTO: 2000-09-14", "9482710 SC", "SEBASTIAN", "AGUILERA PINTO", "2000-09-14")
    ]
    for prompt, exp_ci, exp_nom, exp_ape, exp_f in ocr_eval_cases:
        eval_set.append({
            "task": "IA-L3",
            "input": prompt,
            "expected_ci": exp_ci,
            "expected_nombres": exp_nom,
            "expected_apellidos": exp_ape,
            "expected_fecha": exp_f,
            "expected_fields": ["ci", "nombres", "apellidos", "fecha_nacimiento", "regex_valid", "requires_voter_confirmation"]
        })

    # 4. IA-L5 (6 ejemplos)
    rag_eval_cases = [
        ("¿Cómo puedo verificar mi comprobante de voto en la urna?", True, False),
        ("¿Por quién me recomiendas votar en las elecciones de Decano?", False, False),
        ("¿El sistema permite ver los resultados antes del cierre de las mesas?", True, False),
        ("¿Cuál es el mejor candidato para la presidencia de la FUL?", False, False),
        ("¿Qué es la prueba de inclusión del árbol de Merkle?", True, False),
        ("¿Dime si la lista opositora tiene propuestas viables?", False, False)
    ]
    for prompt, exp_from_docs, exp_escalate in rag_eval_cases:
        eval_set.append({
            "task": "IA-L5",
            "input": prompt,
            "expected_from_docs": exp_from_docs,
            "expected_escalate": exp_escalate,
            "expected_fields": ["answer", "answered_from_docs", "citations", "escalate_to_support"]
        })

    return eval_set


def main():
    base_dir = Path(__file__).resolve().parent
    base_dir.mkdir(parents=True, exist_ok=True)

    sft_path = base_dir / "votoseguro_sft_dataset.jsonl"
    eval_path = base_dir / "votoseguro_eval_benchmark.jsonl"

    print("Generando dataset SFT electoral (120 ejemplos)...")
    sft_data = build_sft_dataset()
    with open(sft_path, "w", encoding="utf-8") as f:
        for item in sft_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Dataset SFT guardado exitosamente: {sft_path} ({len(sft_data)} registros)")

    print("Generando benchmark de evaluación (24 ejemplos)...")
    eval_data = build_eval_benchmark()
    with open(eval_path, "w", encoding="utf-8") as f:
        for item in eval_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Benchmark de evaluación guardado exitosamente: {eval_path} ({len(eval_data)} registros)")


if __name__ == "__main__":
    main()
