# ViralForge - Sistema Autonomo de Videos Virais

Sistema completo para analise, estrategia e producao de videos virais para Instagram Reels, TikTok e YouTube Shorts.

## Visao Geral

ViralForge e uma plataforma que automatiza todo o pipeline de criacao de videos virais:
1. **Coleta** videos virais do Instagram via Apify
2. **Analisa** semanticamente com IA (Gemini/Claude)
3. **Gera estrategias** de replicacao com GPT-4
4. **Produz** videos com Veo 3.1 + TTS

## CHANGELOG v2.1

### Novas Funcionalidades v2.1
| Feature | Descricao |
|---------|-----------|
| 🎯 **Analise Semantica Completa** | Cores, enquadramento, expressoes, audio, performance |
| 🎙️ **Groq Whisper** | Transcricao 10x mais rapida e GRATUITA via API |
| 📝 **Roteiro Sugerido** | Script pronto baseado nos padroes do video |
| 🔧 **Guia de Replicacao** | Equipamentos, dificuldade, tempo, adaptacoes |
| 🤖 **MCP Expandido** | Novas tools para analise semantica via Claude |

### Funcionalidades v2.0
| Feature | Descricao |
|---------|-----------|
| 🎤 **TTS Integrado** | Narracao automatica com edge-tts (gratuito) + ElevenLabs (fallback) |
| 🎵 **Mixagem de Audio** | FFmpeg mixa narracao + musica de fundo + video |
| 📊 **Pre-filtro Estatistico** | Viral Score calculado ANTES de gastar tokens Gemini |
| ✅ **Validacao JSON** | Schemas Pydantic garantem outputs estruturados |
| 💰 **Budget Awareness** | Controle de custos com abort automatico |
| 📈 **Observabilidade** | Metricas por run, tracking de custos detalhado |

### Otimizacoes para Hardware
| Componente | Configuracao | Motivo |
|------------|--------------|--------|
| Whisper | `medium` ou `groq` | CPU-only ou API gratuita |
| Celery | `concurrency=2` | Evita OOM com Whisper local |
| PostgreSQL | `shared_buffers=2GB` | Aproveita RAM disponivel |

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

## MCP Server (ViralForge)

Servidor MCP para integracao com Claude Desktop e outras aplicacoes.

### Tools Disponiveis

| Tool | Descricao |
|------|-----------|
| `scrape_profile` | Coleta videos de um perfil Instagram |
| `analyze_video` | Analisa video com Gemini/Claude |
| `analyze_video_with_claude` | Forca analise com Claude |
| `download_video` | Baixa video do Instagram |
| `transcribe_video` | Transcreve audio (local ou Groq) |
| `full_pipeline` | Download + Transcricao + Analise |
| `get_video_for_analysis` | Retorna video + metadados para analise direta |
| `get_semantic_analysis` | Retorna analise semantica completa |
| `generate_strategy` | Gera estrategia de replicacao |
| `produce_video` | Produz video final |
| `get_budget_status` | Status do orcamento |
| `list_videos` | Lista videos coletados |
| `list_strategies` | Lista estrategias geradas |

### Configuracao Claude Desktop

```json
{
  "mcpServers": {
    "viralforge": {
      "command": "python",
      "args": ["-m", "src.mcp.server"],
      "cwd": "/home/marcocardoso/projects/ViralForge",
      "env": {"PYTHONPATH": "/home/marcocardoso/projects/ViralForge"}
    }
  }
}
```

### Configuracao Docker (SSE)

```bash
# Container rodando em http://localhost:8002/sse
docker compose up -d mcp
```

---

## Analise Semantica Completa

A analise de video inclui:

### Elementos Visuais
- Cores dominantes e paleta cromatica
- Enquadramento (close, medio, aberto)
- Iluminacao (natural, artificial, ring light)
- Texto na tela (fonte, cor, posicao, timing)
- Transicoes e cortes por minuto

### Elementos de Audio
- Tipo de voz (direta, voz off, mista)
- Tom de voz (intimo, energetico, didatico)
- Musica (tipo, volume, timing)
- Efeitos sonoros

### Elementos de Performance
- Expressoes faciais
- Linguagem corporal
- Contato visual com camera
- Nivel de energia
- Bordoes e frases de efeito

### Guia de Replicacao
- Equipamentos necessarios
- Nivel de dificuldade
- Tempo estimado de producao
- Elementos-chave para copiar
- Sugestoes de adaptacao

### Roteiro Sugerido
- Script pronto de 30-60s baseado nos padroes do video

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
│ PROCESSOR   │ ◄─── Whisper local ou Groq (GRATIS)
│ (Download+  │      Groq: 10x mais rapido
│  Transcricao)│
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

### Por que Groq Whisper como opcao?
- **Gratuito** - Tier gratuito generoso
- **10x mais rapido** - API vs processamento local
- **Sem GPU** - Nao precisa de recursos locais
- **Fallback** - Whisper local disponivel se necessario

### Por que Whisper medium (local)?
- **Offline** - Funciona sem internet
- **Privacidade** - Dados nao saem do servidor
- **Sem limites** - Sem rate limiting

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

---

## Integracao com MacsMorpheus

ViralForge e MacsMorpheus sao projetos integrados que compartilham um banco de dados unificado de transcricoes.

| Projeto | Proposito | Funcionalidades |
|---------|-----------|-----------------|
| **ViralForge** | Analise e producao de videos virais | Scraping, analise semantica, estrategia, producao |
| **MacsMorpheus** | Assistente multi-agentes via WhatsApp | Bot WhatsApp, tarefas, copywriting, marketing |

### Arquitetura de Integracao

```
MacsMorpheus                          ViralForge
┌─────────────────┐                  ┌─────────────────────┐
│   Copywriter    │ ──── HTTP ────► │   MCP Server        │
│   Agent         │                  │   (porta 8001)      │
└─────────────────┘                  └─────────────────────┘
        │                                     │
        │                                     ▼
        │                            ┌─────────────────────┐
        │                            │   PostgreSQL        │
        │                            │   (banco unificado) │
        │                            └─────────────────────┘
        │                                     │
        └─────────────────────────────────────┘
              Transcricoes unificadas
```

### MCP Tools para Integracao

Novas tools expostas via HTTP para consumo pelo MacsMorpheus:

| Tool | Endpoint | Descricao |
|------|----------|-----------|
| `ingest_video_from_url` | POST /tools/ingest_video_from_url | Baixa video de YouTube/TikTok/Instagram |
| `list_creators` | POST /tools/list_creators | Lista criadores com estatisticas |
| `get_creator_transcriptions` | POST /tools/get_creator_transcriptions | Retorna transcricoes de um criador |
| `search_transcriptions` | POST /tools/search_transcriptions | Busca full-text com contexto |

### Video Downloaders

ViralForge agora suporta download de multiplas plataformas:

| Plataforma | Biblioteca | Fallbacks |
|------------|------------|-----------|
| YouTube | yt-dlp | - |
| TikTok | yt-dlp | - |
| Instagram | gallery-dl | Meta Graph API, yt-dlp |

### Divisao de Responsabilidades

| Funcionalidade | Responsavel | Via |
|----------------|-------------|-----|
| Download de videos (YouTube/TikTok/Instagram) | ViralForge | MCP Tools |
| Transcricao de videos | ViralForge | Whisper local/Groq |
| Banco de transcricoes | ViralForge | PostgreSQL + MCP |
| Analise de videos virais | ViralForge | Gemini/Claude |
| Producao de videos | ViralForge | Veo 3.1 + TTS |
| Transcricao de audios WhatsApp | MacsMorpheus | Groq Whisper |
| Copywriting e roteiros via chat | MacsMorpheus | Agente Copywriter |

---

**Versao:** 2.1.0
**Data:** Dezembro 2024
**Hardware Alvo:** 4 vCPUs, 15GB RAM, CPU-only
