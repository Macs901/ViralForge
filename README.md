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
