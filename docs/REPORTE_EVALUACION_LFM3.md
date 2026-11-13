# Reporte Oficial de Evaluación y Calibración — Modelo votoseguro-lfm3 (Sprint 2.5)

**Fecha de Ejecución:** 2026-11-13 00:18:44 UTC  
**Plataforma Evaluada:** VotoSeguro v2 — Nodo Neuronal Local  
**Modelo:** `votoseguro-lfm3` (Weights 1.7B/1.5B Q4_K_M + Adaptación Electoral)  
**Endpoint de Inferencia:** `http://127.0.0.1:11434/v1`  
**Muestra de Validación:** 24 casos balanceados (IA-L1, IA-L2b, IA-L3, IA-L5)  

---

## 1. Resumen Ejecutivo de Cumplimiento (Sección 7.4 y Salvaguarda #6)

| Métrica Crítica | Umbral Exigido por el Plan | Resultado Obtenido | Estado de Certificación |
| :--- | :---: | :---: | :---: |
| **Porcentaje de JSON Estricto Válido** | **≥ 95.0%** | **100.0%** | 🟢 SUPERADO |
| **Exactitud Específica de Tarea (Accuracy)** | **≥ 85.0%** | **100.0%** | 🟢 SUPERADO |
| **Latencia Promedio de Inferencia Local** | **< 25,000 ms** | **4827.5 ms** | 🟢 ÓPTIMO |

> [!NOTE]
> El modelo local `votoseguro-lfm3` ha cumplido y superado satisfactoriamente los requerimientos de la Sección 7.4 del Plan de Proyecto VotoSeguro v2, certificando su capacidad para operar como motor neuronal primario con fallback determinista transparente.

---

## 2. Desglose Detallado por Función Electoral

| Código de Función | Propósito Electoral | Muestras | JSON Válido (%) | Exactitud (%) | Latencia Media (ms) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **IA-L1** | Explicación de Anomalías Estadísticas | 6 | 100.0% | 100.0% | 6415.5 ms |
| **IA-L2b** | Arbitraje de Duplicados en Padrón | 6 | 100.0% | 100.0% | 4151.4 ms |
| **IA-L3** | Extracción OCR de Cédula de Identidad | 6 | 100.0% | 100.0% | 4422.7 ms |
| **IA-L5** | Asistente RAG & Neutralidad Cívica | 6 | 100.0% | 100.0% | 4320.3 ms |

---

## 3. Garantías de Privacidad y Salvaguardas Electorales

1. **Invariante #14 (Trazabilidad Libre de PII):** Las inferencias neuronales no transmiten ni registran números de documento, nombres de electores ni sentidos de voto fuera del entorno autorizado.
2. **Invariante #15 (Cero Persistencia de Imágenes):** La extracción de cédulas opera estrictamente sobre cadenas de texto OCR en memoria volátil.
3. **Filtro de Neutralidad Cívica (IA-L5):** Las preguntas de inducción partidaria son rechazadas categóricamente, preservando la neutralidad institucional de la plataforma.
4. **Modo Degradado Determinista:** Ante caídas de conectividad o apagado de la máquina local, el backend en Render conmuta sin errores HTTP 500 al motor determinista de salvaguarda.
