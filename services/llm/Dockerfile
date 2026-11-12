# ==============================================================================
# VotoSeguro v2.0 - Servidor de Inferencia Local LFM3-1.7B
# Modelo: LiquidAI/LFM3-1.7B-GGUF (Cuantización Q4_K_M ~1.05 GB)
# Runtime: llama.cpp server con API compatible OpenAI (/v1/chat/completions)
# ==============================================================================

FROM ghcr.io/ggerganov/llama.cpp:server

# Directorio de modelos
WORKDIR /models

# Metadatos del contenedor
LABEL maintainer="VotoSeguro Architecture Team <dev@votoseguro.org>"
LABEL description="Contenedor de Inferencia Local LFM3-1.7B para Auditoría y Accesibilidad Electoral"

# Variables de entorno por defecto
ENV MODEL_URL="https://huggingface.co/LiquidAI/LFM3-1.7B-GGUF/resolve/main/lfm3-1.7b-q4_k_m.gguf"
ENV MODEL_PATH="/models/lfm3-1.7b-q4_k_m.gguf"
ENV HOST="0.0.0.0"
ENV PORT="8080"
ENV CTX_SIZE="2048"
ENV N_THREADS="4"

# Script de arranque con descarga idempotente del modelo si no está mapeado en volumen
COPY <<-"EOF" /entrypoint.sh
#!/bin/sh
set -e

if [ ! -f "$MODEL_PATH" ]; then
    echo "[VOTOSEGURO-LLM] Modelo LFM3 no encontrado en $MODEL_PATH. Descargando versión cuantizada Q4_K_M..."
    if command -v curl >/dev/null 2>&1; then
        curl -L -o "$MODEL_PATH" "$MODEL_URL"
    elif command -v wget >/dev/null 2>&1; then
        wget -O "$MODEL_PATH" "$MODEL_URL"
    else
        echo "[VOTOSEGURO-LLM] Advertencia: curl/wget no disponibles. Asegúrese de montar el archivo .gguf en el volumen /models"
    fi
fi

echo "[VOTOSEGURO-LLM] Iniciando servidor llama.cpp en $HOST:$PORT con ctx-size $CTX_SIZE..."
exec /server -m "$MODEL_PATH" --host "$HOST" --port "$PORT" -c "$CTX_SIZE" -t "$N_THREADS" --alias "LiquidAI/LFM3-1.7B-Q4_K_M"
EOF

RUN chmod +x /entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
