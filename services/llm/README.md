# Servicio de Inferencia Local LFM3-1.7B (VotoSeguro v2.0)

Este servicio proporciona inferencia de lenguaje natural soberana y local para las funciones asistidas de la plataforma electoral **VotoSeguro**:

1. **IA-L1:** Explicación en lenguaje natural de anomalías estadísticas de participación electoral.
2. **IA-L2b:** Segunda opinión en arbitraje de posibles registros duplicados del padrón.
3. **IA-L3:** Extracción sintáctica estructurada de texto OCR de cédulas de identidad (Cero persistencia de imágenes).
4. **IA-L5:** Asistente documental (RAG) basado exclusivamente en los manuales oficiales de VotoSeguro.

---

## 1. Especificaciones del Modelo

* **Modelo Base:** `LiquidAI/LFM3-1.7B`
* **Formato:** GGUF (`Q4_K_M`)
* **Uso de Memoria RAM:** ~1.05 GB (optimizado para CPUs estándar de 4 núcleos)
* **Runtime:** `llama.cpp:server` con interfaz OpenAI-compatible (`/v1/chat/completions`)
* **Aislamiento de Red:** Expuesto **únicamente en la red interna de Docker** (`http://llm:8080/v1`). No expone puertos hacia internet para proteger la privacidad electoral.

---

## 2. Invocación desde Docker Compose

Para levantar el servicio junto con el ecosistema de VotoSeguro:

```bash
docker compose up -d llm
```

Para verificar que el servicio responde internamente:

```bash
docker compose exec api curl http://llm:8080/v1/models
```

---

## 3. Salvaguarda de Modo Degradado y Disponibilidad en Cloud

Si el contenedor `llm` no se encuentra activo (por ejemplo, en despliegues con cuotas limitadas de RAM como Render Free o durante la ejecución de pruebas unitarias en `pytest`):

* La aplicación FastAPI conmuta **automáticamente al Modo Degradado Determinista** (Salvaguarda #3 del Plan Maestro).
* Los endpoints devuelven respuestas válidas basadas en reglas deterministas, marcando `ai_source: "DETERMINISTIC_FALLBACK"`.
* La emisión atómica del voto (`POST /api/v1/ballot/cast`) **nunca depende del modelo LLM**, garantizando 100% de continuidad del proceso electoral.
