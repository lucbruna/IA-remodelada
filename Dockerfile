# =============================================================================
# Dockerfile — Agente Local (Turbo Edition)
# =============================================================================
# Build:
#   docker build -t agente-local .
#
# Run:
#   docker run -p 8000:8000 -v agente_data:/app/agente_data agente-local
#
# With Ollama:
#   docker compose up
# =============================================================================

# ─── Stage 1: Base ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# System dependencies for ChromaDB, sentence-transformers, OCR, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*


# ─── Stage 2: Dependencies ──────────────────────────────────────────────────
FROM base AS dependencies

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ─── Stage 3: Final ─────────────────────────────────────────────────────────
FROM base AS final

ENV AGENTE_HOST=0.0.0.0 \
    AGENTE_PORT=8000 \
    AGENTE_MODEL=llama3.2 \
    OLLAMA_HOST=http://ollama:11434

COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Install Playwright browsers (chromium only) in final stage
RUN pip install --no-cache-dir playwright && \
    python -m playwright install chromium && \
    python -m playwright install-deps chromium && \
    rm -rf /root/.cache/pip

# Create application directories
RUN mkdir -p /app/agente_data/conversations \
    /app/agente_data/uploads \
    /app/agente_data/chroma_db \
    /app/agente_data/screenshots \
    /app/agente_data/media \
    /app/plugins

# Copy application code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ || exit 1

# Volumes for persistent data
VOLUME ["/app/agente_data"]

# Expose API port
EXPOSE 8000

# Run the API server
CMD ["python", "agente_api_server.py"]
