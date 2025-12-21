# 🎬 Sistema Autônomo de Vídeos Virais - PRD v2.0

## ⚡ CHANGELOG v2.0

### Novas Funcionalidades
| Feature | Descrição |
|---------|-----------|
| 🎤 **TTS Integrado** | Narração automática com edge-tts (gratuito) + ElevenLabs (fallback) |
| 🎵 **Mixagem de Áudio** | FFmpeg mixa narração + música de fundo + vídeo |
| 📊 **Pré-filtro Estatístico** | Viral Score calculado ANTES de gastar tokens Gemini |
| ✅ **Validação JSON** | Schemas Pydantic garantem outputs estruturados |
| 💰 **Budget Awareness** | Controle de custos com abort automático |
| 📈 **Observabilidade** | Métricas por run, tracking de custos detalhado |
| 🔄 **Versionamento de Prompts** | Rastreabilidade de qual prompt gerou cada análise |

### Correções Críticas
- ❌ ~~Vídeos mudos~~ → ✅ Narração TTS sincronizada
- ❌ ~~JSON inválido do Gemini~~ → ✅ Validação + retry automático
- ❌ ~~Sem controle de custos~~ → ✅ Budget com abort
- ❌ ~~Concatenação simples~~ → ✅ Mixagem profissional

### Otimizações para Hardware
| Componente | Configuração | Motivo |
|------------|--------------|--------|
| Whisper | `medium` | CPU-only, 15GB RAM |
| Celery | `concurrency=2` | Evita OOM com Whisper |
| PostgreSQL | `shared_buffers=2GB` | Aproveita RAM disponível |

---

## 📁 Estrutura do PRD

| Arquivo | Conteúdo |
|---------|----------|
| **01-OVERVIEW.md** | Arquitetura v2, fluxo de produção, stack |
| **02-DATABASE.md** | Schema PostgreSQL (10 tabelas + views + triggers) |
| **03-CONFIG-SCHEMAS.md** | .env, settings.py, Pydantic schemas, validadores |
| **04-TOOLS-NEW.md** | TTS Tools, FFmpeg v2, Budget Tools |
| **05-PRODUCER-AGENT.md** | Producer com TTS + mixagem completa |
| **06-ANALYST-WATCHER.md** | Analyst com validação JSON, Watcher com pré-filtro |
| **07-PROMPTS.md** | Prompts otimizados para JSON estrito |
| **08-DOCKER-DEPLOY.md** | Docker Compose, Dockerfile, custos, deploy |

---

## 🚀 Quick Start

### 1. Clone e Configure
```bash
git clone <repo> && cd viral-automation
cp .env.example .env
# Edite .env com suas API keys
```

### 2. Inicie
```bash
docker compose up -d
```

### 3. Adicione Perfil
```bash
docker compose exec worker python -c "
from tools.db_tools import db_tools
db_tools.add_profile('perfil_instagram', 'tecnologia', 3)
"
```

### 4. Execute
```bash
docker compose exec worker python main.py scrape
docker compose exec worker python main.py status
```

---

## 💰 Custos Estimados

| Cenário | Custo/Mês |
|---------|-----------|
| **Teste (mínimo)** | ~$110 |
| **Produção (edge-tts)** | ~$210 |
| **Produção (ElevenLabs)** | ~$255 |

---

## 📊 Pipeline Completo

```
Instagram
    │
    ▼
┌─────────────┐
│  WATCHER    │ ◄─── Apify ($2.30/1000)
│  (Scraping) │
└─────────────┘
    │
    ▼
┌─────────────┐
│ PRE-FILTER  │ ◄─── Viral Score estatístico (GRÁTIS)
│ (Score 0-1) │      Economiza ~50% tokens Gemini
└─────────────┘
    │ (score >= 0.6)
    ▼
┌─────────────┐
│ PROCESSOR   │ ◄─── Whisper local (GRÁTIS)
│ (Download+  │
│  Transcrição)│
└─────────────┘
    │
    ▼
┌─────────────┐
│  ANALYST    │ ◄─── Gemini 1.5 Pro ($0.002/vídeo)
│ (Análise +  │      Validação JSON Pydantic
│  Validação) │
└─────────────┘
    │ (virality >= 0.7)
    ▼
┌─────────────┐
│ STRATEGIST  │ ◄─── GPT-4o ($0.01/estratégia)
│  (Roteiro)  │
└─────────────┘
    │
    ▼
┌─────────────┐
│  PRODUCER   │ ◄─── TTS + Veo 3.1 + FFmpeg
│             │      edge-tts (GRÁTIS) ou ElevenLabs ($0.30/1k)
│  1. TTS     │      Veo ($0.25-0.50/cena)
│  2. Veo     │
│  3. Mixagem │
└─────────────┘
    │
    ▼
final_video.mp4
(1080x1920, 9:16, com narração + música)
```

---

## 🎯 Principais Decisões Técnicas

### Por que edge-tts como padrão?
- **Gratuito** - Sem custo de API
- **Qualidade** - Vozes Microsoft neurais
- **Fallback** - ElevenLabs se necessário

### Por que Whisper medium?
- **CPU-only** - Sem GPU na VPS
- **15GB RAM** - large-v3 seria lento demais
- **Qualidade** - Suficiente para PT-BR

### Por que pré-filtro estatístico?
- **Economia** - 50% menos tokens Gemini
- **Velocidade** - Filtra antes de baixar
- **Customizável** - Score por nicho

### Por que validação JSON?
- **Robustez** - Sem crashes por output malformado
- **Retry** - Tenta novamente se inválido
- **Rastreabilidade** - Registra erros

---

## 📞 Suporte

- **Logs**: `docker compose logs -f worker`
- **Status**: `python main.py status`
- **Budget**: Ver `budget_tracking` no PostgreSQL
- **Métricas**: Ver `run_metrics` no PostgreSQL

---

**Versão:** 2.0.0  
**Data:** Dezembro 2024  
**Hardware Alvo:** 4 vCPUs, 15GB RAM, CPU-only
# Product Requirements Document (PRD) v2.0
# Sistema Autônomo de Análise e Produção de Vídeos Virais

**Versão:** 2.0.0  
**Data:** Dezembro 2024  
**Stack Principal:** Python + Agno + PostgreSQL + Celery + Veo 3.1 + TTS

---

## CHANGELOG v2.0

| Mudança | Descrição |
|---------|-----------|
| ✅ **TTS Integrado** | Novo módulo de Text-to-Speech (edge-tts + ElevenLabs) |
| ✅ **FFmpeg Avançado** | Mixagem de narração + música + vídeo com sincronia |
| ✅ **Pré-filtro Estatístico** | Viral Score composto antes da análise Gemini |
| ✅ **Validação JSON** | Schemas Pydantic para outputs estruturados |
| ✅ **Budget Awareness** | Abort automático quando custo excede limite |
| ✅ **Observabilidade** | Métricas agregadas por run |
| ⚙️ **Whisper Otimizado** | Modelo `medium` para CPU-only (melhor custo-benefício) |

---

## 1. Visão Geral

### 1.1 Objetivo

Sistema 100% autônomo rodando em VPS que:

1. **Monitora** perfis do Instagram para identificar Reels virais
2. **Pré-filtra** usando Viral Score estatístico (economia de tokens)
3. **Baixa e transcreve** os vídeos qualificados
4. **Analisa** com IA (Gemini) com outputs validados
5. **Gera estratégias** de conteúdo originais (GPT-4o)
6. **Produz vídeos** com narração TTS + vídeo Veo 3.1 + música
7. **Controla custos** com budget awareness e abort automático

### 1.2 Fluxo Principal (v2.0)

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   WATCHER   │───▶│  PRE-FILTER │───▶│  PROCESSOR  │───▶│   ANALYST   │
│   (Apify)   │    │(Viral Score)│    │  (Whisper)  │    │  (Gemini)   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                │
                        ┌───────────────────────────────────────┘
                        ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  PUBLISHER  │◀───│   PRODUCER  │◀───│ STRATEGIST  │◀───│   BUDGET    │
│ (Instagram) │    │(TTS+Veo+Mix)│    │  (GPT-4o)   │    │  CONTROLLER │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### 1.3 Hardware de Referência

```
┌─────────────────────────────────────────────────────┐
│  VPS: Ubuntu 24.04 LTS (macspark-prod)              │
├─────────────────────────────────────────────────────┤
│  CPU: 4 vCPUs AMD EPYC 9354P (AVX2/AVX-512)        │
│  RAM: 15 GB (≈10 GB livre)                          │
│  Disco: 193 GB (≈68 GB livre)                       │
│  GPU: Nenhuma (CPU-only)                            │
└─────────────────────────────────────────────────────┘

Implicações:
- Whisper: modelo "medium" (melhor custo-benefício para CPU)
- Celery: concurrency=2 (evitar OOM)
- FFmpeg: encoding em CPU (mais lento, mas funcional)
```

---

## 2. Arquitetura do Sistema v2.0

### 2.1 Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              VPS (Self-Hosted)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      BUDGET CONTROLLER                                │  │
│  │         Monitora custos, aborta se exceder limite diário             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         CELERY BEAT (Scheduler)                       │  │
│  │              Agendamento: 6h, 12h, 18h, 00h + a cada 30min           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    CELERY WORKERS (concurrency=2)                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│         │              │              │              │              │       │
│         ▼              ▼              ▼              ▼              ▼       │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│  │ Watcher  │   │Processor │   │ Analyst  │   │Strategist│   │ Producer │ │
│  │  Agent   │   │  Agent   │   │  Agent   │   │  Agent   │   │  Agent   │ │
│  │ (Apify)  │   │(Whisper) │   │ (Gemini) │   │ (GPT-4o) │   │(TTS+Veo) │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘ │
│         │              │              │              │              │       │
│         │              │              │              │              │       │
│         │         ┌────┴────┐         │              │         ┌────┴────┐ │
│         │         │         │         │              │         │         │ │
│         ▼         ▼         ▼         ▼              ▼         ▼         ▼ │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                           DATA LAYER                                  │  │
│  │  ┌────────────┐    ┌────────────┐    ┌────────────┐                  │  │
│  │  │ PostgreSQL │    │   MinIO    │    │   Redis    │                  │  │
│  │  │  (Dados)   │    │  (Mídia)   │    │  (Filas)   │                  │  │
│  │  └────────────┘    └────────────┘    └────────────┘                  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      FastAPI (Dashboard/API)                          │  │
│  │                         http://localhost:8000                         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Pipeline de Produção de Vídeo (NOVO)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PRODUCER AGENT - FLUXO DETALHADO                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. RECEBE ESTRATÉGIA APROVADA                                         │
│     └─▶ Roteiro: hook_script + development_script + cta_script         │
│     └─▶ Prompts Veo: [scene1, scene2, scene3...]                       │
│                                                                         │
│  2. GERA NARRAÇÃO (TTS)                                                │
│     ┌─────────────┐                                                     │
│     │  edge-tts   │──▶ narration.mp3 (gratuito)                        │
│     └─────────────┘                                                     │
│            │                                                            │
│            ▼ (fallback se edge-tts falhar)                             │
│     ┌─────────────┐                                                     │
│     │ ElevenLabs  │──▶ narration.mp3 (pago, melhor qualidade)          │
│     └─────────────┘                                                     │
│                                                                         │
│  3. CALCULA DURAÇÃO DO ÁUDIO                                           │
│     └─▶ total_duration = len(narration.mp3)                            │
│     └─▶ Ajusta prompts Veo para cobrir duração                         │
│                                                                         │
│  4. GERA CLIPES DE VÍDEO (VEO 3.1)                                     │
│     ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
│     │   Scene 1   │    │   Scene 2   │    │   Scene 3   │              │
│     │   (4-8s)    │    │   (4-8s)    │    │   (4-8s)    │              │
│     └─────────────┘    └─────────────┘    └─────────────┘              │
│                                                                         │
│  5. MONTAGEM FINAL (FFMPEG)                                            │
│     ┌─────────────────────────────────────────────────────┐            │
│     │                                                     │            │
│     │   [Vídeo Concatenado]                               │            │
│     │          +                                          │            │
│     │   [Narração TTS] (volume: 100%)                     │            │
│     │          +                                          │            │
│     │   [Música de Fundo] (volume: 20%, loop)             │            │
│     │          +                                          │            │
│     │   [Legendas Auto] (opcional)                        │            │
│     │                                                     │            │
│     └─────────────────────────────────────────────────────┘            │
│                          │                                              │
│                          ▼                                              │
│                   final_video.mp4                                       │
│                   (1080x1920, 9:16)                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Stack Tecnológica v2.0

### 3.1 Core

| Componente | Tecnologia | Versão | Justificativa |
|------------|------------|--------|---------------|
| **Linguagem** | Python | 3.11+ | Ecossistema de IA maduro |
| **Framework de Agentes** | Agno (Phidata) | Latest | Multi-agentes nativos |
| **Orquestração** | Celery | 5.3+ | Filas distribuídas |
| **Message Broker** | Redis | 7+ | Rápido e confiável |
| **Banco de Dados** | PostgreSQL | 15+ | JSONB, queries complexas |
| **Object Storage** | MinIO | Latest | S3-compatible, self-hosted |
| **API** | FastAPI | 0.100+ | Async, documentação auto |
| **Containers** | Docker + Compose | Latest | Isolamento e portabilidade |

### 3.2 APIs Externas

| Serviço | Uso | Custo |
|---------|-----|-------|
| **Apify** | Scraping Instagram | $2.30/1000 |
| **Google Gemini** | Análise de vídeo | ~$0.002/vídeo |
| **OpenAI GPT-4o** | Geração de estratégias | ~$0.01/estratégia |
| **Fal.ai Veo 3.1** | Geração de vídeo | $0.50/geração |
| **ElevenLabs** (opcional) | TTS premium | ~$0.30/1000 chars |

### 3.3 Processamento Local (NOVO)

| Componente | Uso | Custo |
|------------|-----|-------|
| **Whisper medium** | Transcrição (CPU-only) | $0 |
| **edge-tts** | Text-to-Speech | $0 |
| **FFmpeg** | Manipulação de vídeo/áudio | $0 |

---

## 4. Estrutura de Pastas do Projeto v2.0

```
/viral-video-automation/
│
├── /agents/
│   ├── __init__.py
│   ├── watcher.py              # Agente de monitoramento (Apify)
│   ├── processor.py            # Agente de processamento (Download + Whisper)
│   ├── analyst.py              # Agente de análise (Gemini Vision)
│   ├── strategist.py           # Agente de estratégia (GPT-4o)
│   └── producer.py             # Agente de produção (TTS + Veo + FFmpeg) [ATUALIZADO]
│
├── /tools/
│   ├── __init__.py
│   ├── apify_tools.py          # Ferramentas de scraping
│   ├── gemini_tools.py         # Upload e análise de vídeo
│   ├── fal_tools.py            # Geração Veo 3.1
│   ├── whisper_tools.py        # Transcrição local
│   ├── ffmpeg_tools.py         # Manipulação de vídeo/áudio [ATUALIZADO]
│   ├── tts_tools.py            # Text-to-Speech [NOVO]
│   ├── storage_tools.py        # MinIO S3
│   ├── db_tools.py             # PostgreSQL
│   └── budget_tools.py         # Controle de custos [NOVO]
│
├── /models/
│   ├── __init__.py
│   ├── schemas.py              # Pydantic models [ATUALIZADO]
│   └── validators.py           # Validação de outputs [NOVO]
│
├── /config/
│   ├── __init__.py
│   ├── settings.py             # Configurações (Pydantic Settings)
│   ├── prompts.py              # Todos os prompts do sistema
│   └── budget.py               # Configurações de orçamento [NOVO]
│
├── /database/
│   ├── init.sql                # Schema inicial [ATUALIZADO]
│   └── /migrations/            # Migrações futuras
│
├── /workflows/
│   ├── __init__.py
│   ├── daily_scrape.py         # Workflow de scraping
│   ├── process_pending.py      # Workflow de processamento
│   ├── generate_strategy.py    # Workflow de estratégia
│   └── produce_video.py        # Workflow de produção [ATUALIZADO]
│
├── /api/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   └── routes/
│
├── /assets/                    # [NOVO]
│   └── /music/                 # Músicas de fundo royalty-free
│       ├── upbeat_01.mp3
│       ├── chill_01.mp3
│       └── energetic_01.mp3
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt            # [ATUALIZADO]
├── celery_app.py
├── main.py
├── .env.example
└── README.md
```
# 02 - Schema do Banco de Dados v2.0 (PostgreSQL)

## Mudanças v2.0

| Tabela | Mudança |
|--------|---------|
| `viral_videos` | + `statistical_viral_score` (pré-filtro) |
| `video_analyses` | + `prompt_version` (versionamento) |
| `generated_strategies` | + `tts_config`, `music_track` |
| `produced_videos` | + `tts_file_path`, `narration_duration` |
| `budget_tracking` | **NOVA** - controle de custos |
| `prompt_versions` | **NOVA** - versionamento de prompts |
| `run_metrics` | **NOVA** - observabilidade |

---

## Arquivo: `database/init.sql`

```sql
-- ============================================
-- EXTENSÕES
-- ============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TABELA: Perfis Monitorados
-- ============================================
CREATE TABLE monitored_profiles (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    platform VARCHAR(20) DEFAULT 'instagram',
    niche VARCHAR(100),
    priority INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    
    -- Configurações de nicho para viral score
    niche_avg_views INTEGER DEFAULT 50000,
    niche_avg_likes INTEGER DEFAULT 5000,
    niche_avg_comments INTEGER DEFAULT 500,
    
    last_scraped_at TIMESTAMP,
    total_videos_collected INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- TABELA: Vídeos Virais Coletados [ATUALIZADO]
-- ============================================
CREATE TABLE viral_videos (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES monitored_profiles(id) ON DELETE SET NULL,
    
    -- Identificadores únicos
    platform_id VARCHAR(100) UNIQUE NOT NULL,
    shortcode VARCHAR(50) UNIQUE,
    source_url TEXT NOT NULL,
    
    -- Métricas de engajamento
    views_count INTEGER DEFAULT 0,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    shares_count INTEGER DEFAULT 0,
    saves_count INTEGER DEFAULT 0,
    engagement_rate DECIMAL(5,2),
    
    -- [NOVO] Viral Score Estatístico (pré-filtro)
    statistical_viral_score DECIMAL(5,4),  -- 0.0000 a 1.0000
    recency_score DECIMAL(3,2),            -- 0.00 a 1.00
    normalized_views DECIMAL(5,4),
    normalized_engagement DECIMAL(5,4),
    passes_prefilter BOOLEAN DEFAULT false,
    
    -- Conteúdo original
    caption TEXT,
    hashtags JSONB DEFAULT '[]',
    mentions JSONB DEFAULT '[]',
    first_comment TEXT,
    
    -- Metadados do vídeo
    duration_seconds INTEGER,
    width INTEGER,
    height INTEGER,
    aspect_ratio VARCHAR(10),
    
    -- Arquivos locais (caminhos no MinIO)
    video_file_path TEXT,
    thumbnail_path TEXT,
    audio_file_path TEXT,
    
    -- Transcrição
    transcription TEXT,
    transcription_language VARCHAR(10),
    transcription_confidence DECIMAL(3,2),
    
    -- Timestamps
    posted_at TIMESTAMP,
    scraped_at TIMESTAMP DEFAULT NOW(),
    
    -- Status de processamento
    is_downloaded BOOLEAN DEFAULT false,
    is_transcribed BOOLEAN DEFAULT false,
    is_analyzed BOOLEAN DEFAULT false,
    processing_error TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- TABELA: Versionamento de Prompts [NOVA]
-- ============================================
CREATE TABLE prompt_versions (
    id SERIAL PRIMARY KEY,
    prompt_type VARCHAR(50) NOT NULL,      -- 'analysis', 'strategy', 'producer'
    version VARCHAR(20) NOT NULL,           -- 'v1.0', 'v1.1', etc.
    prompt_text TEXT NOT NULL,
    
    -- Metadados
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    
    -- Performance tracking
    total_uses INTEGER DEFAULT 0,
    avg_quality_score DECIMAL(3,2),
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(prompt_type, version)
);

-- Inserir versões iniciais dos prompts
INSERT INTO prompt_versions (prompt_type, version, description, is_active) VALUES
('analysis', 'v1.0', 'Prompt inicial de análise Gemini', true),
('strategy', 'v1.0', 'Prompt inicial de estratégia GPT-4o', true),
('producer', 'v1.0', 'Prompt inicial de produção', true);

-- ============================================
-- TABELA: Análises de Vídeo [ATUALIZADO]
-- ============================================
CREATE TABLE video_analyses (
    id SERIAL PRIMARY KEY,
    video_id INTEGER REFERENCES viral_videos(id) ON DELETE CASCADE UNIQUE,
    
    -- [NOVO] Versionamento de prompt
    prompt_version_id INTEGER REFERENCES prompt_versions(id),
    
    -- Análise do Hook (0-3 segundos)
    hook_analysis JSONB,
    
    -- Análise do Desenvolvimento
    development JSONB,
    
    -- Análise do CTA
    cta_analysis JSONB,
    
    -- Fatores de Viralização
    viral_factors JSONB,
    
    -- Elementos Visuais
    visual_elements JSONB,
    
    -- Elementos de Áudio
    audio_elements JSONB,
    
    -- Scores calculados
    virality_score DECIMAL(3,2),
    replicability_score DECIMAL(3,2),
    production_quality_score DECIMAL(3,2),
    
    -- [NOVO] Validação do output
    is_valid_json BOOLEAN DEFAULT true,
    validation_errors JSONB,
    
    -- Resposta raw do Gemini (backup)
    raw_gemini_response TEXT,
    
    -- Metadados
    model_used VARCHAR(50) DEFAULT 'gemini-1.5-pro',
    tokens_used INTEGER,
    analysis_cost_usd DECIMAL(10,6),
    analyzed_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- TABELA: Estratégias Geradas [ATUALIZADO]
-- ============================================
CREATE TABLE generated_strategies (
    id SERIAL PRIMARY KEY,
    source_video_id INTEGER REFERENCES viral_videos(id) ON DELETE SET NULL,
    prompt_version_id INTEGER REFERENCES prompt_versions(id),
    
    -- Identificação
    title VARCHAR(255) NOT NULL,
    concept TEXT,
    target_niche VARCHAR(100),
    
    -- Roteiro completo
    hook_script TEXT,
    hook_duration VARCHAR(10) DEFAULT '0-3s',
    development_script TEXT,
    development_duration VARCHAR(10) DEFAULT '3-25s',
    cta_script TEXT,
    cta_duration VARCHAR(10) DEFAULT '25-30s',
    full_script TEXT,
    
    -- [NOVO] Configuração de TTS
    tts_config JSONB DEFAULT '{
        "provider": "edge-tts",
        "voice": "pt-BR-FranciscaNeural",
        "rate": "+0%",
        "pitch": "+0Hz"
    }',
    
    -- [NOVO] Música de fundo
    music_track VARCHAR(100),              -- ex: 'upbeat_01.mp3'
    music_volume DECIMAL(3,2) DEFAULT 0.20, -- 20% do volume
    
    -- Prompts para Veo 3.1
    veo_prompts JSONB,
    
    -- Metadados de publicação
    suggested_hashtags JSONB,
    suggested_caption TEXT,
    best_posting_time VARCHAR(50),
    suggested_music TEXT,
    
    -- Status
    status VARCHAR(20) DEFAULT 'draft',
    
    -- Custos
    estimated_production_cost_usd DECIMAL(10,4),
    
    -- Validação
    is_valid_json BOOLEAN DEFAULT true,
    validation_errors JSONB,
    
    -- Metadados
    model_used VARCHAR(50) DEFAULT 'gpt-4o',
    tokens_used INTEGER,
    generation_cost_usd DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- TABELA: Vídeos Produzidos [ATUALIZADO]
-- ============================================
CREATE TABLE produced_videos (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES generated_strategies(id) ON DELETE SET NULL,
    production_batch_id UUID DEFAULT uuid_generate_v4(),
    
    -- [NOVO] Arquivos de áudio
    tts_file_path TEXT,                    -- Caminho da narração
    tts_provider VARCHAR(20),              -- 'edge-tts' ou 'elevenlabs'
    narration_duration_seconds DECIMAL(6,2),
    
    -- Jobs do Fal.ai
    veo_jobs JSONB,
    
    -- Arquivos finais (MinIO)
    clips_paths JSONB,
    concatenated_video_path TEXT,          -- Vídeo sem áudio
    final_video_path TEXT,                 -- Vídeo com narração + música
    
    -- [NOVO] Metadados de mixagem
    music_track_used VARCHAR(100),
    music_volume_used DECIMAL(3,2),
    
    -- Metadados do vídeo final
    final_duration_seconds INTEGER,
    final_resolution VARCHAR(20),
    final_file_size_mb DECIMAL(10,2),
    
    -- Custos detalhados
    tts_cost_usd DECIMAL(10,4) DEFAULT 0,
    veo_cost_usd DECIMAL(10,4),
    total_production_cost_usd DECIMAL(10,4),
    
    -- Publicação
    is_published BOOLEAN DEFAULT false,
    published_platform VARCHAR(20),
    published_url TEXT,
    published_at TIMESTAMP,
    
    -- Métricas pós-publicação
    post_views INTEGER DEFAULT 0,
    post_likes INTEGER DEFAULT 0,
    post_comments INTEGER DEFAULT 0,
    post_shares INTEGER DEFAULT 0,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- TABELA: Controle de Orçamento [NOVA]
-- ============================================
CREATE TABLE budget_tracking (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    
    -- Limites configurados
    daily_budget_limit_usd DECIMAL(10,2) DEFAULT 20.00,
    monthly_budget_limit_usd DECIMAL(10,2) DEFAULT 500.00,
    
    -- Gastos por serviço
    apify_cost_usd DECIMAL(10,4) DEFAULT 0,
    gemini_cost_usd DECIMAL(10,4) DEFAULT 0,
    openai_cost_usd DECIMAL(10,4) DEFAULT 0,
    veo_cost_usd DECIMAL(10,4) DEFAULT 0,
    elevenlabs_cost_usd DECIMAL(10,4) DEFAULT 0,
    
    -- Totais
    total_cost_usd DECIMAL(10,4) DEFAULT 0,
    
    -- Status
    budget_exceeded BOOLEAN DEFAULT false,
    budget_exceeded_at TIMESTAMP,
    
    -- Contadores
    api_calls_count INTEGER DEFAULT 0,
    videos_produced INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(date)
);

-- ============================================
-- TABELA: Métricas de Execução [NOVA]
-- ============================================
CREATE TABLE run_metrics (
    id SERIAL PRIMARY KEY,
    run_id UUID DEFAULT uuid_generate_v4(),
    
    -- Identificação
    task_name VARCHAR(100) NOT NULL,
    agent_name VARCHAR(50),
    
    -- Timing
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_seconds DECIMAL(10,3),
    
    -- Recursos processados
    items_input INTEGER DEFAULT 0,
    items_processed INTEGER DEFAULT 0,
    items_failed INTEGER DEFAULT 0,
    
    -- Custos desta run
    estimated_cost_usd DECIMAL(10,4) DEFAULT 0,
    actual_cost_usd DECIMAL(10,4),
    
    -- Status
    status VARCHAR(20) DEFAULT 'running',  -- running, completed, failed, aborted
    error_message TEXT,
    
    -- Detalhes
    details JSONB,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- TABELA: Logs de Execução (existente, mantida)
-- ============================================
CREATE TABLE execution_logs (
    id SERIAL PRIMARY KEY,
    task_name VARCHAR(100) NOT NULL,
    task_id VARCHAR(100),
    agent_name VARCHAR(50),
    run_id UUID,                           -- [NOVO] Link para run_metrics
    
    related_video_id INTEGER REFERENCES viral_videos(id) ON DELETE SET NULL,
    related_strategy_id INTEGER REFERENCES generated_strategies(id) ON DELETE SET NULL,
    related_production_id INTEGER REFERENCES produced_videos(id) ON DELETE SET NULL,
    
    status VARCHAR(20),
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    error_traceback TEXT,
    
    duration_seconds DECIMAL(10,3),
    tokens_used INTEGER,
    cost_usd DECIMAL(10,6),
    
    executed_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- TABELA: Configurações do Sistema
-- ============================================
CREATE TABLE system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Configurações atualizadas
INSERT INTO system_config (key, value, description) VALUES
('daily_limits', '{
    "veo_generations": 10,
    "scraping_profiles": 20,
    "analyses": 50,
    "strategies": 20,
    "tts_characters": 50000
}', 'Limites diários de operações'),

('quality_thresholds', '{
    "min_views": 10000,
    "min_likes": 1000,
    "min_comments": 100,
    "min_statistical_score": 0.6,
    "min_virality_score": 0.7
}', 'Thresholds mínimos'),

('costs', '{
    "veo_per_generation": 0.50,
    "veo_fast_per_generation": 0.25,
    "gemini_per_video": 0.002,
    "gpt4o_per_strategy": 0.01,
    "elevenlabs_per_1000_chars": 0.30,
    "apify_per_1000_results": 2.30
}', 'Custos por operação em USD'),

('budget', '{
    "daily_limit_usd": 20.00,
    "monthly_limit_usd": 500.00,
    "abort_on_exceed": true,
    "warning_threshold": 0.8
}', 'Configurações de orçamento'),

('tts_defaults', '{
    "provider": "edge-tts",
    "fallback_provider": "elevenlabs",
    "voice_pt_br": "pt-BR-FranciscaNeural",
    "voice_en_us": "en-US-JennyNeural",
    "rate": "+0%",
    "pitch": "+0Hz"
}', 'Configurações padrão de TTS')

ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW();

-- ============================================
-- TABELA: Contador Diário [ATUALIZADO]
-- ============================================
CREATE TABLE daily_counters (
    id SERIAL PRIMARY KEY,
    date DATE UNIQUE DEFAULT CURRENT_DATE,
    
    -- Contadores de operações
    veo_generations INTEGER DEFAULT 0,
    scraping_runs INTEGER DEFAULT 0,
    videos_collected INTEGER DEFAULT 0,
    videos_analyzed INTEGER DEFAULT 0,
    strategies_generated INTEGER DEFAULT 0,
    videos_produced INTEGER DEFAULT 0,
    
    -- [NOVO] Contadores de TTS
    tts_characters_used INTEGER DEFAULT 0,
    tts_edge_calls INTEGER DEFAULT 0,
    tts_elevenlabs_calls INTEGER DEFAULT 0,
    
    -- Custos
    total_cost_usd DECIMAL(10,4) DEFAULT 0,
    
    -- [NOVO] Budget status
    budget_warning_sent BOOLEAN DEFAULT false,
    budget_exceeded BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- ÍNDICES PARA PERFORMANCE
-- ============================================

-- viral_videos
CREATE INDEX idx_viral_videos_engagement ON viral_videos(views_count DESC, likes_count DESC);
CREATE INDEX idx_viral_videos_statistical_score ON viral_videos(statistical_viral_score DESC) WHERE passes_prefilter = true;
CREATE INDEX idx_viral_videos_not_downloaded ON viral_videos(is_downloaded) WHERE is_downloaded = false;
CREATE INDEX idx_viral_videos_not_transcribed ON viral_videos(is_transcribed) WHERE is_transcribed = false;
CREATE INDEX idx_viral_videos_not_analyzed ON viral_videos(is_analyzed) WHERE is_analyzed = false;
CREATE INDEX idx_viral_videos_posted_at ON viral_videos(posted_at DESC);
CREATE INDEX idx_viral_videos_prefilter ON viral_videos(passes_prefilter) WHERE passes_prefilter = true;

-- video_analyses
CREATE INDEX idx_analyses_virality ON video_analyses(virality_score DESC);
CREATE INDEX idx_analyses_prompt_version ON video_analyses(prompt_version_id);

-- generated_strategies
CREATE INDEX idx_strategies_status ON generated_strategies(status);

-- budget_tracking
CREATE INDEX idx_budget_date ON budget_tracking(date DESC);

-- run_metrics
CREATE INDEX idx_run_metrics_task ON run_metrics(task_name, started_at DESC);
CREATE INDEX idx_run_metrics_status ON run_metrics(status);

-- ============================================
-- FUNÇÕES AUXILIARES
-- ============================================

-- Função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para updated_at
CREATE TRIGGER update_monitored_profiles_updated_at BEFORE UPDATE ON monitored_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_viral_videos_updated_at BEFORE UPDATE ON viral_videos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_generated_strategies_updated_at BEFORE UPDATE ON generated_strategies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_produced_videos_updated_at BEFORE UPDATE ON produced_videos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_budget_tracking_updated_at BEFORE UPDATE ON budget_tracking
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Função para calcular engagement_rate automaticamente
CREATE OR REPLACE FUNCTION calculate_engagement_rate()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.views_count > 0 THEN
        NEW.engagement_rate = ((NEW.likes_count + NEW.comments_count + COALESCE(NEW.shares_count, 0))::DECIMAL / NEW.views_count) * 100;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER calculate_engagement_before_insert BEFORE INSERT ON viral_videos
    FOR EACH ROW EXECUTE FUNCTION calculate_engagement_rate();

CREATE TRIGGER calculate_engagement_before_update BEFORE UPDATE ON viral_videos
    FOR EACH ROW EXECUTE FUNCTION calculate_engagement_rate();

-- [NOVA] Função para calcular viral score estatístico
CREATE OR REPLACE FUNCTION calculate_statistical_viral_score()
RETURNS TRIGGER AS $$
DECLARE
    profile_record RECORD;
    days_since_post INTEGER;
BEGIN
    -- Busca médias do nicho
    SELECT niche_avg_views, niche_avg_likes, niche_avg_comments 
    INTO profile_record
    FROM monitored_profiles WHERE id = NEW.profile_id;
    
    -- Se não encontrou perfil, usa valores padrão
    IF profile_record IS NULL THEN
        profile_record.niche_avg_views := 50000;
        profile_record.niche_avg_likes := 5000;
        profile_record.niche_avg_comments := 500;
    END IF;
    
    -- Calcula scores normalizados (0-1, com cap em 2x a média)
    NEW.normalized_views := LEAST(NEW.views_count::DECIMAL / (profile_record.niche_avg_views * 2), 1.0);
    NEW.normalized_engagement := LEAST(
        ((NEW.likes_count + NEW.comments_count)::DECIMAL / 
        ((profile_record.niche_avg_likes + profile_record.niche_avg_comments) * 2)), 
        1.0
    );
    
    -- Calcula recency score (decai ao longo de 7 dias)
    IF NEW.posted_at IS NOT NULL THEN
        days_since_post := EXTRACT(DAY FROM NOW() - NEW.posted_at);
        NEW.recency_score := GREATEST(1.0 - (days_since_post::DECIMAL / 7.0), 0.0);
    ELSE
        NEW.recency_score := 0.5; -- Valor neutro se não souber a data
    END IF;
    
    -- Calcula score final (média ponderada)
    -- 40% views + 40% engagement + 20% recência
    NEW.statistical_viral_score := (
        NEW.normalized_views * 0.4 +
        NEW.normalized_engagement * 0.4 +
        NEW.recency_score * 0.2
    );
    
    -- Define se passa no pré-filtro (score >= 0.6)
    NEW.passes_prefilter := NEW.statistical_viral_score >= 0.6;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER calculate_viral_score_before_insert BEFORE INSERT ON viral_videos
    FOR EACH ROW EXECUTE FUNCTION calculate_statistical_viral_score();

CREATE TRIGGER calculate_viral_score_before_update BEFORE UPDATE ON viral_videos
    FOR EACH ROW EXECUTE FUNCTION calculate_statistical_viral_score();

-- ============================================
-- VIEWS ÚTEIS [ATUALIZADAS]
-- ============================================

-- View: Vídeos que passaram no pré-filtro e estão pendentes
CREATE OR REPLACE VIEW v_prefiltered_pending AS
SELECT 
    v.id,
    v.platform_id,
    v.source_url,
    v.views_count,
    v.likes_count,
    v.statistical_viral_score,
    v.is_downloaded,
    v.is_transcribed,
    v.is_analyzed,
    p.username as profile_username,
    p.niche
FROM viral_videos v
LEFT JOIN monitored_profiles p ON v.profile_id = p.id
WHERE v.passes_prefilter = true 
  AND v.is_analyzed = false
ORDER BY v.statistical_viral_score DESC;

-- View: Top vídeos para criar estratégias
CREATE OR REPLACE VIEW v_top_videos_for_strategy AS
SELECT 
    v.id as video_id,
    v.source_url,
    v.views_count,
    v.engagement_rate,
    v.statistical_viral_score,
    a.virality_score,
    a.replicability_score,
    v.transcription,
    a.hook_analysis,
    a.viral_factors,
    pv.version as prompt_version
FROM viral_videos v
JOIN video_analyses a ON v.id = a.video_id
LEFT JOIN prompt_versions pv ON a.prompt_version_id = pv.id
WHERE a.virality_score >= 0.7
  AND a.replicability_score >= 0.6
  AND a.is_valid_json = true
  AND NOT EXISTS (
      SELECT 1 FROM generated_strategies gs WHERE gs.source_video_id = v.id
  )
ORDER BY a.virality_score DESC, v.statistical_viral_score DESC;

-- View: Dashboard de estatísticas
CREATE OR REPLACE VIEW v_dashboard_stats AS
SELECT
    (SELECT COUNT(*) FROM monitored_profiles WHERE is_active = true) as active_profiles,
    (SELECT COUNT(*) FROM viral_videos) as total_videos,
    (SELECT COUNT(*) FROM viral_videos WHERE passes_prefilter = true) as prefiltered_videos,
    (SELECT COUNT(*) FROM viral_videos WHERE is_analyzed = true) as analyzed_videos,
    (SELECT COUNT(*) FROM generated_strategies) as total_strategies,
    (SELECT COUNT(*) FROM produced_videos WHERE status = 'completed') as produced_videos,
    (SELECT COALESCE(SUM(total_cost_usd), 0) FROM daily_counters WHERE date = CURRENT_DATE) as today_cost,
    (SELECT budget_exceeded FROM daily_counters WHERE date = CURRENT_DATE) as budget_exceeded;

-- View: Métricas de run por dia
CREATE OR REPLACE VIEW v_daily_run_metrics AS
SELECT 
    DATE(started_at) as run_date,
    task_name,
    COUNT(*) as total_runs,
    COUNT(*) FILTER (WHERE status = 'completed') as successful_runs,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_runs,
    AVG(duration_seconds) as avg_duration,
    SUM(actual_cost_usd) as total_cost
FROM run_metrics
GROUP BY DATE(started_at), task_name
ORDER BY run_date DESC, task_name;
```
# 03 - Configurações, Schemas e Validação v2.0

## 3.1 Arquivo: `.env.example`

```env
# ============================================
# DATABASE
# ============================================
DB_USER=viral_admin
DB_PASSWORD=sua_senha_segura_aqui
DB_HOST=postgres
DB_PORT=5432
DB_NAME=viral_videos
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}

# ============================================
# REDIS
# ============================================
REDIS_URL=redis://redis:6379/0

# ============================================
# MINIO (Object Storage)
# ============================================
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=sua_senha_minio_aqui
MINIO_BUCKET=viral-videos
MINIO_SECURE=false

# ============================================
# APIs EXTERNAS
# ============================================
APIFY_TOKEN=apify_api_xxxxxxxxxx
GOOGLE_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
FAL_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# [NOVO] ElevenLabs (TTS Premium - Opcional)
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=pNInz6obpgDQGcFmaJgB

# ============================================
# LIMITES E CONFIGURAÇÕES
# ============================================
MAX_DAILY_VEO_GENERATIONS=10
MAX_DAILY_SCRAPING_PROFILES=20
MAX_DAILY_ANALYSES=50
MAX_DAILY_TTS_CHARACTERS=50000

# Thresholds de qualidade
MIN_VIEWS_THRESHOLD=10000
MIN_LIKES_THRESHOLD=1000
MIN_COMMENTS_THRESHOLD=100
MIN_STATISTICAL_SCORE=0.6
MIN_VIRALITY_SCORE=0.7

# Modo de teste
TEST_MODE=true

# ============================================
# [NOVO] ORÇAMENTO
# ============================================
DAILY_BUDGET_LIMIT_USD=20.00
MONTHLY_BUDGET_LIMIT_USD=500.00
BUDGET_WARNING_THRESHOLD=0.8
ABORT_ON_BUDGET_EXCEED=true

# ============================================
# [NOVO] TTS CONFIGURAÇÃO
# ============================================
TTS_PROVIDER=edge-tts
TTS_FALLBACK_PROVIDER=elevenlabs
TTS_VOICE_PT_BR=pt-BR-FranciscaNeural
TTS_VOICE_EN_US=en-US-JennyNeural
TTS_RATE=+0%
TTS_PITCH=+0Hz

# ============================================
# WHISPER (Transcrição Local)
# ============================================
# Para CPU-only com 15GB RAM, usar 'medium'
# Opções: tiny, base, small, medium, large, large-v2, large-v3
WHISPER_MODEL=medium

# ============================================
# CELERY
# ============================================
# Para 4 vCPUs e 15GB RAM, usar concurrency=2
CELERY_CONCURRENCY=2

# ============================================
# TIMEZONE
# ============================================
TZ=America/Sao_Paulo
```

---

## 3.2 Arquivo: `config/settings.py`

```python
"""
Configurações centralizadas do sistema v2.0.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import Optional
from decimal import Decimal


class Settings(BaseSettings):
    """Configurações do sistema carregadas do .env"""
    
    # ========== Database ==========
    database_url: str = Field(..., description="URL de conexão PostgreSQL")
    
    # ========== Redis ==========
    redis_url: str = Field(default="redis://redis:6379/0")
    
    # ========== MinIO ==========
    minio_endpoint: str = Field(default="minio:9000")
    minio_access_key: str = Field(...)
    minio_secret_key: str = Field(...)
    minio_bucket: str = Field(default="viral-videos")
    minio_secure: bool = Field(default=False)
    
    # ========== APIs Externas ==========
    apify_token: str = Field(...)
    google_api_key: str = Field(...)
    openai_api_key: str = Field(...)
    fal_key: str = Field(...)
    
    # [NOVO] ElevenLabs
    elevenlabs_api_key: Optional[str] = Field(default=None)
    elevenlabs_voice_id: str = Field(default="pNInz6obpgDQGcFmaJgB")
    
    # ========== Limites Diários ==========
    max_daily_veo_generations: int = Field(default=10)
    max_daily_scraping_profiles: int = Field(default=20)
    max_daily_analyses: int = Field(default=50)
    max_daily_tts_characters: int = Field(default=50000)
    
    # ========== Thresholds de Qualidade ==========
    min_views_threshold: int = Field(default=10000)
    min_likes_threshold: int = Field(default=1000)
    min_comments_threshold: int = Field(default=100)
    min_statistical_score: float = Field(default=0.6)
    min_virality_score: float = Field(default=0.7)
    
    # ========== [NOVO] Orçamento ==========
    daily_budget_limit_usd: Decimal = Field(default=Decimal("20.00"))
    monthly_budget_limit_usd: Decimal = Field(default=Decimal("500.00"))
    budget_warning_threshold: float = Field(default=0.8)
    abort_on_budget_exceed: bool = Field(default=True)
    
    # ========== [NOVO] TTS ==========
    tts_provider: str = Field(default="edge-tts")
    tts_fallback_provider: str = Field(default="elevenlabs")
    tts_voice_pt_br: str = Field(default="pt-BR-FranciscaNeural")
    tts_voice_en_us: str = Field(default="en-US-JennyNeural")
    tts_rate: str = Field(default="+0%")
    tts_pitch: str = Field(default="+0Hz")
    
    # ========== Modo de Teste ==========
    test_mode: bool = Field(default=True)
    
    # ========== Whisper ==========
    whisper_model: str = Field(default="medium")
    
    # ========== Celery ==========
    celery_concurrency: int = Field(default=2)
    
    # ========== Timezone ==========
    tz: str = Field(default="America/Sao_Paulo")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    # ========== Propriedades Computadas ==========
    
    @property
    def veo_endpoint(self) -> str:
        if self.test_mode:
            return "fal-ai/veo3.1/fast"
        return "fal-ai/veo3.1"
    
    @property
    def veo_cost_per_generation(self) -> float:
        if self.test_mode:
            return 0.25
        return 0.50
    
    @property
    def elevenlabs_available(self) -> bool:
        return bool(self.elevenlabs_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

---

## 3.3 Arquivo: `models/schemas.py` [NOVO - Validação Pydantic]

```python
"""
Schemas Pydantic para validação de outputs estruturados.
Garante que outputs de Gemini e GPT-4o sejam válidos e consistentes.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from decimal import Decimal
from enum import Enum


# ============================================
# ENUMS
# ============================================

class HookTechnique(str, Enum):
    CURIOSITY_GAP = "curiosity_gap"
    PATTERN_INTERRUPT = "pattern_interrupt"
    BOLD_CLAIM = "bold_claim"
    QUESTION = "question"
    SHOCKING_STAT = "shocking_stat"
    CONTROVERSY = "controversy"
    TRANSFORMATION = "transformation"
    OTHER = "other"


class NarrativeStyle(str, Enum):
    TUTORIAL = "tutorial"
    STORY = "story"
    DEMONSTRATION = "demonstration"
    COMPARISON = "comparison"
    TRANSFORMATION = "transformation"
    BEHIND_SCENES = "behind_scenes"
    LISTICLE = "listicle"
    OTHER = "other"


class CTAType(str, Enum):
    COMMENT = "comment"
    LIKE = "like"
    SHARE = "share"
    FOLLOW = "follow"
    LINK = "link"
    SAVE = "save"
    OTHER = "other"


class TTSProvider(str, Enum):
    EDGE_TTS = "edge-tts"
    ELEVENLABS = "elevenlabs"


# ============================================
# SCHEMAS DE ANÁLISE (OUTPUT DO GEMINI)
# ============================================

class HookAnalysis(BaseModel):
    """Análise do hook (primeiros 3 segundos)"""
    duration_seconds: float = Field(ge=0, le=10, description="Duração do hook em segundos")
    technique: HookTechnique = Field(description="Técnica utilizada no hook")
    text_transcription: Optional[str] = Field(default=None, description="Texto falado no hook")
    visual_description: str = Field(description="Descrição visual do hook")
    effectiveness_score: float = Field(ge=0, le=1, description="Score de efetividade 0-1")


class DevelopmentAnalysis(BaseModel):
    """Análise do desenvolvimento do conteúdo"""
    narrative_style: NarrativeStyle = Field(description="Estilo narrativo")
    key_points: List[str] = Field(min_length=1, max_length=10, description="Pontos-chave")
    pacing: str = Field(description="Ritmo do conteúdo (fast, medium, slow)")
    retention_techniques: List[str] = Field(default=[], description="Técnicas de retenção")


class CTAAnalysis(BaseModel):
    """Análise do Call-to-Action"""
    type: CTAType = Field(description="Tipo de CTA")
    text: Optional[str] = Field(default=None, description="Texto do CTA")
    placement: str = Field(description="Posicionamento (start, middle, end)")
    effectiveness: float = Field(ge=0, le=1, default=0.5)


class VisualElements(BaseModel):
    """Análise dos elementos visuais"""
    lighting: str = Field(description="Descrição da iluminação")
    color_palette: List[str] = Field(default=[], description="Paleta de cores")
    camera_movements: List[str] = Field(default=[], description="Movimentos de câmera")
    text_overlays: bool = Field(default=False, description="Possui texto sobreposto")
    transitions: List[str] = Field(default=[], description="Tipos de transição")
    thumbnail_hook: Optional[str] = Field(default=None, description="Elemento de hook na thumbnail")


class AudioElements(BaseModel):
    """Análise dos elementos de áudio"""
    music_type: str = Field(description="Tipo de música (trending, original, none)")
    voice_tone: str = Field(description="Tom da voz (energetic, calm, serious)")
    sound_effects: bool = Field(default=False, description="Possui efeitos sonoros")
    music_bpm: Optional[int] = Field(default=None, ge=60, le=200)


class ViralFactors(BaseModel):
    """Fatores de viralização identificados"""
    trend_alignment: str = Field(description="Alinhamento com tendências")
    emotional_trigger: str = Field(description="Gatilho emocional principal")
    shareability_reason: str = Field(description="Motivo de compartilhamento")
    target_audience: str = Field(description="Público-alvo identificado")


class AnalysisScores(BaseModel):
    """Scores calculados pela análise"""
    virality_potential: float = Field(ge=0, le=1, description="Potencial de viralização")
    replicability: float = Field(ge=0, le=1, description="Facilidade de replicar")
    production_quality: float = Field(ge=0, le=1, description="Qualidade de produção")


class VideoAnalysisOutput(BaseModel):
    """Schema completo do output do Gemini"""
    hook: HookAnalysis
    development: DevelopmentAnalysis
    cta: CTAAnalysis
    visual_analysis: VisualElements
    audio_analysis: AudioElements
    viral_factors: ViralFactors
    scores: AnalysisScores
    transcription_full: Optional[str] = None
    
    class Config:
        extra = "ignore"  # Ignora campos extras do Gemini


# ============================================
# SCHEMAS DE ESTRATÉGIA (OUTPUT DO GPT-4o)
# ============================================

class ScriptSection(BaseModel):
    """Seção do roteiro"""
    duracao: str = Field(description="Duração da seção (ex: '0-3s')")
    texto_falado: str = Field(min_length=1, description="Texto a ser narrado")
    acao_visual: Optional[str] = Field(default=None, description="Ação visual")


class VeoPrompt(BaseModel):
    """Prompt individual para o Veo 3.1"""
    scene: int = Field(ge=1, description="Número da cena")
    duration: str = Field(description="Duração (ex: '4s', '6s')")
    prompt: str = Field(min_length=10, description="Prompt descritivo")
    camera: Optional[str] = Field(default=None, description="Movimento de câmera")
    lighting: Optional[str] = Field(default=None, description="Iluminação")
    
    @validator('duration')
    def validate_duration(cls, v):
        # Remove 's' e verifica se é número válido
        num = v.replace('s', '').strip()
        try:
            seconds = float(num)
            if seconds > 8:
                raise ValueError("Veo 3.1 suporta máximo de 8 segundos por cena")
        except ValueError:
            raise ValueError(f"Duração inválida: {v}")
        return v


class PublicationConfig(BaseModel):
    """Configurações de publicação"""
    caption: str = Field(min_length=1, description="Legenda do post")
    hashtags: List[str] = Field(min_length=1, max_length=30, description="Hashtags")
    melhor_horario: Optional[str] = Field(default=None, description="Melhor horário")
    primeira_frase_hook: Optional[str] = Field(default=None)


class StrategyOutput(BaseModel):
    """Schema completo do output de estratégia"""
    titulo: str = Field(min_length=1, max_length=255)
    conceito_central: str = Field(min_length=10)
    roteiro: Dict[str, ScriptSection] = Field(description="Seções: hook, desenvolvimento, cta")
    veo_prompts: List[VeoPrompt] = Field(min_length=1, max_length=10)
    publicacao: PublicationConfig
    
    @validator('veo_prompts')
    def validate_total_duration(cls, v):
        total = 0
        for prompt in v:
            num = prompt.duration.replace('s', '').strip()
            total += float(num)
        if total > 60:
            raise ValueError(f"Duração total ({total}s) excede 60 segundos")
        return v
    
    class Config:
        extra = "ignore"


# ============================================
# SCHEMAS DE TTS [NOVO]
# ============================================

class TTSConfig(BaseModel):
    """Configuração de Text-to-Speech"""
    provider: TTSProvider = Field(default=TTSProvider.EDGE_TTS)
    voice: str = Field(default="pt-BR-FranciscaNeural")
    rate: str = Field(default="+0%", description="Velocidade (-50% a +50%)")
    pitch: str = Field(default="+0Hz", description="Tom (-50Hz a +50Hz)")
    
    @validator('rate')
    def validate_rate(cls, v):
        if not v.endswith('%'):
            raise ValueError("Rate deve terminar com % (ex: +10%)")
        return v


class TTSResult(BaseModel):
    """Resultado da geração de TTS"""
    provider_used: TTSProvider
    audio_path: str
    duration_seconds: float
    characters_used: int
    cost_usd: Decimal = Field(default=Decimal("0"))


# ============================================
# SCHEMAS DE PRODUÇÃO [NOVO]
# ============================================

class ProductionClip(BaseModel):
    """Informações de um clipe gerado"""
    scene: int
    prompt: str
    video_path: str
    duration_seconds: float
    cost_usd: Decimal
    status: str = "success"
    error: Optional[str] = None


class ProductionResult(BaseModel):
    """Resultado completo da produção"""
    production_id: int
    strategy_id: int
    
    # TTS
    tts_result: TTSResult
    
    # Vídeo
    clips: List[ProductionClip]
    concatenated_path: str
    final_path: str
    
    # Custos
    tts_cost_usd: Decimal
    veo_cost_usd: Decimal
    total_cost_usd: Decimal
    
    # Metadados
    final_duration_seconds: float
    status: str
```

---

## 3.4 Arquivo: `models/validators.py` [NOVO]

```python
"""
Validadores para garantir outputs estruturados e consistentes.
"""

import json
import re
from typing import Tuple, Optional, Any, Type
from pydantic import BaseModel, ValidationError

from models.schemas import VideoAnalysisOutput, StrategyOutput


def extract_json_from_response(response: str) -> str:
    """
    Extrai JSON de uma resposta que pode conter markdown ou texto extra.
    """
    # Remove blocos de código markdown
    response = response.strip()
    
    # Tenta extrair JSON de blocos ```json
    json_block_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
    if json_block_match:
        return json_block_match.group(1).strip()
    
    # Tenta extrair JSON de blocos ``` genéricos
    code_block_match = re.search(r'```\s*([\s\S]*?)\s*```', response)
    if code_block_match:
        return code_block_match.group(1).strip()
    
    # Tenta encontrar JSON puro (começa com { e termina com })
    json_match = re.search(r'(\{[\s\S]*\})', response)
    if json_match:
        return json_match.group(1).strip()
    
    return response


def validate_analysis_output(response: str) -> Tuple[bool, Optional[VideoAnalysisOutput], Optional[str]]:
    """
    Valida o output do Gemini contra o schema de análise.
    
    Returns:
        Tuple[is_valid, parsed_output, error_message]
    """
    try:
        # Extrai JSON
        json_str = extract_json_from_response(response)
        
        # Tenta parsear
        data = json.loads(json_str)
        
        # Valida contra schema
        output = VideoAnalysisOutput(**data)
        
        return True, output, None
        
    except json.JSONDecodeError as e:
        return False, None, f"JSON inválido: {str(e)}"
    except ValidationError as e:
        errors = e.errors()
        error_messages = [f"{err['loc']}: {err['msg']}" for err in errors]
        return False, None, f"Validação falhou: {'; '.join(error_messages)}"
    except Exception as e:
        return False, None, f"Erro inesperado: {str(e)}"


def validate_strategy_output(response: str) -> Tuple[bool, Optional[StrategyOutput], Optional[str]]:
    """
    Valida o output do GPT-4o contra o schema de estratégia.
    
    Returns:
        Tuple[is_valid, parsed_output, error_message]
    """
    try:
        json_str = extract_json_from_response(response)
        data = json.loads(json_str)
        output = StrategyOutput(**data)
        return True, output, None
        
    except json.JSONDecodeError as e:
        return False, None, f"JSON inválido: {str(e)}"
    except ValidationError as e:
        errors = e.errors()
        error_messages = [f"{err['loc']}: {err['msg']}" for err in errors]
        return False, None, f"Validação falhou: {'; '.join(error_messages)}"
    except Exception as e:
        return False, None, f"Erro inesperado: {str(e)}"


def safe_parse_json(response: str, schema: Type[BaseModel]) -> Tuple[bool, Optional[Any], Optional[str]]:
    """
    Parser genérico que valida qualquer response contra um schema Pydantic.
    """
    try:
        json_str = extract_json_from_response(response)
        data = json.loads(json_str)
        output = schema(**data)
        return True, output, None
    except Exception as e:
        return False, None, str(e)
```

---

## 3.5 Arquivo: `requirements.txt` [ATUALIZADO]

```text
# Core
python-dotenv==1.0.1
pydantic==2.5.3
pydantic-settings==2.1.0

# Framework de Agentes
agno>=0.1.0

# AI/ML
openai==1.6.1
google-generativeai==0.3.2
fal-client==0.3.0
openai-whisper==20231117

# [NOVO] TTS
edge-tts==6.1.9
elevenlabs==0.2.27

# Database
psycopg2-binary==2.9.9
sqlalchemy==2.0.23

# Storage
minio==7.2.0

# Task Queue
celery==5.3.4
redis==5.0.1

# API
fastapi==0.104.1
uvicorn==0.24.0.post1

# HTTP
requests==2.31.0
httpx==0.25.2

# Audio/Video
pydub==0.25.1
mutagen==1.47.0

# Utilities
python-multipart==0.0.6
aiofiles==23.2.1

# Dev/Testing
pytest==7.4.3
pytest-asyncio==0.21.1
```
# 04 - Tools v2.0 (Novas e Atualizadas)

## 4.1 TTS Tools [NOVO] - `tools/tts_tools.py`

```python
"""
Ferramentas de Text-to-Speech.
Suporta edge-tts (gratuito) e ElevenLabs (pago) com fallback automático.
"""

import os
import asyncio
import tempfile
from typing import Optional
from decimal import Decimal
from pathlib import Path

import edge_tts
from mutagen.mp3 import MP3

from config.settings import settings
from models.schemas import TTSConfig, TTSResult, TTSProvider
from tools.db_tools import db_tools


class TTSTools:
    """Ferramentas de Text-to-Speech para os agentes"""
    
    # Vozes disponíveis no edge-tts
    EDGE_VOICES = {
        'pt-BR': [
            'pt-BR-FranciscaNeural',    # Feminina (recomendada)
            'pt-BR-AntonioNeural',       # Masculina
        ],
        'en-US': [
            'en-US-JennyNeural',         # Feminina
            'en-US-GuyNeural',           # Masculina
        ],
        'es-ES': [
            'es-ES-ElviraNeural',
            'es-ES-AlvaroNeural',
        ]
    }
    
    def __init__(self):
        self.elevenlabs_client = None
        if settings.elevenlabs_available:
            try:
                from elevenlabs import ElevenLabs
                self.elevenlabs_client = ElevenLabs(api_key=settings.elevenlabs_api_key)
            except ImportError:
                print("⚠️ ElevenLabs não instalado. Usando apenas edge-tts.")
    
    async def generate_tts_edge(
        self,
        text: str,
        output_path: str,
        voice: str = None,
        rate: str = "+0%",
        pitch: str = "+0Hz"
    ) -> TTSResult:
        """
        Gera áudio usando edge-tts (Microsoft, gratuito).
        
        Args:
            text: Texto a ser convertido
            output_path: Caminho para salvar o áudio
            voice: Voz a usar (ex: 'pt-BR-FranciscaNeural')
            rate: Velocidade (ex: '+10%', '-20%')
            pitch: Tom (ex: '+5Hz', '-10Hz')
        """
        if voice is None:
            voice = settings.tts_voice_pt_br
        
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await communicate.save(output_path)
        
        # Calcula duração
        duration = self._get_audio_duration(output_path)
        
        # Atualiza contador
        db_tools.increment_counter('tts_edge_calls')
        db_tools.increment_counter('tts_characters_used', len(text))
        
        return TTSResult(
            provider_used=TTSProvider.EDGE_TTS,
            audio_path=output_path,
            duration_seconds=duration,
            characters_used=len(text),
            cost_usd=Decimal("0")  # edge-tts é gratuito
        )
    
    def generate_tts_elevenlabs(
        self,
        text: str,
        output_path: str,
        voice_id: str = None
    ) -> TTSResult:
        """
        Gera áudio usando ElevenLabs (pago, alta qualidade).
        
        Args:
            text: Texto a ser convertido
            output_path: Caminho para salvar o áudio
            voice_id: ID da voz no ElevenLabs
        """
        if not settings.elevenlabs_available:
            raise Exception("ElevenLabs não configurado. Defina ELEVENLABS_API_KEY no .env")
        
        if voice_id is None:
            voice_id = settings.elevenlabs_voice_id
        
        from elevenlabs import generate, save
        
        audio = generate(
            text=text,
            voice=voice_id,
            model="eleven_multilingual_v2"
        )
        
        save(audio, output_path)
        
        # Calcula duração e custo
        duration = self._get_audio_duration(output_path)
        cost = self._calculate_elevenlabs_cost(len(text))
        
        # Atualiza contadores
        db_tools.increment_counter('tts_elevenlabs_calls')
        db_tools.increment_counter('tts_characters_used', len(text))
        db_tools.add_daily_cost(float(cost))
        
        return TTSResult(
            provider_used=TTSProvider.ELEVENLABS,
            audio_path=output_path,
            duration_seconds=duration,
            characters_used=len(text),
            cost_usd=cost
        )
    
    def generate_tts(
        self,
        text: str,
        output_path: str = None,
        config: TTSConfig = None,
        use_fallback: bool = True
    ) -> TTSResult:
        """
        Gera áudio usando o provider configurado, com fallback automático.
        
        Args:
            text: Texto a ser convertido
            output_path: Caminho para salvar (auto-gerado se None)
            config: Configuração de TTS (usa padrões se None)
            use_fallback: Se True, tenta fallback em caso de erro
        """
        if config is None:
            config = TTSConfig(
                provider=TTSProvider(settings.tts_provider),
                voice=settings.tts_voice_pt_br,
                rate=settings.tts_rate,
                pitch=settings.tts_pitch
            )
        
        if output_path is None:
            output_path = tempfile.mktemp(suffix='.mp3')
        
        # Verifica limite diário
        counter = db_tools.get_daily_counter()
        if counter['tts_characters_used'] + len(text) > settings.max_daily_tts_characters:
            raise Exception(f"Limite diário de TTS excedido: {counter['tts_characters_used']}/{settings.max_daily_tts_characters}")
        
        try:
            if config.provider == TTSProvider.EDGE_TTS:
                return asyncio.run(self.generate_tts_edge(
                    text=text,
                    output_path=output_path,
                    voice=config.voice,
                    rate=config.rate,
                    pitch=config.pitch
                ))
            elif config.provider == TTSProvider.ELEVENLABS:
                return self.generate_tts_elevenlabs(
                    text=text,
                    output_path=output_path
                )
        except Exception as e:
            if use_fallback and settings.tts_fallback_provider:
                print(f"⚠️ Erro no {config.provider}: {e}. Tentando fallback...")
                fallback_provider = TTSProvider(settings.tts_fallback_provider)
                if fallback_provider != config.provider:
                    config.provider = fallback_provider
                    return self.generate_tts(text, output_path, config, use_fallback=False)
            raise
    
    def generate_narration_from_script(
        self,
        hook_script: str,
        development_script: str,
        cta_script: str,
        output_path: str = None,
        config: TTSConfig = None
    ) -> TTSResult:
        """
        Gera narração completa a partir das seções do roteiro.
        Adiciona pausas naturais entre seções.
        """
        # Monta texto completo com pausas
        full_text = f"{hook_script}... {development_script}... {cta_script}"
        
        return self.generate_tts(
            text=full_text,
            output_path=output_path,
            config=config
        )
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Retorna a duração do áudio em segundos."""
        try:
            audio = MP3(audio_path)
            return audio.info.length
        except:
            # Fallback usando ffprobe
            import subprocess
            cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 
                   'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', 
                   audio_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
    
    def _calculate_elevenlabs_cost(self, characters: int) -> Decimal:
        """Calcula custo do ElevenLabs (~$0.30 por 1000 caracteres)."""
        return Decimal(str(characters)) / Decimal("1000") * Decimal("0.30")
    
    def list_available_voices(self, language: str = 'pt-BR') -> list:
        """Lista vozes disponíveis para um idioma."""
        return self.EDGE_VOICES.get(language, [])


# Instância global
tts_tools = TTSTools()
```

---

## 4.2 FFmpeg Tools [ATUALIZADO] - `tools/ffmpeg_tools.py`

```python
"""
Ferramentas de manipulação de vídeo/áudio usando FFmpeg.
v2.0: Inclui mixagem de áudio, sincronia TTS+vídeo, música de fundo.
"""

import os
import subprocess
import tempfile
import json
from typing import List, Optional
from pathlib import Path


class FFmpegTools:
    """Ferramentas FFmpeg para os agentes"""
    
    # Diretório de músicas de fundo
    MUSIC_DIR = "/app/assets/music"
    
    def extract_audio(self, video_path: str, output_path: str = None, 
                      format: str = 'mp3', sample_rate: int = 16000) -> str:
        """Extrai áudio de um arquivo de vídeo."""
        if output_path is None:
            output_path = f"{os.path.splitext(video_path)[0]}.{format}"
        
        codec = 'libmp3lame' if format == 'mp3' else 'pcm_s16le'
        cmd = [
            'ffmpeg', '-y', '-i', video_path,
            '-vn', '-acodec', codec,
            '-ar', str(sample_rate), '-ac', '1',
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    
    def concatenate_videos(self, video_paths: List[str], output_path: str,
                          resize_to: tuple = None) -> str:
        """
        Concatena múltiplos vídeos em um único arquivo.
        
        Args:
            video_paths: Lista de caminhos dos vídeos
            output_path: Caminho do vídeo final
            resize_to: Tupla (width, height) para redimensionar
        """
        # Se precisar redimensionar, processa cada vídeo primeiro
        if resize_to:
            processed_paths = []
            for i, path in enumerate(video_paths):
                resized = tempfile.mktemp(suffix=f'_resized_{i}.mp4')
                self.resize_video(path, resized, resize_to[0], resize_to[1])
                processed_paths.append(resized)
            video_paths = processed_paths
        
        # Cria arquivo de lista
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for path in video_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")
            list_file = f.name
        
        try:
            cmd = [
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                '-i', list_file, '-c', 'copy', output_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
        finally:
            os.unlink(list_file)
            # Limpa arquivos temporários se foram criados
            if resize_to:
                for p in video_paths:
                    if os.path.exists(p):
                        os.unlink(p)
        
        return output_path
    
    def resize_video(self, video_path: str, output_path: str,
                    width: int = 1080, height: int = 1920) -> str:
        """Redimensiona vídeo para resolução específica (padrão: 9:16 vertical)."""
        cmd = [
            'ffmpeg', '-y', '-i', video_path,
            '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,'
                   f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black',
            '-c:a', 'copy', output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    
    def mix_audio_with_video(
        self,
        video_path: str,
        narration_path: str,
        output_path: str,
        background_music_path: str = None,
        narration_volume: float = 1.0,
        music_volume: float = 0.2,
        fade_music: bool = True
    ) -> str:
        """
        [NOVO] Mixa narração TTS + música de fundo com o vídeo.
        
        Args:
            video_path: Vídeo base (pode ter ou não áudio)
            narration_path: Arquivo de narração TTS
            output_path: Caminho do vídeo final
            background_music_path: Música de fundo (opcional)
            narration_volume: Volume da narração (0-2, padrão 1.0)
            music_volume: Volume da música (0-1, padrão 0.2)
            fade_music: Se True, faz fade out no final da música
        """
        video_duration = self.get_video_duration(video_path)
        narration_duration = self.get_audio_duration(narration_path)
        
        # Se narração é mais longa que o vídeo, estende o último frame
        if narration_duration > video_duration:
            extended_video = tempfile.mktemp(suffix='_extended.mp4')
            self._extend_video_to_duration(video_path, extended_video, narration_duration)
            video_path = extended_video
        
        # Monta filtro de áudio
        filter_parts = []
        inputs = ['-i', video_path, '-i', narration_path]
        audio_inputs = ['1:a']
        
        # Ajusta volume da narração
        filter_parts.append(f'[1:a]volume={narration_volume}[narration]')
        
        if background_music_path and os.path.exists(background_music_path):
            inputs.extend(['-i', background_music_path])
            
            # Loop e trim da música para a duração do vídeo
            music_filter = f'[2:a]aloop=loop=-1:size=2e+09,atrim=0:{video_duration}'
            
            # Adiciona fade out se solicitado
            if fade_music:
                fade_start = max(0, video_duration - 2)  # Fade nos últimos 2 segundos
                music_filter += f',afade=t=out:st={fade_start}:d=2'
            
            music_filter += f',volume={music_volume}[music]'
            filter_parts.append(music_filter)
            
            # Mixa narração + música
            filter_parts.append('[narration][music]amix=inputs=2:duration=longest[aout]')
        else:
            filter_parts.append('[narration]acopy[aout]')
        
        filter_complex = ';'.join(filter_parts)
        
        cmd = [
            'ffmpeg', '-y',
            *inputs,
            '-filter_complex', filter_complex,
            '-map', '0:v',
            '-map', '[aout]',
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',
            output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Limpa arquivo temporário se foi criado
        if 'extended_video' in locals() and os.path.exists(extended_video):
            os.unlink(extended_video)
        
        return output_path
    
    def _extend_video_to_duration(self, video_path: str, output_path: str, 
                                   target_duration: float) -> str:
        """Estende o vídeo repetindo o último frame até a duração alvo."""
        current_duration = self.get_video_duration(video_path)
        extra_duration = target_duration - current_duration
        
        if extra_duration <= 0:
            # Não precisa estender, apenas copia
            subprocess.run(['cp', video_path, output_path], check=True)
            return output_path
        
        # Extrai último frame
        last_frame = tempfile.mktemp(suffix='.png')
        subprocess.run([
            'ffmpeg', '-y', '-sseof', '-0.1', '-i', video_path,
            '-vframes', '1', '-q:v', '2', last_frame
        ], check=True, capture_output=True)
        
        # Cria vídeo do último frame com a duração extra
        freeze_video = tempfile.mktemp(suffix='_freeze.mp4')
        subprocess.run([
            'ffmpeg', '-y', '-loop', '1', '-i', last_frame,
            '-t', str(extra_duration),
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            '-r', '30', freeze_video
        ], check=True, capture_output=True)
        
        # Concatena original + freeze
        self.concatenate_videos([video_path, freeze_video], output_path)
        
        # Limpa temporários
        os.unlink(last_frame)
        os.unlink(freeze_video)
        
        return output_path
    
    def create_thumbnail(self, video_path: str, output_path: str,
                        timestamp: str = '00:00:01') -> str:
        """Cria thumbnail de um vídeo."""
        cmd = [
            'ffmpeg', '-y', '-i', video_path,
            '-ss', timestamp, '-vframes', '1',
            '-q:v', '2', output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    
    def add_subtitles(self, video_path: str, srt_path: str, 
                      output_path: str, style: str = None) -> str:
        """
        [NOVO] Adiciona legendas ao vídeo.
        
        Args:
            video_path: Vídeo base
            srt_path: Arquivo de legendas SRT
            output_path: Vídeo com legendas
            style: Estilo ASS (opcional)
        """
        if style is None:
            # Estilo padrão para Reels (fonte grande, fundo semi-transparente)
            style = "FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1"
        
        cmd = [
            'ffmpeg', '-y', '-i', video_path,
            '-vf', f"subtitles={srt_path}:force_style='{style}'",
            '-c:a', 'copy', output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    
    def get_video_duration(self, video_path: str) -> float:
        """Retorna a duração do vídeo em segundos."""
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
    
    def get_audio_duration(self, audio_path: str) -> float:
        """Retorna a duração do áudio em segundos."""
        return self.get_video_duration(audio_path)  # FFprobe funciona para áudio também
    
    def get_video_info(self, video_path: str) -> dict:
        """Obtém informações detalhadas sobre um vídeo."""
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        video_stream = next((s for s in data['streams'] if s['codec_type'] == 'video'), {})
        audio_stream = next((s for s in data['streams'] if s['codec_type'] == 'audio'), None)
        
        return {
            'duration': float(data['format'].get('duration', 0)),
            'width': video_stream.get('width'),
            'height': video_stream.get('height'),
            'fps': eval(video_stream.get('r_frame_rate', '0/1')) if video_stream.get('r_frame_rate') else 0,
            'size_bytes': int(data['format'].get('size', 0)),
            'has_audio': audio_stream is not None,
            'codec_video': video_stream.get('codec_name'),
            'codec_audio': audio_stream.get('codec_name') if audio_stream else None
        }
    
    def get_available_music_tracks(self) -> List[str]:
        """Lista músicas de fundo disponíveis."""
        if not os.path.exists(self.MUSIC_DIR):
            return []
        return [f for f in os.listdir(self.MUSIC_DIR) if f.endswith(('.mp3', '.wav'))]
    
    def get_music_path(self, track_name: str) -> Optional[str]:
        """Retorna caminho completo de uma música de fundo."""
        path = os.path.join(self.MUSIC_DIR, track_name)
        return path if os.path.exists(path) else None


# Instância global
ffmpeg_tools = FFmpegTools()
```

---

## 4.3 Budget Tools [NOVO] - `tools/budget_tools.py`

```python
"""
Ferramentas de controle de orçamento.
Monitora custos, aplica limites e aborta operações quando necessário.
"""

from decimal import Decimal
from datetime import date, datetime
from typing import Dict, Optional, Tuple

from config.settings import settings
from tools.db_tools import db_tools


class BudgetTools:
    """Controle de orçamento e custos"""
    
    # Custos por operação (em USD)
    COSTS = {
        'veo': Decimal('0.50'),
        'veo_fast': Decimal('0.25'),
        'gemini': Decimal('0.002'),
        'gpt4o': Decimal('0.01'),
        'elevenlabs_per_1k_chars': Decimal('0.30'),
        'apify_per_1k': Decimal('2.30'),
    }
    
    def get_daily_budget_status(self) -> Dict:
        """
        Retorna status atual do orçamento diário.
        """
        today = date.today()
        tracking = self._ensure_budget_tracking(today)
        
        total_spent = Decimal(str(tracking['total_cost_usd']))
        daily_limit = settings.daily_budget_limit_usd
        remaining = daily_limit - total_spent
        percentage_used = (total_spent / daily_limit * 100) if daily_limit > 0 else 0
        
        return {
            'date': today.isoformat(),
            'total_spent_usd': float(total_spent),
            'daily_limit_usd': float(daily_limit),
            'remaining_usd': float(remaining),
            'percentage_used': float(percentage_used),
            'budget_exceeded': tracking['budget_exceeded'],
            'warning_threshold_reached': percentage_used >= (settings.budget_warning_threshold * 100),
            'breakdown': {
                'apify': float(tracking['apify_cost_usd']),
                'gemini': float(tracking['gemini_cost_usd']),
                'openai': float(tracking['openai_cost_usd']),
                'veo': float(tracking['veo_cost_usd']),
                'elevenlabs': float(tracking['elevenlabs_cost_usd']),
            }
        }
    
    def can_spend(self, amount_usd: float, service: str = 'general') -> Tuple[bool, str]:
        """
        Verifica se pode gastar um determinado valor.
        
        Returns:
            Tuple[can_spend, reason]
        """
        status = self.get_daily_budget_status()
        amount = Decimal(str(amount_usd))
        
        # Verifica se já excedeu
        if status['budget_exceeded']:
            return False, "Orçamento diário já foi excedido"
        
        # Verifica se a operação excederia o limite
        if Decimal(str(status['remaining_usd'])) < amount:
            if settings.abort_on_budget_exceed:
                return False, f"Operação excederia limite diário. Disponível: ${status['remaining_usd']:.2f}"
            else:
                # Permite mas registra warning
                return True, f"⚠️ Operação excede orçamento (modo soft limit)"
        
        return True, "OK"
    
    def check_before_operation(self, operation: str) -> Tuple[bool, str]:
        """
        Verifica se uma operação específica pode ser executada.
        
        Args:
            operation: 'veo', 'gemini', 'gpt4o', 'elevenlabs'
        """
        cost = self.COSTS.get(operation)
        if cost is None:
            return True, "Operação sem custo definido"
        
        if settings.test_mode and operation == 'veo':
            cost = self.COSTS['veo_fast']
        
        return self.can_spend(float(cost), operation)
    
    def record_cost(self, amount_usd: float, service: str) -> None:
        """
        Registra um custo no tracking diário.
        
        Args:
            amount_usd: Valor gasto
            service: 'apify', 'gemini', 'openai', 'veo', 'elevenlabs'
        """
        today = date.today()
        self._ensure_budget_tracking(today)
        
        # Mapeamento de serviço para coluna
        service_column = {
            'apify': 'apify_cost_usd',
            'gemini': 'gemini_cost_usd',
            'openai': 'openai_cost_usd',
            'gpt4o': 'openai_cost_usd',
            'veo': 'veo_cost_usd',
            'elevenlabs': 'elevenlabs_cost_usd',
        }.get(service, 'apify_cost_usd')  # fallback para apify
        
        # Atualiza no banco
        with db_tools.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    UPDATE budget_tracking
                    SET {service_column} = {service_column} + %s,
                        total_cost_usd = total_cost_usd + %s,
                        api_calls_count = api_calls_count + 1,
                        updated_at = NOW()
                    WHERE date = %s
                """, (amount_usd, amount_usd, today))
                
                # Verifica se excedeu limite
                cur.execute("""
                    UPDATE budget_tracking
                    SET budget_exceeded = (total_cost_usd >= %s),
                        budget_exceeded_at = CASE 
                            WHEN total_cost_usd >= %s AND budget_exceeded_at IS NULL 
                            THEN NOW() 
                            ELSE budget_exceeded_at 
                        END
                    WHERE date = %s
                """, (float(settings.daily_budget_limit_usd), 
                      float(settings.daily_budget_limit_usd), today))
                
                conn.commit()
        
        # Também registra no daily_counters (compatibilidade)
        db_tools.add_daily_cost(amount_usd)
    
    def estimate_run_cost(
        self,
        veo_scenes: int = 0,
        gemini_analyses: int = 0,
        gpt4o_strategies: int = 0,
        elevenlabs_chars: int = 0
    ) -> Dict:
        """
        Estima o custo de uma run antes de executar.
        """
        veo_cost = self.COSTS['veo_fast' if settings.test_mode else 'veo']
        
        costs = {
            'veo': float(veo_cost * veo_scenes),
            'gemini': float(self.COSTS['gemini'] * gemini_analyses),
            'gpt4o': float(self.COSTS['gpt4o'] * gpt4o_strategies),
            'elevenlabs': float(self.COSTS['elevenlabs_per_1k_chars'] * elevenlabs_chars / 1000),
        }
        costs['total'] = sum(costs.values())
        
        # Verifica se cabe no orçamento
        can_afford, reason = self.can_spend(costs['total'])
        costs['can_afford'] = can_afford
        costs['reason'] = reason
        
        return costs
    
    def _ensure_budget_tracking(self, target_date: date) -> Dict:
        """Garante que existe registro de tracking para a data."""
        with db_tools.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO budget_tracking (date, daily_budget_limit_usd, monthly_budget_limit_usd)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (date) DO NOTHING
                """, (target_date, float(settings.daily_budget_limit_usd), 
                      float(settings.monthly_budget_limit_usd)))
                conn.commit()
                
                cur.execute("SELECT * FROM budget_tracking WHERE date = %s", (target_date,))
                columns = [desc[0] for desc in cur.description]
                row = cur.fetchone()
                return dict(zip(columns, row))
    
    def get_monthly_summary(self, year: int = None, month: int = None) -> Dict:
        """Retorna resumo de custos do mês."""
        if year is None or month is None:
            today = date.today()
            year, month = today.year, today.month
        
        with db_tools.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) as days_with_activity,
                        COALESCE(SUM(total_cost_usd), 0) as total_cost,
                        COALESCE(SUM(apify_cost_usd), 0) as apify_total,
                        COALESCE(SUM(gemini_cost_usd), 0) as gemini_total,
                        COALESCE(SUM(openai_cost_usd), 0) as openai_total,
                        COALESCE(SUM(veo_cost_usd), 0) as veo_total,
                        COALESCE(SUM(elevenlabs_cost_usd), 0) as elevenlabs_total,
                        COALESCE(SUM(api_calls_count), 0) as total_api_calls,
                        COALESCE(SUM(videos_produced), 0) as total_videos
                    FROM budget_tracking
                    WHERE EXTRACT(YEAR FROM date) = %s
                      AND EXTRACT(MONTH FROM date) = %s
                """, (year, month))
                row = cur.fetchone()
                
                return {
                    'year': year,
                    'month': month,
                    'days_with_activity': row[0],
                    'total_cost_usd': float(row[1]),
                    'monthly_limit_usd': float(settings.monthly_budget_limit_usd),
                    'remaining_usd': float(settings.monthly_budget_limit_usd - row[1]),
                    'breakdown': {
                        'apify': float(row[2]),
                        'gemini': float(row[3]),
                        'openai': float(row[4]),
                        'veo': float(row[5]),
                        'elevenlabs': float(row[6]),
                    },
                    'total_api_calls': row[7],
                    'total_videos_produced': row[8]
                }


# Instância global
budget_tools = BudgetTools()


# Decorator para verificar orçamento antes de operações
def check_budget(operation: str):
    """Decorator que verifica orçamento antes de executar uma função."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            can_proceed, reason = budget_tools.check_before_operation(operation)
            if not can_proceed:
                raise BudgetExceededException(reason)
            return func(*args, **kwargs)
        return wrapper
    return decorator


class BudgetExceededException(Exception):
    """Exceção levantada quando o orçamento é excedido."""
    pass
```
# 05 - Producer Agent v2.0 (Com TTS e Mixagem)

## 5.1 Producer Agent [ATUALIZADO] - `agents/producer.py`

```python
"""
Agente Producer v2.0 - Produz vídeos com narração TTS + Veo 3.1 + mixagem.

FLUXO:
1. Recebe estratégia aprovada
2. Gera narração TTS (edge-tts ou ElevenLabs)
3. Calcula duração total do áudio
4. Gera clipes no Veo 3.1 ajustados à duração
5. Concatena clipes
6. Mixa narração + música de fundo + vídeo
7. Salva resultado final
"""

import os
import tempfile
from typing import Dict, List, Optional
from decimal import Decimal

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from tools.db_tools import db_tools
from tools.storage_tools import storage_tools
from tools.fal_tools import fal_tools
from tools.ffmpeg_tools import ffmpeg_tools
from tools.tts_tools import tts_tools
from tools.budget_tools import budget_tools, BudgetExceededException
from models.schemas import TTSConfig, TTSProvider, TTSResult
from config.settings import settings


# ============================================
# FUNÇÕES DO AGENTE
# ============================================

def check_production_limit() -> str:
    """Verifica limite diário de produções e orçamento."""
    veo_status = fal_tools.check_daily_limit()
    budget_status = budget_tools.get_daily_budget_status()
    
    result = f"""
📊 **Status de Produção**

**Veo 3.1:**
- Gerações hoje: {veo_status['current_count']}/{veo_status['daily_limit']}
- Restantes: {veo_status['remaining']}

**Orçamento Diário:**
- Gasto hoje: ${budget_status['total_spent_usd']:.2f}
- Limite: ${budget_status['daily_limit_usd']:.2f}
- Disponível: ${budget_status['remaining_usd']:.2f}
- Uso: {budget_status['percentage_used']:.1f}%
"""
    
    if budget_status['budget_exceeded']:
        result += "\n⛔ **ORÇAMENTO DIÁRIO EXCEDIDO - Produção bloqueada**"
    elif budget_status['warning_threshold_reached']:
        result += "\n⚠️ **Atenção: Próximo do limite diário**"
    
    if not veo_status['can_generate']:
        result += "\n⛔ **LIMITE DE VEO ATINGIDO - Produção bloqueada**"
    
    return result


def estimate_production_cost(strategy_id: int) -> str:
    """Estima custo de produção antes de executar."""
    strategy = db_tools.get_strategy_by_id(strategy_id)
    if not strategy:
        return f"❌ Estratégia {strategy_id} não encontrada"
    
    veo_prompts = strategy.get('veo_prompts', [])
    full_script = strategy.get('full_script', '')
    
    # Estima caracteres do roteiro
    script_chars = len(strategy.get('hook_script', '')) + \
                   len(strategy.get('development_script', '')) + \
                   len(strategy.get('cta_script', ''))
    
    estimate = budget_tools.estimate_run_cost(
        veo_scenes=len(veo_prompts),
        elevenlabs_chars=script_chars if settings.tts_provider == 'elevenlabs' else 0
    )
    
    result = f"""
💰 **Estimativa de Custo - Estratégia {strategy_id}**

**Veo 3.1:** {len(veo_prompts)} cenas × ${settings.veo_cost_per_generation:.2f} = ${estimate['veo']:.2f}
**TTS:** {script_chars} caracteres = ${estimate['elevenlabs']:.2f}
**Total Estimado:** ${estimate['total']:.2f}

**Status:** {'✅ Dentro do orçamento' if estimate['can_afford'] else '❌ ' + estimate['reason']}
"""
    return result


def generate_narration(strategy_id: int, provider: str = None) -> str:
    """
    Gera narração TTS para uma estratégia.
    
    Args:
        strategy_id: ID da estratégia
        provider: 'edge-tts' ou 'elevenlabs' (usa padrão se None)
    """
    try:
        strategy = db_tools.get_strategy_by_id(strategy_id)
        if not strategy:
            return f"❌ Estratégia {strategy_id} não encontrada"
        
        # Monta texto completo
        hook = strategy.get('hook_script', '')
        development = strategy.get('development_script', '')
        cta = strategy.get('cta_script', '')
        
        if not hook and not development:
            return f"❌ Estratégia {strategy_id} não tem roteiro"
        
        # Configura TTS
        config = TTSConfig(
            provider=TTSProvider(provider) if provider else TTSProvider(settings.tts_provider),
            voice=settings.tts_voice_pt_br,
            rate=settings.tts_rate,
            pitch=settings.tts_pitch
        )
        
        # Gera narração
        output_path = tempfile.mktemp(suffix='_narration.mp3')
        result = tts_tools.generate_narration_from_script(
            hook_script=hook,
            development_script=development,
            cta_script=cta,
            output_path=output_path,
            config=config
        )
        
        # Upload para MinIO
        object_name = f"narrations/strategy_{strategy_id}.mp3"
        storage_tools.upload_file(output_path, object_name)
        
        # Limpa temp
        os.unlink(output_path)
        
        return f"""
✅ **Narração Gerada**
- Estratégia: {strategy_id}
- Provider: {result.provider_used.value}
- Duração: {result.duration_seconds:.1f}s
- Caracteres: {result.characters_used}
- Custo: ${result.cost_usd:.4f}
- Arquivo: {object_name}
"""
    except Exception as e:
        return f"❌ Erro ao gerar narração: {str(e)}"


def produce_video(strategy_id: int, test_mode: bool = None) -> str:
    """
    Produz um vídeo completo com narração + Veo + mixagem.
    
    Args:
        strategy_id: ID da estratégia aprovada
        test_mode: Se True, usa Veo fast (mais barato)
    """
    if test_mode is None:
        test_mode = settings.test_mode
    
    try:
        # 1. VALIDAÇÕES INICIAIS
        # =====================
        
        # Verifica orçamento
        budget_status = budget_tools.get_daily_budget_status()
        if budget_status['budget_exceeded'] and settings.abort_on_budget_exceed:
            return "❌ Orçamento diário excedido. Produção bloqueada."
        
        # Verifica limite Veo
        veo_limit = fal_tools.check_daily_limit()
        if not veo_limit['can_generate']:
            return "❌ Limite diário de Veo atingido."
        
        # Busca estratégia
        strategy = db_tools.get_strategy_by_id(strategy_id)
        if not strategy:
            return f"❌ Estratégia {strategy_id} não encontrada"
        
        if strategy['status'] not in ('approved', 'draft'):
            return f"❌ Estratégia {strategy_id} não está aprovada (status: {strategy['status']})"
        
        veo_prompts = strategy.get('veo_prompts', [])
        if not veo_prompts:
            return f"❌ Estratégia {strategy_id} não tem prompts de vídeo"
        
        # Verifica se tem cenas suficientes para o Veo disponível
        if len(veo_prompts) > veo_limit['remaining']:
            return f"❌ Limite Veo insuficiente. Necessário: {len(veo_prompts)}, Disponível: {veo_limit['remaining']}"
        
        # Estima custo
        script_chars = len(strategy.get('hook_script', '')) + \
                       len(strategy.get('development_script', '')) + \
                       len(strategy.get('cta_script', ''))
        
        cost_estimate = budget_tools.estimate_run_cost(
            veo_scenes=len(veo_prompts),
            elevenlabs_chars=script_chars if settings.tts_provider == 'elevenlabs' else 0
        )
        
        if not cost_estimate['can_afford'] and settings.abort_on_budget_exceed:
            return f"❌ Custo estimado (${cost_estimate['total']:.2f}) excede orçamento disponível"
        
        # 2. INICIA PRODUÇÃO
        # ==================
        
        db_tools.update_strategy_status(strategy_id, 'in_production')
        production_id = db_tools.create_production(strategy_id)
        
        print(f"🎬 Iniciando produção {production_id} para estratégia {strategy_id}")
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            
            # 3. GERA NARRAÇÃO TTS
            # ====================
            print("🎤 Gerando narração TTS...")
            
            narration_path = os.path.join(tmp_dir, 'narration.mp3')
            
            tts_config = TTSConfig(
                provider=TTSProvider(settings.tts_provider),
                voice=strategy.get('tts_config', {}).get('voice', settings.tts_voice_pt_br),
                rate=strategy.get('tts_config', {}).get('rate', settings.tts_rate),
                pitch=strategy.get('tts_config', {}).get('pitch', settings.tts_pitch)
            )
            
            tts_result = tts_tools.generate_narration_from_script(
                hook_script=strategy.get('hook_script', ''),
                development_script=strategy.get('development_script', ''),
                cta_script=strategy.get('cta_script', ''),
                output_path=narration_path,
                config=tts_config
            )
            
            narration_duration = tts_result.duration_seconds
            print(f"   ✅ Narração: {narration_duration:.1f}s ({tts_result.provider_used.value})")
            
            # Upload narração
            narration_object = f"productions/{production_id}/narration.mp3"
            storage_tools.upload_file(narration_path, narration_object)
            
            # 4. AJUSTA DURAÇÃO DOS PROMPTS VEO
            # =================================
            adjusted_prompts = _adjust_veo_prompts_to_duration(veo_prompts, narration_duration)
            
            # 5. GERA CLIPES DE VÍDEO (VEO 3.1)
            # =================================
            print(f"🎥 Gerando {len(adjusted_prompts)} clipes com Veo 3.1...")
            
            clips = fal_tools.generate_multiple_clips(adjusted_prompts, tmp_dir)
            
            # Verifica falhas
            failed = [c for c in clips if c.get('status') == 'failed']
            if len(failed) == len(clips):
                db_tools.update_production(production_id, {
                    'status': 'failed',
                    'error_message': 'Todas as cenas falharam na geração',
                    'veo_jobs': clips
                })
                return f"❌ Todas as {len(clips)} cenas falharam na geração"
            
            if failed:
                print(f"   ⚠️ {len(failed)} cenas falharam, continuando com {len(clips) - len(failed)}")
            
            successful_clips = [c for c in clips if c.get('status') == 'success']
            clip_paths = [c['video_path'] for c in successful_clips]
            
            # 6. CONCATENA VÍDEOS
            # ===================
            print("🔗 Concatenando clipes...")
            
            concatenated_path = os.path.join(tmp_dir, 'concatenated.mp4')
            ffmpeg_tools.concatenate_videos(
                clip_paths, 
                concatenated_path,
                resize_to=(1080, 1920)  # Formato vertical 9:16
            )
            
            # 7. MIXA ÁUDIO (NARRAÇÃO + MÚSICA)
            # =================================
            print("🎵 Mixando áudio...")
            
            final_path = os.path.join(tmp_dir, 'final.mp4')
            
            # Busca música de fundo
            music_track = strategy.get('music_track')
            music_path = None
            if music_track:
                music_path = ffmpeg_tools.get_music_path(music_track)
            
            if not music_path:
                # Usa música padrão se disponível
                available_music = ffmpeg_tools.get_available_music_tracks()
                if available_music:
                    music_path = ffmpeg_tools.get_music_path(available_music[0])
            
            ffmpeg_tools.mix_audio_with_video(
                video_path=concatenated_path,
                narration_path=narration_path,
                output_path=final_path,
                background_music_path=music_path,
                narration_volume=1.0,
                music_volume=float(strategy.get('music_volume', 0.20)),
                fade_music=True
            )
            
            # 8. UPLOAD FINAL
            # ===============
            print("☁️ Fazendo upload do vídeo final...")
            
            final_object = f"productions/{production_id}/final.mp4"
            storage_tools.upload_file(final_path, final_object)
            
            # Upload clipes individuais (para backup/edição)
            clips_objects = []
            for clip in successful_clips:
                clip_object = f"productions/{production_id}/clips/scene_{clip['scene']:02d}.mp4"
                storage_tools.upload_file(clip['video_path'], clip_object)
                clips_objects.append(clip_object)
            
            # 9. CALCULA CUSTOS E ATUALIZA BD
            # ===============================
            veo_cost = sum(Decimal(str(c.get('cost_usd', 0))) for c in successful_clips)
            tts_cost = tts_result.cost_usd
            total_cost = veo_cost + tts_cost
            
            # Registra custos
            budget_tools.record_cost(float(veo_cost), 'veo')
            if tts_cost > 0:
                budget_tools.record_cost(float(tts_cost), 'elevenlabs')
            
            # Obtém info do vídeo final
            final_info = ffmpeg_tools.get_video_info(final_path)
            
            # Atualiza produção
            db_tools.update_production(production_id, {
                'status': 'completed',
                'tts_file_path': narration_object,
                'tts_provider': tts_result.provider_used.value,
                'narration_duration_seconds': narration_duration,
                'veo_jobs': clips,
                'clips_paths': clips_objects,
                'concatenated_video_path': f"productions/{production_id}/concatenated.mp4",
                'final_video_path': final_object,
                'music_track_used': music_track,
                'music_volume_used': strategy.get('music_volume', 0.20),
                'final_duration_seconds': int(final_info['duration']),
                'final_resolution': f"{final_info['width']}x{final_info['height']}",
                'final_file_size_mb': round(final_info['size_bytes'] / (1024*1024), 2),
                'tts_cost_usd': float(tts_cost),
                'veo_cost_usd': float(veo_cost),
                'total_production_cost_usd': float(total_cost)
            })
            
            # Atualiza estratégia
            db_tools.update_strategy_status(strategy_id, 'produced')
            
            # Incrementa contador
            db_tools.increment_counter('videos_produced')
            
            # 10. RESULTADO
            # =============
            return f"""
✅ **Produção {production_id} Concluída!**

📹 **Vídeo:**
- Duração: {final_info['duration']:.1f}s
- Resolução: {final_info['width']}x{final_info['height']}
- Tamanho: {final_info['size_bytes'] / (1024*1024):.1f} MB
- Cenas: {len(successful_clips)}/{len(veo_prompts)}

🎤 **Narração:**
- Provider: {tts_result.provider_used.value}
- Duração: {narration_duration:.1f}s

💰 **Custos:**
- Veo: ${float(veo_cost):.2f}
- TTS: ${float(tts_cost):.4f}
- **Total: ${float(total_cost):.2f}**

📁 **Arquivo:** {final_object}
"""
    
    except BudgetExceededException as e:
        if 'production_id' in locals():
            db_tools.update_production(production_id, {
                'status': 'failed',
                'error_message': f'Orçamento excedido: {str(e)}'
            })
        return f"❌ Produção abortada: {str(e)}"
    
    except Exception as e:
        if 'production_id' in locals():
            db_tools.update_production(production_id, {
                'status': 'failed',
                'error_message': str(e)
            })
        return f"❌ Erro na produção: {str(e)}"


def _adjust_veo_prompts_to_duration(prompts: List[Dict], target_duration: float) -> List[Dict]:
    """
    Ajusta duração dos prompts Veo para cobrir a narração.
    
    O Veo 3.1 suporta máximo de 8 segundos por cena.
    Se a narração for mais longa que o total das cenas, aumenta duração das cenas.
    """
    # Calcula duração total atual
    current_total = 0
    for p in prompts:
        duration_str = p.get('duration', '4s').replace('s', '')
        current_total += float(duration_str)
    
    # Se já é suficiente, retorna como está
    if current_total >= target_duration:
        return prompts
    
    # Calcula fator de escala
    scale_factor = target_duration / current_total
    
    adjusted = []
    for p in prompts:
        new_p = p.copy()
        duration_str = p.get('duration', '4s').replace('s', '')
        new_duration = float(duration_str) * scale_factor
        
        # Limita a 8 segundos (máximo do Veo)
        new_duration = min(new_duration, 8.0)
        
        new_p['duration'] = f"{new_duration:.0f}s"
        adjusted.append(new_p)
    
    return adjusted


def get_pending_productions() -> str:
    """Lista estratégias aprovadas pendentes de produção."""
    strategies = db_tools.get_pending_strategies()
    if not strategies:
        return "ℹ️ Nenhuma estratégia pendente de produção"
    
    result = f"📋 **{len(strategies)} estratégias pendentes:**\n"
    for s in strategies:
        scenes = len(s.get('veo_prompts', []))
        cost = s.get('estimated_production_cost_usd', 0)
        result += f"- **ID {s['id']}:** {s['title']} ({scenes} cenas, ~${cost:.2f})\n"
    return result


def get_production_status(production_id: int) -> str:
    """Retorna status detalhado de uma produção."""
    production = db_tools.get_production_by_id(production_id)
    if not production:
        return f"❌ Produção {production_id} não encontrada"
    
    result = f"""
🎬 **Produção {production_id}**

**Status:** {production['status']}
**TTS Provider:** {production.get('tts_provider', 'N/A')}
**Narração:** {production.get('narration_duration_seconds', 0):.1f}s
**Duração Final:** {production.get('final_duration_seconds', 0)}s
**Resolução:** {production.get('final_resolution', 'N/A')}

**Custos:**
- TTS: ${production.get('tts_cost_usd', 0):.4f}
- Veo: ${production.get('veo_cost_usd', 0):.2f}
- **Total: ${production.get('total_production_cost_usd', 0):.2f}**
"""
    
    if production['status'] == 'completed':
        result += f"\n📁 **Arquivo:** {production['final_video_path']}"
    
    if production.get('error_message'):
        result += f"\n\n❌ **Erro:** {production['error_message']}"
    
    return result


def list_available_voices() -> str:
    """Lista vozes disponíveis para TTS."""
    voices = tts_tools.EDGE_VOICES
    result = "🎤 **Vozes Disponíveis (edge-tts):**\n\n"
    for lang, voice_list in voices.items():
        result += f"**{lang}:**\n"
        for v in voice_list:
            result += f"  - `{v}`\n"
    return result


def list_available_music() -> str:
    """Lista músicas de fundo disponíveis."""
    tracks = ffmpeg_tools.get_available_music_tracks()
    if not tracks:
        return "ℹ️ Nenhuma música de fundo disponível. Adicione arquivos em /assets/music/"
    
    result = "🎵 **Músicas de Fundo Disponíveis:**\n"
    for t in tracks:
        result += f"  - `{t}`\n"
    return result


# ============================================
# CRIAÇÃO DO AGENTE
# ============================================

producer_agent = Agent(
    name="Producer Agent v2",
    model=OpenAIChat(id="gpt-4o"),
    instructions="""
    Você é um Diretor de Cinema de IA especializado em produção de vídeos virais.
    
    ## Suas Responsabilidades:
    
    1. **Verificar limites** antes de qualquer produção
       - Orçamento diário
       - Limite de gerações Veo
    
    2. **Gerar narração** (TTS)
       - Usa edge-tts (gratuito) por padrão
       - Fallback para ElevenLabs se necessário
    
    3. **Gerar clipes de vídeo** (Veo 3.1)
       - Ajusta duração das cenas para cobrir narração
       - Máximo 8 segundos por cena
    
    4. **Mixar áudio**
       - Narração TTS + Música de fundo
       - Volume da música em ~20%
    
    5. **Monitorar custos**
       - Reportar custos após cada produção
       - Abortar se exceder orçamento
    
    ## Fluxo de Produção:
    
    1. `check_production_limit()` - Verifica se pode produzir
    2. `estimate_production_cost(strategy_id)` - Estima custo
    3. `produce_video(strategy_id)` - Executa produção completa
    
    ## Modo de Teste vs Produção:
    
    - **Teste:** Veo fast ($0.25/cena), para desenvolvimento
    - **Produção:** Veo normal ($0.50/cena), qualidade máxima
    """,
    tools=[
        check_production_limit,
        estimate_production_cost,
        generate_narration,
        produce_video,
        get_pending_productions,
        get_production_status,
        list_available_voices,
        list_available_music
    ],
    show_tool_calls=True,
    markdown=True
)


# ============================================
# FUNÇÃO DE EXECUÇÃO
# ============================================

def run_produce_pending(test_mode: bool = True) -> str:
    """Produz vídeos para estratégias aprovadas."""
    mode_text = "teste" if test_mode else "produção"
    prompt = f"""
    Execute a produção de vídeos em modo {mode_text}.
    
    1. Primeiro, verifique os limites de produção
    2. Liste as estratégias pendentes
    3. Se houver estratégias e orçamento disponível, produza a primeira da fila
    4. Reporte o resultado final com custos
    """
    response = producer_agent.run(prompt)
    return response.content
```
# 06 - Analyst Agent v2.0 (Com Validação JSON)

## 6.1 Analyst Agent [ATUALIZADO] - `agents/analyst.py`

```python
"""
Agente Analyst v2.0 - Analisa vídeos usando Gemini Vision.
Inclui validação Pydantic dos outputs e versionamento de prompts.
"""

import os
import json
import tempfile
from typing import Optional

from agno.agent import Agent
from agno.models.google import Gemini

from tools.db_tools import db_tools
from tools.storage_tools import storage_tools
from tools.gemini_tools import gemini_tools
from tools.budget_tools import budget_tools
from models.validators import validate_analysis_output
from config.prompts import ANALYSIS_PROMPT
from config.settings import settings


def get_current_prompt_version(prompt_type: str = 'analysis') -> dict:
    """Retorna a versão ativa do prompt de análise."""
    with db_tools.get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, version, prompt_text
                FROM prompt_versions
                WHERE prompt_type = %s AND is_active = true
                ORDER BY created_at DESC LIMIT 1
            """, (prompt_type,))
            row = cur.fetchone()
            if row:
                return {'id': row[0], 'version': row[1], 'prompt_text': row[2]}
            return {'id': None, 'version': 'v1.0', 'prompt_text': None}


def analyze_video(video_id: int, retry_on_invalid: bool = True) -> str:
    """
    Analisa um vídeo usando Gemini Vision com validação de output.
    
    Args:
        video_id: ID do vídeo no banco
        retry_on_invalid: Se True, tenta novamente se JSON for inválido
    """
    try:
        # Verifica orçamento
        can_proceed, reason = budget_tools.check_before_operation('gemini')
        if not can_proceed:
            return f"❌ {reason}"
        
        # Busca vídeo
        video = db_tools.get_video_by_id(video_id)
        if not video:
            return f"❌ Vídeo {video_id} não encontrado"
        if not video['is_transcribed']:
            return f"❌ Vídeo {video_id} ainda não foi transcrito"
        if video['is_analyzed']:
            return f"ℹ️ Vídeo {video_id} já foi analisado"
        
        # Verifica pré-filtro
        if not video.get('passes_prefilter', True):
            return f"⚠️ Vídeo {video_id} não passou no pré-filtro (score: {video.get('statistical_viral_score', 0):.2f})"
        
        # Baixa vídeo do storage
        video_object = video['video_file_path']
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            tmp_path = tmp.name
        
        storage_tools.download_file(video_object, tmp_path)
        
        # Busca versão do prompt
        prompt_info = get_current_prompt_version('analysis')
        prompt_template = prompt_info['prompt_text'] or ANALYSIS_PROMPT
        
        # Monta prompt com contexto
        full_prompt = prompt_template.format(
            transcription=video['transcription'] or 'Não disponível',
            caption=video['caption'] or 'Sem legenda',
            hashtags=', '.join(video.get('hashtags', [])) or 'Sem hashtags',
            views=video['views_count'],
            likes=video['likes_count'],
            comments=video['comments_count']
        )
        
        # Adiciona instrução de JSON estrito
        full_prompt += """

IMPORTANTE: Retorne APENAS um JSON válido, sem texto adicional antes ou depois.
Não use blocos de código markdown (```).
O JSON deve seguir EXATAMENTE o schema especificado.
"""
        
        # Executa análise
        analysis_result = gemini_tools.full_video_analysis(tmp_path, full_prompt)
        raw_response = analysis_result.get('raw_response', '')
        
        # Valida output
        is_valid, parsed_output, error = validate_analysis_output(raw_response)
        
        if not is_valid:
            if retry_on_invalid:
                # Tenta novamente com prompt mais enfático
                print(f"⚠️ JSON inválido na primeira tentativa: {error}. Retentando...")
                full_prompt += f"\n\nATENÇÃO: Sua resposta anterior foi inválida. Erro: {error}\nRetorne um JSON válido!"
                analysis_result = gemini_tools.full_video_analysis(tmp_path, full_prompt)
                raw_response = analysis_result.get('raw_response', '')
                is_valid, parsed_output, error = validate_analysis_output(raw_response)
            
            if not is_valid:
                # Salva mesmo assim, mas marca como inválido
                db_tools.save_analysis(video_id, {
                    'hook_analysis': {},
                    'development': {},
                    'cta_analysis': {},
                    'viral_factors': {},
                    'visual_elements': {},
                    'audio_elements': {},
                    'virality_score': 0,
                    'replicability_score': 0,
                    'production_quality_score': 0,
                    'raw_response': raw_response,
                    'model_used': analysis_result.get('model_used', 'gemini-1.5-pro'),
                    'tokens_used': analysis_result.get('tokens_used'),
                    'is_valid_json': False,
                    'validation_errors': {'error': error},
                    'prompt_version_id': prompt_info['id']
                })
                
                # Registra custo mesmo com erro
                budget_tools.record_cost(0.002, 'gemini')
                
                return f"⚠️ Vídeo {video_id} analisado mas JSON inválido: {error}"
        
        # Extrai dados do output validado
        output_dict = parsed_output.model_dump()
        scores = output_dict.get('scores', {})
        
        # Salva análise válida
        analysis_id = db_tools.save_analysis(video_id, {
            'hook_analysis': output_dict.get('hook', {}),
            'development': output_dict.get('development', {}),
            'cta_analysis': output_dict.get('cta', {}),
            'viral_factors': output_dict.get('viral_factors', {}),
            'visual_elements': output_dict.get('visual_analysis', {}),
            'audio_elements': output_dict.get('audio_analysis', {}),
            'virality_score': scores.get('virality_potential'),
            'replicability_score': scores.get('replicability'),
            'production_quality_score': scores.get('production_quality'),
            'raw_response': raw_response,
            'model_used': analysis_result.get('model_used', 'gemini-1.5-pro'),
            'tokens_used': analysis_result.get('tokens_used'),
            'is_valid_json': True,
            'validation_errors': None,
            'prompt_version_id': prompt_info['id']
        })
        
        # Registra custo
        budget_tools.record_cost(0.002, 'gemini')
        
        # Atualiza uso do prompt
        if prompt_info['id']:
            with db_tools.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE prompt_versions 
                        SET total_uses = total_uses + 1
                        WHERE id = %s
                    """, (prompt_info['id'],))
                    conn.commit()
        
        # Limpa temp
        os.unlink(tmp_path)
        
        # Incrementa contador
        db_tools.increment_counter('videos_analyzed')
        
        return f"""
✅ **Vídeo {video_id} Analisado**

**Scores:**
- Viralidade: {scores.get('virality_potential', 0):.2f}
- Replicabilidade: {scores.get('replicability', 0):.2f}
- Qualidade: {scores.get('production_quality', 0):.2f}

**Hook:** {output_dict.get('hook', {}).get('technique', 'N/A')}
**Narrativa:** {output_dict.get('development', {}).get('narrative_style', 'N/A')}
**CTA:** {output_dict.get('cta', {}).get('type', 'N/A')}

**Prompt Version:** {prompt_info['version']}
**JSON Válido:** ✅
"""
    
    except Exception as e:
        db_tools.set_video_error(video_id, str(e))
        return f"❌ Erro ao analisar vídeo {video_id}: {str(e)}"


def get_pending_analyses(limit: int = 5, only_prefiltered: bool = True) -> str:
    """
    Lista vídeos pendentes de análise.
    
    Args:
        limit: Máximo de vídeos a listar
        only_prefiltered: Se True, só lista vídeos que passaram no pré-filtro
    """
    if only_prefiltered:
        # Usa view otimizada
        with db_tools.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, platform_id, views_count, statistical_viral_score
                    FROM v_prefiltered_pending
                    WHERE is_transcribed = true
                    LIMIT %s
                """, (limit,))
                videos = cur.fetchall()
    else:
        videos = db_tools.get_videos_pending_analysis(limit)
    
    if not videos:
        return "✅ Nenhum vídeo pendente de análise."
    
    result = f"📋 **{len(videos)} vídeos pendentes de análise:**\n"
    for v in videos:
        if isinstance(v, tuple):
            result += f"- **ID {v[0]}:** {v[2]} views, score: {v[3]:.2f}\n"
        else:
            result += f"- **ID {v['id']}:** {v['views_count']} views\n"
    return result


def get_analysis_summary(video_id: int) -> str:
    """Retorna resumo completo da análise de um vídeo."""
    analysis = db_tools.get_analysis_by_video_id(video_id)
    if not analysis:
        return f"❌ Análise do vídeo {video_id} não encontrada"
    
    validation_status = "✅ Válido" if analysis.get('is_valid_json', True) else "⚠️ JSON Inválido"
    
    result = f"""
📊 **Análise do Vídeo {video_id}**

**Validação:** {validation_status}

**Scores:**
- Viralidade: {analysis['virality_score']:.2f}
- Replicabilidade: {analysis['replicability_score']:.2f}
- Qualidade: {analysis['production_quality_score']:.2f}

**Hook:**
{json.dumps(analysis.get('hook_analysis', {}), indent=2, ensure_ascii=False)[:500]}

**Fatores Virais:**
{json.dumps(analysis.get('viral_factors', {}), indent=2, ensure_ascii=False)[:500]}
"""
    
    if analysis.get('validation_errors'):
        result += f"\n**Erros de Validação:**\n{analysis['validation_errors']}"
    
    return result


def get_validation_stats() -> str:
    """Retorna estatísticas de validação das análises."""
    with db_tools.get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_valid_json = true THEN 1 ELSE 0 END) as valid,
                    SUM(CASE WHEN is_valid_json = false THEN 1 ELSE 0 END) as invalid,
                    AVG(virality_score) as avg_virality,
                    AVG(replicability_score) as avg_replicability
                FROM video_analyses
            """)
            row = cur.fetchone()
            
            return f"""
📈 **Estatísticas de Análises**

**Total:** {row[0]}
**Válidas:** {row[1]} ({(row[1]/row[0]*100) if row[0] else 0:.1f}%)
**Inválidas:** {row[2]} ({(row[2]/row[0]*100) if row[0] else 0:.1f}%)

**Médias:**
- Viralidade: {row[3] or 0:.2f}
- Replicabilidade: {row[4] or 0:.2f}
"""


def reanalyze_invalid(limit: int = 5) -> str:
    """Re-analisa vídeos com JSON inválido."""
    with db_tools.get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT va.video_id
                FROM video_analyses va
                WHERE va.is_valid_json = false
                LIMIT %s
            """, (limit,))
            videos = cur.fetchall()
    
    if not videos:
        return "✅ Nenhum vídeo com análise inválida"
    
    results = []
    for (video_id,) in videos:
        # Remove análise anterior
        with db_tools.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM video_analyses WHERE video_id = %s", (video_id,))
                cur.execute("UPDATE viral_videos SET is_analyzed = false WHERE id = %s", (video_id,))
                conn.commit()
        
        # Re-analisa
        result = analyze_video(video_id, retry_on_invalid=True)
        results.append(f"Vídeo {video_id}: {result[:100]}...")
    
    return f"♻️ Re-análise concluída:\n" + "\n".join(results)


# ============================================
# CRIAÇÃO DO AGENTE
# ============================================

analyst_agent = Agent(
    name="Analyst Agent v2",
    model=Gemini(id="gemini-1.5-pro"),
    instructions="""
    Você é um especialista em engenharia reversa de conteúdo viral.
    
    ## Suas Responsabilidades:
    
    1. **Analisar vídeos** usando Gemini Vision
       - Identificar padrões de sucesso
       - Avaliar hook, desenvolvimento, CTA
       - Calcular scores de viralidade
    
    2. **Validar outputs**
       - Garantir JSON válido
       - Re-tentar se necessário
       - Registrar erros de validação
    
    3. **Respeitar pré-filtro**
       - Priorizar vídeos com alto score estatístico
       - Economizar tokens em vídeos de baixa qualidade
    
    ## Métricas Importantes:
    
    - **Virality Score >= 0.7**: Bom candidato para estratégia
    - **Replicability >= 0.6**: Fácil de replicar
    - **JSON Válido**: Essencial para downstream
    
    ## Comandos:
    
    - `analyze_video(video_id)`: Analisa um vídeo
    - `get_pending_analyses()`: Lista pendentes
    - `get_validation_stats()`: Estatísticas de validação
    - `reanalyze_invalid()`: Re-analisa JSONs inválidos
    """,
    tools=[
        analyze_video,
        get_pending_analyses,
        get_analysis_summary,
        get_validation_stats,
        reanalyze_invalid
    ],
    show_tool_calls=True,
    markdown=True
)


def run_analyze_pending(limit: int = 5) -> str:
    """Analisa vídeos pendentes que passaram no pré-filtro."""
    prompt = f"""
    Analise até {limit} vídeos pendentes.
    
    1. Liste os vídeos pendentes (apenas pré-filtrados)
    2. Analise cada um
    3. Mostre estatísticas de validação ao final
    """
    response = analyst_agent.run(prompt)
    return response.content
```

---

## 6.2 Watcher Agent com Pré-Filtro - `agents/watcher.py`

```python
"""
Agente Watcher v2.0 - Monitora perfis e aplica pré-filtro estatístico.
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from tools.apify_tools import apify_tools
from tools.db_tools import db_tools
from tools.budget_tools import budget_tools
from config.settings import settings


def scrape_profile(username: str, max_results: int = 20) -> str:
    """
    Faz scraping dos Reels de um perfil do Instagram.
    Aplica pré-filtro estatístico automaticamente.
    """
    try:
        # Verifica orçamento
        can_proceed, reason = budget_tools.check_before_operation('apify')
        if not can_proceed:
            return f"❌ {reason}"
        
        profiles = db_tools.get_active_profiles()
        profile = next((p for p in profiles if p['username'] == username), None)
        profile_id = profile['id'] if profile else None
        
        results = apify_tools.scrape_instagram_profile(username=username, max_results=max_results)
        
        # Filtra por thresholds básicos
        qualified = []
        for video in results:
            if (video['views_count'] >= settings.min_views_threshold or
                video['likes_count'] >= settings.min_likes_threshold or
                video['comments_count'] >= settings.min_comments_threshold):
                video['profile_id'] = profile_id
                qualified.append(video)
        
        # Salva no banco (o trigger calcula statistical_viral_score)
        saved_count = 0
        prefiltered_count = 0
        for video in qualified:
            try:
                video_id = db_tools.save_viral_video(video)
                saved_count += 1
                
                # Verifica se passou no pré-filtro
                saved_video = db_tools.get_video_by_id(video_id)
                if saved_video and saved_video.get('passes_prefilter'):
                    prefiltered_count += 1
            except Exception as e:
                print(f"Erro salvando vídeo {video.get('shortcode')}: {e}")
        
        if profile_id:
            db_tools.update_profile_scraped(profile_id, saved_count)
        
        # Registra custo estimado do Apify
        budget_tools.record_cost(len(results) * 0.0023, 'apify')  # ~$2.30/1000
        
        db_tools.increment_counter('scraping_runs')
        db_tools.increment_counter('videos_collected', saved_count)
        
        return f"""
✅ **Scraping de @{username} concluído**

- Encontrados: {len(results)}
- Qualificados (thresholds): {len(qualified)}
- Salvos: {saved_count}
- **Passaram pré-filtro: {prefiltered_count}** (prontos para análise)
"""
    except Exception as e:
        return f"❌ Erro no scraping de @{username}: {str(e)}"


def get_profiles_to_monitor() -> str:
    """Retorna lista de perfis ativos para monitoramento."""
    profiles = db_tools.get_active_profiles()
    if not profiles:
        return "Nenhum perfil cadastrado para monitoramento."
    
    result = "📋 **Perfis para monitorar:**\n"
    for p in profiles:
        result += f"- @{p['username']} (Nicho: {p['niche'] or 'N/A'}, Prioridade: {p['priority']})\n"
    return result


def add_profile_to_monitor(username: str, niche: str = None, priority: int = 1,
                           avg_views: int = 50000, avg_likes: int = 5000) -> str:
    """
    Adiciona um novo perfil para monitoramento.
    
    Args:
        username: @ do perfil
        niche: Categoria do conteúdo
        priority: 1-5 (5 = máxima)
        avg_views: Média de views do nicho (para normalização)
        avg_likes: Média de likes do nicho (para normalização)
    """
    try:
        profile_id = db_tools.add_profile(username, niche, priority)
        
        # Atualiza médias do nicho se fornecidas
        with db_tools.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE monitored_profiles
                    SET niche_avg_views = %s,
                        niche_avg_likes = %s,
                        niche_avg_comments = %s
                    WHERE id = %s
                """, (avg_views, avg_likes, avg_likes // 10, profile_id))
                conn.commit()
        
        return f"""
✅ **Perfil @{username} adicionado**

- ID: {profile_id}
- Nicho: {niche or 'N/A'}
- Prioridade: {priority}
- Médias do nicho: {avg_views} views, {avg_likes} likes
"""
    except Exception as e:
        return f"❌ Erro ao adicionar perfil: {str(e)}"


def get_prefilter_stats() -> str:
    """Retorna estatísticas do pré-filtro."""
    with db_tools.get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN passes_prefilter = true THEN 1 ELSE 0 END) as passed,
                    AVG(statistical_viral_score) as avg_score,
                    AVG(CASE WHEN passes_prefilter = true THEN statistical_viral_score END) as avg_passed_score
                FROM viral_videos
            """)
            row = cur.fetchone()
            
            pass_rate = (row[1] / row[0] * 100) if row[0] else 0
            
            return f"""
📊 **Estatísticas do Pré-Filtro**

**Total de vídeos:** {row[0]}
**Passaram no filtro:** {row[1]} ({pass_rate:.1f}%)
**Score médio geral:** {row[2] or 0:.3f}
**Score médio (aprovados):** {row[3] or 0:.3f}

**Threshold atual:** {settings.min_statistical_score}
"""


# Agente
watcher_agent = Agent(
    name="Watcher Agent v2",
    model=OpenAIChat(id="gpt-4o-mini"),
    instructions="""
    Você é um agente de monitoramento de conteúdo viral no Instagram.
    
    ## Responsabilidades:
    
    1. Monitorar perfis cadastrados
    2. Coletar Reels que atendem thresholds mínimos
    3. Aplicar pré-filtro estatístico (Viral Score)
    4. Reportar quantos passaram no pré-filtro
    
    ## Pré-Filtro Estatístico:
    
    O sistema calcula automaticamente um score 0-1 baseado em:
    - 40% Views normalizadas
    - 40% Engagement normalizado
    - 20% Recência
    
    Vídeos com score >= 0.6 passam para análise profunda (Gemini).
    """,
    tools=[scrape_profile, get_profiles_to_monitor, add_profile_to_monitor, get_prefilter_stats],
    show_tool_calls=True,
    markdown=True
)


def run_daily_watch() -> str:
    """Executa o monitoramento diário de todos os perfis ativos."""
    profiles = db_tools.get_active_profiles()
    if not profiles:
        return "Nenhum perfil para monitorar."
    
    usernames = [p['username'] for p in profiles]
    prompt = f"""
    Execute o monitoramento diário dos seguintes perfis:
    Perfis: {', '.join(['@' + u for u in usernames])}
    
    Para cada perfil, faça o scraping dos últimos 20 Reels.
    Ao final, mostre as estatísticas do pré-filtro.
    """
    response = watcher_agent.run(prompt)
    return response.content
```
# 07 - Prompts Otimizados v2.0

## 7.1 Arquivo: `config/prompts.py`

```python
"""
Prompts otimizados para os agentes v2.0.
Todos os prompts exigem output JSON estrito e validável.
"""

# ============================================
# ANALYSIS PROMPT (Gemini Vision)
# ============================================

ANALYSIS_PROMPT = """
Você é um especialista em engenharia reversa de conteúdo viral.
Analise este vídeo do Instagram/TikTok e extraia insights estruturados.

## CONTEXTO DO VÍDEO:
- Transcrição: {transcription}
- Legenda: {caption}
- Hashtags: {hashtags}
- Views: {views}
- Likes: {likes}
- Comentários: {comments}

## SUA TAREFA:
Analise o vídeo frame a frame e retorne um JSON com a estrutura EXATA abaixo.

## OUTPUT OBRIGATÓRIO (JSON ESTRITO):

{{
  "hook": {{
    "duration_seconds": <float 0-10>,
    "technique": "<curiosity_gap|pattern_interrupt|bold_claim|question|shocking_stat|controversy|transformation|other>",
    "text_transcription": "<texto falado nos primeiros 3 segundos ou null>",
    "visual_description": "<descrição visual do hook>",
    "effectiveness_score": <float 0-1>
  }},
  "development": {{
    "narrative_style": "<tutorial|story|demonstration|comparison|transformation|behind_scenes|listicle|other>",
    "key_points": ["<ponto 1>", "<ponto 2>", ...],
    "pacing": "<fast|medium|slow>",
    "retention_techniques": ["<técnica 1>", "<técnica 2>", ...]
  }},
  "cta": {{
    "type": "<comment|like|share|follow|link|save|other>",
    "text": "<texto do CTA ou null>",
    "placement": "<start|middle|end>",
    "effectiveness": <float 0-1>
  }},
  "visual_analysis": {{
    "lighting": "<descrição da iluminação>",
    "color_palette": ["<cor 1>", "<cor 2>", ...],
    "camera_movements": ["<movimento 1>", ...],
    "text_overlays": <true|false>,
    "transitions": ["<tipo 1>", ...],
    "thumbnail_hook": "<elemento que chama atenção na thumbnail ou null>"
  }},
  "audio_analysis": {{
    "music_type": "<trending|original|none>",
    "voice_tone": "<energetic|calm|serious|humorous|inspirational>",
    "sound_effects": <true|false>,
    "music_bpm": <int 60-200 ou null>
  }},
  "viral_factors": {{
    "trend_alignment": "<descrição do alinhamento com tendências>",
    "emotional_trigger": "<emoção principal evocada>",
    "shareability_reason": "<motivo pelo qual pessoas compartilhariam>",
    "target_audience": "<público-alvo identificado>"
  }},
  "scores": {{
    "virality_potential": <float 0-1>,
    "replicability": <float 0-1>,
    "production_quality": <float 0-1>
  }}
}}

## REGRAS:
1. Retorne APENAS o JSON, sem texto antes ou depois
2. Não use blocos de código markdown (```)
3. Todos os campos são obrigatórios
4. Use exatamente os valores permitidos nos campos enum
5. Scores devem ser realistas (0.7+ indica viral genuíno)
"""


# ============================================
# STRATEGY PROMPT (GPT-4o)
# ============================================

STRATEGY_PROMPT = """
Você é um copywriter especialista em viralização de conteúdo para Instagram Reels.

## VÍDEO VIRAL DE REFERÊNCIA:
- Transcrição: {transcription}
- Legenda: {caption}
- Métricas: {views} views, {likes} likes, {comments} comentários

## ANÁLISE DO VÍDEO:
- Hook: {hook_analysis}
- Desenvolvimento: {development}
- CTA: {cta_analysis}
- Fatores virais: {viral_factors}
- Elementos visuais: {visual_elements}
- Score de viralidade: {virality_score}

## NICHO ALVO: {target_niche}

## SUA TAREFA:
Crie uma NOVA estratégia de conteúdo inspirada no padrão viral identificado.
O conteúdo deve ser ORIGINAL, não uma cópia.

## OUTPUT OBRIGATÓRIO (JSON ESTRITO):

{{
  "titulo": "<título do vídeo (max 100 chars)>",
  "conceito_central": "<conceito único que diferencia este conteúdo>",
  "roteiro": {{
    "hook": {{
      "duracao": "0-3s",
      "texto_falado": "<texto que será narrado no hook - IMPACTANTE>",
      "acao_visual": "<descrição da ação visual>"
    }},
    "desenvolvimento": {{
      "duracao": "3-25s",
      "texto_falado": "<texto da parte principal - INFORMATIVO e ENGAJANTE>",
      "acao_visual": "<descrição das ações visuais>"
    }},
    "cta": {{
      "duracao": "25-30s",
      "texto_falado": "<texto do call-to-action - URGENTE>",
      "acao_visual": "<descrição da ação visual>"
    }}
  }},
  "veo_prompts": [
    {{
      "scene": 1,
      "duration": "<4s|5s|6s|7s|8s>",
      "prompt": "<prompt detalhado para Veo 3.1 - MÍNIMO 50 palavras>",
      "camera": "<static shot|slow pan|tracking shot|drone shot|handheld|zoom in|zoom out>",
      "lighting": "<natural|studio|dramatic|soft|backlit|golden hour>"
    }},
    {{
      "scene": 2,
      "duration": "...",
      "prompt": "...",
      "camera": "...",
      "lighting": "..."
    }}
  ],
  "publicacao": {{
    "caption": "<legenda completa com emojis e call-to-action>",
    "hashtags": ["<hashtag1>", "<hashtag2>", ...],
    "melhor_horario": "<horário sugerido ex: 18h-20h>",
    "primeira_frase_hook": "<primeira frase que aparece no feed>"
  }}
}}

## DICAS PARA PROMPTS VEO 3.1:
1. Sempre inclua: "4k, cinematic lighting, photorealistic, high quality"
2. Especifique ambiente, sujeito, ação e emoção
3. Movimentos de câmera: "slow pan left", "tracking shot following subject"
4. Máximo 8 segundos por cena
5. Seja MUITO específico - quanto mais detalhes, melhor o resultado

## REGRAS:
1. Retorne APENAS o JSON, sem texto antes ou depois
2. Não use blocos de código markdown (```)
3. O roteiro deve ter EXATAMENTE 3 seções: hook, desenvolvimento, cta
4. Mínimo 3 cenas no veo_prompts, máximo 8
5. Duração total: 25-35 segundos
6. Texto falado deve ser natural para TTS (sem emojis, sem caps lock)
"""


# ============================================
# PRODUCER INSTRUCTIONS (Enhancer de Prompts Veo)
# ============================================

VEO_PROMPT_ENHANCER = """
Você otimiza prompts para o Google Veo 3.1.

## PROMPT ORIGINAL:
{original_prompt}

## DURAÇÃO: {duration}

## REGRAS DE OTIMIZAÇÃO:

1. **Adicione qualificadores técnicos:**
   - "4k resolution, cinematic lighting, photorealistic rendering"
   - "professional cinematography, high production value"

2. **Especifique movimento de câmera:**
   - Se estático: "static shot, locked camera, steady frame"
   - Se movimento: "smooth tracking shot", "slow dolly in", "gentle pan right"

3. **Defina iluminação:**
   - "natural daylight", "golden hour sunlight", "soft studio lighting"
   - "dramatic shadows", "backlit silhouette", "neon glow"

4. **Ambiente e atmosfera:**
   - Cores dominantes
   - Textura do ambiente
   - Profundidade de campo

5. **Ação clara:**
   - Sujeito fazendo ação específica
   - Expressão facial/corporal
   - Interação com ambiente

## OUTPUT:
Retorne APENAS o prompt otimizado, sem explicações.
Máximo 200 palavras.
"""


# ============================================
# TTS SCRIPT OPTIMIZER
# ============================================

TTS_SCRIPT_OPTIMIZER = """
Você otimiza textos para narração TTS (Text-to-Speech).

## TEXTO ORIGINAL:
{original_text}

## REGRAS:
1. Remova emojis e caracteres especiais
2. Converta números para extenso quando natural ("3" → "três")
3. Adicione pontuação para pausas naturais
4. Use "..." para pausas dramáticas
5. Evite siglas - escreva por extenso
6. Mantenha frases curtas (máximo 15 palavras)
7. Use linguagem conversacional

## OUTPUT:
Retorne APENAS o texto otimizado para TTS, sem explicações.
"""


# ============================================
# PROMPT VERSIONS (para o banco de dados)
# ============================================

PROMPT_VERSIONS = {
    'analysis': {
        'v1.0': ANALYSIS_PROMPT,
    },
    'strategy': {
        'v1.0': STRATEGY_PROMPT,
    },
    'veo_enhancer': {
        'v1.0': VEO_PROMPT_ENHANCER,
    },
    'tts_optimizer': {
        'v1.0': TTS_SCRIPT_OPTIMIZER,
    }
}


def get_prompt(prompt_type: str, version: str = 'v1.0') -> str:
    """Retorna um prompt específico por tipo e versão."""
    return PROMPT_VERSIONS.get(prompt_type, {}).get(version, '')


def list_prompt_versions() -> dict:
    """Lista todas as versões de prompts disponíveis."""
    return {
        prompt_type: list(versions.keys())
        for prompt_type, versions in PROMPT_VERSIONS.items()
    }
```

---

## 7.2 Exemplos de Outputs Esperados

### Exemplo de Output do Gemini (Análise)

```json
{
  "hook": {
    "duration_seconds": 2.5,
    "technique": "curiosity_gap",
    "text_transcription": "Você não vai acreditar no que descobri sobre produtividade",
    "visual_description": "Close-up do rosto com expressão de surpresa, fundo desfocado",
    "effectiveness_score": 0.85
  },
  "development": {
    "narrative_style": "tutorial",
    "key_points": [
      "Técnica Pomodoro modificada",
      "Bloqueio de distrações",
      "Revisão semanal"
    ],
    "pacing": "fast",
    "retention_techniques": ["text overlays", "jump cuts", "sound effects"]
  },
  "cta": {
    "type": "follow",
    "text": "Segue pra mais dicas de produtividade",
    "placement": "end",
    "effectiveness": 0.75
  },
  "visual_analysis": {
    "lighting": "Iluminação natural de janela, suave e difusa",
    "color_palette": ["branco", "azul", "bege"],
    "camera_movements": ["static", "zoom in lento no final"],
    "text_overlays": true,
    "transitions": ["jump cut", "fade"],
    "thumbnail_hook": "Expressão de surpresa com texto 'PRODUTIVIDADE'"
  },
  "audio_analysis": {
    "music_type": "trending",
    "voice_tone": "energetic",
    "sound_effects": true,
    "music_bpm": 120
  },
  "viral_factors": {
    "trend_alignment": "Produtividade é tema evergreen com picos em janeiro e setembro",
    "emotional_trigger": "Frustração com falta de foco, desejo de melhoria",
    "shareability_reason": "Dicas práticas e aplicáveis imediatamente",
    "target_audience": "Profissionais 25-35, estudantes universitários"
  },
  "scores": {
    "virality_potential": 0.78,
    "replicability": 0.85,
    "production_quality": 0.72
  }
}
```

### Exemplo de Output do GPT-4o (Estratégia)

```json
{
  "titulo": "A técnica de 2 minutos que mudou minha produtividade",
  "conceito_central": "Regra dos 2 minutos aplicada ao trabalho remoto com twist de gamificação",
  "roteiro": {
    "hook": {
      "duracao": "0-3s",
      "texto_falado": "Eu perdia 3 horas por dia até descobrir essa técnica simples.",
      "acao_visual": "Close no rosto com expressão de revelação importante"
    },
    "desenvolvimento": {
      "duracao": "3-25s",
      "texto_falado": "A regra é simples. Se algo leva menos de dois minutos, faça agora. Mas aqui está o segredo que ninguém conta. Transforme isso em um jogo. Cada tarefa completada vale um ponto. Dez pontos e você ganha uma pausa de cinco minutos. Em uma semana, minha produtividade triplicou.",
      "acao_visual": "Demonstração visual de tarefas sendo completadas, contador de pontos, celebração"
    },
    "cta": {
      "duracao": "25-30s",
      "texto_falado": "Salva esse vídeo e comenta quantos pontos você fez hoje.",
      "acao_visual": "Gesto de salvar, texto animado com call-to-action"
    }
  },
  "veo_prompts": [
    {
      "scene": 1,
      "duration": "4s",
      "prompt": "Professional young adult in modern home office, close-up shot of face showing moment of realization, natural window lighting creating soft shadows, warm color grading, 4k cinematic quality, photorealistic, shallow depth of field with blurred background showing desk setup",
      "camera": "static shot",
      "lighting": "natural"
    },
    {
      "scene": 2,
      "duration": "6s",
      "prompt": "Hands typing on laptop keyboard in modern minimalist workspace, sticky notes being checked off one by one, satisfying visual of task completion, overhead shot transitioning to side angle, soft studio lighting, 4k resolution, professional cinematography",
      "camera": "slow pan",
      "lighting": "studio"
    },
    {
      "scene": 3,
      "duration": "5s",
      "prompt": "Digital counter incrementing from 0 to 10 with celebration particles, gamification UI elements floating in 3D space, vibrant colors against clean white background, motion graphics style, 4k quality, modern tech aesthetic",
      "camera": "zoom in",
      "lighting": "soft"
    },
    {
      "scene": 4,
      "duration": "4s",
      "prompt": "Same professional from scene 1, now smiling confidently at camera, making save gesture with hand, animated text appearing beside them, warm inviting atmosphere, golden hour lighting through window, 4k cinematic, photorealistic rendering",
      "camera": "static shot",
      "lighting": "golden hour"
    }
  ],
  "publicacao": {
    "caption": "A técnica que me fez parar de procrastinar 🎯\n\nEu testei por 30 dias e os resultados foram surreais.\n\nSalva pra não esquecer e comenta quantos pontos você fez! 👇\n\n#produtividade #dicasdeestudo #trabalhoremoto #focototal #organizacao",
    "hashtags": [
      "produtividade",
      "dicasdeestudo",
      "trabalhoremoto",
      "focototal",
      "organizacao",
      "homeoffice",
      "crescimentopessoal"
    ],
    "melhor_horario": "18h-20h",
    "primeira_frase_hook": "A técnica que me fez parar de procrastinar 🎯"
  }
}
```
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
