# 08 - Docker, Deploy e Custos v2.0

## 8.1 Docker Compose [ATUALIZADO] - `docker-compose.yml`

```yaml
version: '3.8'

services:
  # ============================================
  # PostgreSQL - Banco de Dados Principal
  # ============================================
  postgres:
    image: postgres:15-alpine
    container_name: viral_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${DB_USER:-viral_admin}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-viral_secret}
      POSTGRES_DB: ${DB_NAME:-viral_videos}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-viral_admin}"]
      interval: 10s
      timeout: 5s
      retries: 5
    # Otimizado para 15GB RAM
    command: >
      postgres
      -c shared_buffers=2GB
      -c effective_cache_size=6GB
      -c maintenance_work_mem=512MB
      -c work_mem=64MB

  # ============================================
  # Redis - Message Broker para Celery
  # ============================================
  redis:
    image: redis:7-alpine
    container_name: viral_redis
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ============================================
  # MinIO - Object Storage (S3-compatible)
  # ============================================
  minio:
    image: minio/minio:latest
    container_name: viral_minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY:-minioadmin123}
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  # ============================================
  # Celery Worker - Processamento de Tasks
  # Otimizado para 4 vCPUs, 15GB RAM, CPU-only
  # ============================================
  worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: viral_worker
    restart: unless-stopped
    # Concurrency=2 para não sobrecarregar CPU com Whisper
    command: celery -A main worker --loglevel=info --concurrency=2
    environment:
      - DATABASE_URL=postgresql://${DB_USER:-viral_admin}:${DB_PASSWORD:-viral_secret}@postgres:5432/${DB_NAME:-viral_videos}
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-minioadmin}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-minioadmin123}
      - MINIO_BUCKET=${MINIO_BUCKET:-viral-videos}
      # APIs
      - APIFY_TOKEN=${APIFY_TOKEN}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - FAL_KEY=${FAL_KEY}
      - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY:-}
      # TTS
      - TTS_PROVIDER=${TTS_PROVIDER:-edge-tts}
      - TTS_VOICE_PT_BR=${TTS_VOICE_PT_BR:-pt-BR-FranciscaNeural}
      # Whisper otimizado para CPU
      - WHISPER_MODEL=${WHISPER_MODEL:-medium}
      # Budget
      - DAILY_BUDGET_LIMIT_USD=${DAILY_BUDGET_LIMIT_USD:-20.00}
      - ABORT_ON_BUDGET_EXCEED=${ABORT_ON_BUDGET_EXCEED:-true}
      # Modo
      - TEST_MODE=${TEST_MODE:-true}
      - TZ=${TZ:-America/Sao_Paulo}
    volumes:
      - ./:/app
      - whisper_models:/root/.cache/whisper
      - ./assets/music:/app/assets/music:ro
    deploy:
      resources:
        limits:
          memory: 8G  # Reserva 8GB para worker (Whisper + FFmpeg)
        reservations:
          memory: 4G
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy

  # ============================================
  # Celery Beat - Agendador de Tasks
  # ============================================
  scheduler:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: viral_scheduler
    restart: unless-stopped
    command: celery -A main beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql://${DB_USER:-viral_admin}:${DB_PASSWORD:-viral_secret}@postgres:5432/${DB_NAME:-viral_videos}
      - REDIS_URL=redis://redis:6379/0
      - TZ=${TZ:-America/Sao_Paulo}
    volumes:
      - ./:/app
    depends_on:
      - worker

  # ============================================
  # FastAPI - Dashboard e API REST
  # ============================================
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: viral_api
    restart: unless-stopped
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000
    environment:
      - DATABASE_URL=postgresql://${DB_USER:-viral_admin}:${DB_PASSWORD:-viral_secret}@postgres:5432/${DB_NAME:-viral_videos}
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-minioadmin}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-minioadmin123}
      - TZ=${TZ:-America/Sao_Paulo}
    volumes:
      - ./:/app
    ports:
      - "8000:8000"
    deploy:
      resources:
        limits:
          memory: 1G
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  minio_data:
    driver: local
  whisper_models:
    driver: local

networks:
  default:
    name: viral_network
```

---

## 8.2 Dockerfile [ATUALIZADO]

```dockerfile
FROM python:3.11-slim

# Metadados
LABEL maintainer="viral-automation"
LABEL version="2.0"

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    build-essential \
    # Para edge-tts
    && rm -rf /var/lib/apt/lists/*

# Define diretório de trabalho
WORKDIR /app

# Copia requirements primeiro (cache de dependências)
COPY requirements.txt .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Pré-baixa modelo Whisper medium (otimizado para CPU)
# Isso acelera a primeira execução
RUN python -c "import whisper; whisper.load_model('medium')" || true

# Copia código da aplicação
COPY . .

# Cria diretório de assets
RUN mkdir -p /app/assets/music

# Variáveis de ambiente padrão
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV WHISPER_MODEL=medium

# Expõe porta para API
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Comando padrão
CMD ["python", "main.py", "help"]
```

---

## 8.3 Estimativa de Custos v2.0

### Custos Mensais Detalhados

| Serviço | Operação | Custo Unit. | Volume/Dia | Volume/Mês | Custo/Mês |
|---------|----------|-------------|------------|------------|-----------|
| **Apify** | Scraping | $2.30/1000 | 200 vídeos | 6.000 | **$14** |
| **Gemini 1.5 Pro** | Análise | $0.002/vídeo | 30 vídeos* | 900 | **$2** |
| **GPT-4o** | Estratégia | $0.01/cada | 10 estratégias | 300 | **$3** |
| **Veo 3.1** | Vídeo (test) | $0.25/cena | 20 cenas | 600 | **$150** |
| **Veo 3.1** | Vídeo (prod) | $0.50/cena | 20 cenas | 600 | **$300** |
| **edge-tts** | Narração | $0 | Ilimitado | Ilimitado | **$0** |
| **ElevenLabs** | Narração (premium) | $0.30/1k chars | 5k chars | 150k | **$45** |
| **Whisper** | Transcrição | $0 (local) | Ilimitado | Ilimitado | **$0** |

*Reduzido devido ao pré-filtro estatístico (≈50% economia)

### Cenários de Custo

| Cenário | APIs | VPS | Total/Mês |
|---------|------|-----|-----------|
| **Teste (mínimo)** | $70 | $40 | **$110** |
| **Produção (edge-tts)** | $170 | $40 | **$210** |
| **Produção (ElevenLabs)** | $215 | $40 | **$255** |
| **Escala (2x volume)** | $340 | $60 | **$400** |

### Budget Diário Recomendado

| Modo | Limite Diário | Vídeos/Dia | Notas |
|------|---------------|------------|-------|
| **Conservador** | $5 | 1-2 | Ideal para início |
| **Moderado** | $10 | 3-4 | Crescimento sustentável |
| **Agressivo** | $20 | 5-8 | Escala rápida |

---

## 8.4 Instruções de Deploy

### Pré-requisitos

```
VPS Ubuntu 24.04 LTS
├── CPU: 4+ vCPUs (AVX2 recomendado para Whisper)
├── RAM: 15+ GB
├── Disco: 100+ GB SSD
├── GPU: Não necessário (CPU-only)
└── IP público
```

### Passo 1: Preparar Sistema

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Instalar Docker Compose v2
sudo apt install docker-compose-plugin -y

# Reiniciar para aplicar grupos
sudo reboot
```

### Passo 2: Clonar e Configurar

```bash
# Criar diretório
sudo mkdir -p /opt/viral-automation
sudo chown $USER:$USER /opt/viral-automation
cd /opt/viral-automation

# Clonar projeto (ou copiar arquivos)
git clone <seu-repositorio> .

# Configurar ambiente
cp .env.example .env
nano .env
```

### Passo 3: Configurar .env

```bash
# OBRIGATÓRIOS
DB_PASSWORD=<senha_forte_32_chars>
MINIO_SECRET_KEY=<senha_forte_32_chars>
APIFY_TOKEN=<seu_token>
GOOGLE_API_KEY=<sua_chave>
OPENAI_API_KEY=<sua_chave>
FAL_KEY=<sua_chave>

# OPCIONAIS (TTS premium)
ELEVENLABS_API_KEY=<sua_chave>

# RECOMENDADOS
DAILY_BUDGET_LIMIT_USD=10.00
TEST_MODE=true
WHISPER_MODEL=medium
```

### Passo 4: Criar Diretórios de Assets

```bash
# Músicas de fundo
mkdir -p assets/music

# Adicionar músicas royalty-free (opcional)
# wget -O assets/music/upbeat_01.mp3 <url>
# wget -O assets/music/chill_01.mp3 <url>
```

### Passo 5: Iniciar Sistema

```bash
# Build e start
docker compose up -d --build

# Verificar status
docker compose ps

# Ver logs
docker compose logs -f worker
```

### Passo 6: Inicialização

```bash
# Criar bucket no MinIO (primeira vez)
docker compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin123
docker compose exec minio mc mb local/viral-videos

# Adicionar primeiro perfil
docker compose exec worker python -c "
from tools.db_tools import db_tools
db_tools.add_profile('exemplo_perfil', 'tecnologia', 3)
print('✅ Perfil adicionado!')
"

# Testar scraping
docker compose exec worker python main.py scrape

# Ver status
docker compose exec worker python main.py status
```

---

## 8.5 Comandos Operacionais

### Comandos Diários

```bash
# Ver status do sistema
docker compose exec worker python main.py status

# Ver orçamento
docker compose exec worker python -c "
from tools.budget_tools import budget_tools
print(budget_tools.get_daily_budget_status())
"

# Executar scraping manual
docker compose exec worker python main.py scrape

# Processar pendentes
docker compose exec worker python main.py process

# Analisar vídeos
docker compose exec worker python main.py analyze

# Gerar estratégias
docker compose exec worker python main.py strategy tecnologia

# Produzir vídeo (modo teste)
docker compose exec worker python main.py produce 1

# Produzir vídeo (modo produção)
docker compose exec worker python main.py produce 1 prod
```

### Manutenção

```bash
# Reiniciar workers
docker compose restart worker scheduler

# Atualizar código
git pull
docker compose up -d --build worker scheduler api

# Backup do banco
docker compose exec postgres pg_dump -U viral_admin viral_videos > backup_$(date +%Y%m%d).sql

# Ver uso de recursos
docker stats

# Limpar logs antigos
docker compose logs --tail=1000 worker > worker_recent.log
```

### Debug

```bash
# Shell do container
docker compose exec worker bash

# Testar TTS
docker compose exec worker python -c "
from tools.tts_tools import tts_tools
import asyncio
result = asyncio.run(tts_tools.generate_tts_edge('Olá, teste de narração', '/tmp/test.mp3'))
print(f'Duração: {result.duration_seconds}s')
"

# Testar Whisper
docker compose exec worker python -c "
from tools.whisper_tools import whisper_tools
print(whisper_tools.get_available_models())
"

# Testar validação JSON
docker compose exec worker python -c "
from models.validators import validate_analysis_output
is_valid, output, error = validate_analysis_output('{\"invalid\": true}')
print(f'Valid: {is_valid}, Error: {error}')
"
```

---

## 8.6 Checklist de Go-Live v2.0

### Infraestrutura
- [ ] VPS Ubuntu 24.04 configurada
- [ ] Docker e Compose instalados
- [ ] 15GB+ RAM disponível
- [ ] 60GB+ disco livre

### Configuração
- [ ] `.env` com todas as chaves
- [ ] PostgreSQL rodando e acessível
- [ ] MinIO rodando com bucket criado
- [ ] Redis rodando

### Funcionalidades
- [ ] Worker Celery rodando
- [ ] Scheduler Celery rodando
- [ ] Pelo menos 1 perfil cadastrado
- [ ] Scraping manual OK
- [ ] Download de vídeo OK
- [ ] Transcrição Whisper OK
- [ ] Análise Gemini OK (JSON válido)
- [ ] Geração de estratégia OK
- [ ] Geração TTS OK
- [ ] Produção completa OK (teste)

### Budget e Segurança
- [ ] Limite diário configurado
- [ ] Modo teste ativo inicialmente
- [ ] Abort on exceed = true
- [ ] Backup do banco configurado

### Monitoramento
- [ ] Logs funcionando
- [ ] API dashboard acessível
- [ ] Métricas de run sendo registradas
