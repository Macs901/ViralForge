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

# Define diretorio de trabalho
WORKDIR /app

# Copia requirements primeiro (cache de dependencias)
COPY requirements.txt .

# Instala dependencias Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Adiciona click para CLI
RUN pip install --no-cache-dir click>=8.1.0

# Pre-baixa modelo Whisper medium (otimizado para CPU)
# Isso acelera a primeira execucao
RUN python -c "import whisper; whisper.load_model('medium')" || true

# Copia codigo da aplicacao
COPY . .

# Cria diretorios necessarios
RUN mkdir -p /app/assets/music /app/data/temp

# Expoe porta para API
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Comando padrao
CMD ["python", "main.py", "help-commands"]
