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
