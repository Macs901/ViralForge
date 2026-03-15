FROM python:3.11-slim

# Metadados
LABEL maintainer="ViralForge"
LABEL version="2.0"

# Variaveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV WHISPER_MODEL=medium

# Instala dependencias do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala uv
RUN pip install --no-cache-dir uv

# Define diretorio de trabalho
WORKDIR /app

# Copia manifesto de dependencias (cache layer)
COPY pyproject.toml uv.lock* /app/

# Instala dependencias Python via uv
RUN uv sync --frozen || uv sync

# Pre-baixa modelo Whisper medium (otimizado para CPU)
RUN uv run python -c "import whisper; whisper.load_model('medium')" || true

# Copia codigo da aplicacao
COPY . .

# Cria diretorios necessarios
RUN mkdir -p /app/assets/music /app/data/temp

# Expoe portas para API e MCP
EXPOSE 8000
EXPOSE 8001

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Comando padrao
CMD ["uv", "run", "python", "main.py", "help-commands"]
