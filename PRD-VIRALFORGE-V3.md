# ViralForge v3.0 - Product Requirements Document (PRD)

## Documento de Requisitos do Produto

**Versao:** 3.0
**Data:** Dezembro 2024
**Autor:** Marco Cardoso
**Status:** Draft

---

## 1. Visao Executiva

### 1.1 O que e o ViralForge?

**ViralForge** e uma plataforma autonoma de inteligencia competitiva e producao de conteudo viral. O sistema monitora criadores de sucesso em multiplas plataformas, analisa padroes de viralidade, extrai insights acionaveis e automatiza a producao de conteudo similar adaptado ao seu estilo.

### 1.2 Proposta de Valor

> "Transformar horas de pesquisa manual em insights automatizados que geram conteudo viral em minutos."

| Problema | Solucao ViralForge |
|----------|-------------------|
| Gastar horas pesquisando tendencias | Monitoramento automatico 24/7 de criadores de sucesso |
| Nao entender por que um video viralizou | Analise semantica profunda com IA (visual, audio, narrativa) |
| Dificuldade em replicar formatos | Roteiros prontos baseados em padroes comprovados |
| Producao demorada de conteudo | Geracao automatizada de videos com IA |
| Perder tendencias em tempo real | Alertas de tendencias emergentes |

### 1.3 Diferencial Competitivo

```
Ferramentas Tradicionais          ViralForge
──────────────────────────────    ──────────────────────────────
Metricas superficiais       →     Analise semantica profunda
Dados historicos            →     Monitoramento em tempo real
Insights manuais            →     Insights automatizados por IA
Sem producao                →     Producao end-to-end automatizada
Plataforma unica            →     Multi-plataforma integrada
Interface separada          →     Integrado ao seu workflow (WhatsApp, Claude)
```

---

## 2. Estado Atual (v2.1)

### 2.1 Arquitetura Existente

```
┌─────────────────────────────────────────────────────────────┐
│                     VIRALFORGE v2.1                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│  │ WATCHER  │ → │ ANALYST  │ → │STRATEGIST│ → │ PRODUCER │ │
│  │          │   │          │   │          │   │          │ │
│  │ Scraping │   │ Gemini   │   │ GPT-4    │   │ Veo+TTS  │ │
│  │ Apify    │   │ Claude   │   │ Roteiros │   │ FFmpeg   │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘ │
│       │              │              │              │        │
│       └──────────────┴──────────────┴──────────────┘        │
│                          │                                  │
│                    PostgreSQL                               │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  MCP Server (32 tools) │ REST API │ Integracao SparkOne     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Funcionalidades Atuais

| Agente | Funcao | Status |
|--------|--------|--------|
| **Watcher** | Monitora perfis Instagram via Apify | ✅ Funcional |
| **Analyst** | Analisa videos com Gemini/Claude | ✅ Funcional |
| **Strategist** | Gera estrategias de replicacao | ✅ Funcional |
| **Producer** | Produz videos com Veo + TTS | ✅ Funcional |

### 2.3 Limitacoes Atuais

| Limitacao | Impacto | Prioridade |
|-----------|---------|------------|
| Apenas Instagram | Perde TikTok/YouTube trends | Alta |
| Sem monitoramento de Stories | Perde conteudo efemero | Alta |
| Sem download de Carrosseis | Perde formato popular | Alta |
| Analise reativa (nao proativa) | Perde timing de trends | Media |
| Sem deteccao de tendencias | Apenas analisa individualmente | Media |
| Sem personalizacao de estilo | Conteudo generico | Media |
| Sem agendamento de publicacao | Publicacao manual | Baixa |

---

## 3. Visao v3.0 - Evolucao Completa

### 3.1 Pilares Estrategicos

```
                    ┌─────────────────────┐
                    │   VIRALFORGE v3.0   │
                    └──────────┬──────────┘
                               │
       ┌───────────────────────┼───────────────────────┐
       │                       │                       │
       ▼                       ▼                       ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  INTELIGENCIA│      │   PRODUCAO   │      │  PUBLICACAO  │
│  COMPETITIVA │      │  AUTOMATIZADA│      │  INTELIGENTE │
├──────────────┤      ├──────────────┤      ├──────────────┤
│ Multi-plat.  │      │ AI Generativa│      │ Agendamento  │
│ Trends       │      │ Personalizac.│      │ Multi-canal  │
│ Benchmarking │      │ A/B Testing  │      │ Analytics    │
└──────────────┘      └──────────────┘      └──────────────┘
```

### 3.2 Novos Agentes

| Agente | Funcao | Novidade |
|--------|--------|----------|
| **Trend Hunter** | Detecta tendencias emergentes em tempo real | 🆕 Novo |
| **Style Cloner** | Aprende e replica seu estilo unico | 🆕 Novo |
| **Content Scheduler** | Agenda e publica automaticamente | 🆕 Novo |
| **Performance Tracker** | Monitora resultados e otimiza | 🆕 Novo |
| **Competitor Intel** | Benchmarking profundo de concorrentes | 🆕 Novo |

---

## 4. Funcionalidades Detalhadas

### 4.1 FASE 1: Expansao Multi-Plataforma (Prioridade Alta)

#### 4.1.1 Suporte a TikTok

```yaml
Funcionalidade: Monitoramento TikTok
Status: Planejado
Prioridade: P0 (Critica)

Requisitos:
  - Scraping de perfis TikTok (yt-dlp + TikTok API)
  - Download de videos sem marca d'agua
  - Extracao de metricas (views, likes, comments, shares)
  - Deteccao de sons/audios trending
  - Analise de hashtags e desafios

Metricas de Sucesso:
  - 95% taxa de sucesso no download
  - < 5s por video baixado
  - Cobertura de 100% das metricas publicas
```

#### 4.1.2 Suporte a YouTube Shorts

```yaml
Funcionalidade: Monitoramento YouTube Shorts
Status: Planejado
Prioridade: P0 (Critica)

Requisitos:
  - Scraping de canais focados em Shorts
  - Download via yt-dlp
  - Extracao de metricas (views, likes, comments)
  - Analise de SEO (titulo, descricao, tags)
  - Deteccao de thumbnails eficazes

Metricas de Sucesso:
  - 99% taxa de sucesso (YouTube API robusta)
  - Metricas em tempo real
```

#### 4.1.3 Instagram Stories e Carrosseis

```yaml
Funcionalidade: Captura de Stories e Carrosseis
Status: Planejado
Prioridade: P0 (Critica)

Requisitos:
  Stories:
    - Captura antes de expirar (24h)
    - Download de imagens e videos
    - Extracao de stickers, enquetes, links
    - Deteccao de mentions e hashtags
    - Historico de stories salvos

  Carrosseis:
    - Download de todas as imagens/videos
    - Analise de sequencia narrativa
    - Extracao de textos em cada slide
    - Analise de call-to-action final

Metricas de Sucesso:
  - 90% de stories capturados antes de expirar
  - 100% de slides de carrosseis baixados
```

#### 4.1.4 Twitter/X Videos

```yaml
Funcionalidade: Monitoramento Twitter/X
Status: Planejado
Prioridade: P1 (Alta)

Requisitos:
  - Monitoramento de tweets com video
  - Download de videos nativos e externos
  - Analise de threads virais
  - Deteccao de tweets em alta
  - Extracao de quote tweets e respostas
```

### 4.2 FASE 2: Deteccao de Tendencias (Prioridade Alta)

#### 4.2.1 Trend Hunter Agent

```yaml
Funcionalidade: Deteccao Automatica de Tendencias
Status: Planejado
Prioridade: P0 (Critica)

Arquitetura:
  ┌─────────────────────────────────────────────────────────┐
  │                    TREND HUNTER                         │
  ├─────────────────────────────────────────────────────────┤
  │                                                         │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
  │  │ Sound    │  │ Format   │  │ Topic    │  │ Hashtag │ │
  │  │ Detector │  │ Detector │  │ Detector │  │ Tracker │ │
  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
  │       │             │             │              │      │
  │       └─────────────┴─────────────┴──────────────┘      │
  │                          │                              │
  │                    ┌─────▼─────┐                        │
  │                    │  Trend    │                        │
  │                    │ Aggregator│                        │
  │                    └─────┬─────┘                        │
  │                          │                              │
  │                    ┌─────▼─────┐                        │
  │                    │  Alert    │                        │
  │                    │  Engine   │                        │
  │                    └───────────┘                        │
  │                                                         │
  └─────────────────────────────────────────────────────────┘

Detectores:
  Sound Detector:
    - Identifica audios/musicas em alta
    - Rastreia uso em multiplas plataformas
    - Detecta remixes e variacoes
    - Alerta quando som atinge threshold

  Format Detector:
    - Identifica novos formatos de video
    - Ex: "Get Ready With Me", "POV", "Tutorial rapido"
    - Detecta transicoes e efeitos trending
    - Mapeia estrutura de narrativa

  Topic Detector:
    - Analisa topicos em alta por nicho
    - Usa NLP para clustering semantico
    - Detecta eventos e noticias relevantes
    - Correlaciona com calendario (feriados, eventos)

  Hashtag Tracker:
    - Monitora hashtags emergentes
    - Detecta crescimento exponencial
    - Alerta antes da saturacao
    - Sugere timing ideal

Alertas:
  - Push notification (WhatsApp via SparkOne)
  - Email digest diario
  - Dashboard real-time
  - MCP tool para consulta

Metricas de Sucesso:
  - Detectar trend 24-48h antes do pico
  - 80% precision em predicoes
  - < 5 falsos positivos por semana
```

#### 4.2.2 Viral Score Preditivo

```yaml
Funcionalidade: Predicao de Viralidade
Status: Planejado
Prioridade: P1 (Alta)

Modelo ML:
  Features:
    - Metricas iniciais (views/hora, engagement rate)
    - Analise de hook (primeiros 3 segundos)
    - Padroes de audio (musica trending, voz)
    - Elementos visuais (cores, texto, movimento)
    - Timing (dia/hora de postagem)
    - Historico do criador

  Output:
    - Viral Score (0-100)
    - Confianca da predicao
    - Fatores contribuintes
    - Estimativa de alcance final

  Treinamento:
    - Dataset: 100k+ videos com outcomes conhecidos
    - Modelo: Gradient Boosting + Neural Network ensemble
    - Retreino: Semanal com novos dados
```

### 4.3 FASE 3: Personalizacao de Estilo (Prioridade Media)

#### 4.3.1 Style Cloner Agent

```yaml
Funcionalidade: Aprendizado de Estilo Pessoal
Status: Planejado
Prioridade: P1 (Alta)

Conceito:
  O Style Cloner analisa SEU conteudo anterior para criar
  um "DNA de estilo" unico que e aplicado a todo conteudo
  gerado pelo ViralForge.

Componentes:

  Style Analyzer:
    - Analisa seus ultimos 50 videos/posts
    - Extrai padroes de:
      - Tom de voz (formal, casual, humoristico)
      - Vocabulario (jargoes, expressoes, bordoes)
      - Ritmo de edicao (cortes por minuto, transicoes)
      - Paleta de cores preferida
      - Enquadramento tipico
      - Musicas/sons frequentes
      - CTAs usados

  Style Profile:
    {
      "voice": {
        "tone": "energetico-didatico",
        "vocabulary_level": "intermediario",
        "catchphrases": ["e isso ai", "bora la"],
        "avoid": ["termos tecnicos complexos"]
      },
      "visual": {
        "primary_colors": ["#FF6B35", "#004E89"],
        "framing": "close-up-70%",
        "text_style": "bold-sans-serif",
        "transitions": ["corte-seco", "zoom-rapido"]
      },
      "audio": {
        "music_genres": ["lo-fi", "upbeat-pop"],
        "voice_pace": "120-wpm",
        "sound_effects": ["whoosh", "ding"]
      },
      "structure": {
        "hook_duration": "2-3s",
        "avg_video_length": "45s",
        "cta_position": "final-5s"
      }
    }

  Style Enforcer:
    - Aplica Style Profile a todo conteudo gerado
    - Valida consistencia de marca
    - Sugere ajustes quando desvia do estilo

Metricas de Sucesso:
  - 90% dos usuarios reconhecem conteudo como "deles"
  - Reducao de edicao manual em 70%
```

#### 4.3.2 Brand Kit Integration

```yaml
Funcionalidade: Kit de Marca Integrado
Status: Planejado
Prioridade: P2 (Media)

Componentes:
  - Upload de logos (PNG, SVG)
  - Paleta de cores oficial
  - Fontes customizadas
  - Templates de intro/outro
  - Watermarks e overlays
  - Sons de marca (jingles, swooshes)

Aplicacao Automatica:
  - Intro padrao em todos os videos
  - Logo watermark posicionado
  - Cores da marca em textos/graficos
  - Musica de fundo do banco aprovado
```

### 4.4 FASE 4: Producao Avancada (Prioridade Media)

#### 4.4.1 Multi-Format Production

```yaml
Funcionalidade: Producao em Multiplos Formatos
Status: Planejado
Prioridade: P1 (Alta)

Formatos:
  Video Vertical (9:16):
    - Reels, TikTok, Shorts
    - Duracao: 15s, 30s, 60s, 90s

  Video Horizontal (16:9):
    - YouTube long-form
    - LinkedIn video

  Video Quadrado (1:1):
    - Feed Instagram
    - Facebook

  Carrossel:
    - 2-10 slides
    - Mix de imagem e video
    - Geracao automatica de slides

  Stories:
    - Sequencia de 15s
    - Stickers e CTAs
    - Swipe-up links

  Thumbnail:
    - Geracao automatica
    - A/B testing de variantes
    - Otimizacao com base em CTR

Adaptacao Automatica:
  - Um roteiro → multiplos formatos
  - Resize inteligente (sem cortar elementos)
  - Legendas reposicionadas por formato
```

#### 4.4.2 Voice Cloning

```yaml
Funcionalidade: Clonagem de Voz
Status: Planejado
Prioridade: P2 (Media)

Implementacao:
  - ElevenLabs Voice Cloning
  - Treinamento com 30min de audio do usuario
  - Modelo dedicado por usuario

Uso:
  - Narracao com SUA voz em videos gerados
  - Consistencia de marca
  - Escala de producao sem gravacao

Restricoes:
  - Apenas para voz do proprio usuario
  - Consentimento explicito
  - Marca d'agua de AI quando exigido
```

#### 4.4.3 AI Avatar

```yaml
Funcionalidade: Avatar IA para Videos
Status: Futuro
Prioridade: P3 (Baixa)

Conceito:
  - Avatar digital baseado na sua imagem
  - Lip-sync com audio gerado
  - Expressoes faciais naturais

Tecnologias:
  - HeyGen ou D-ID para avatar
  - Integracao com Voice Cloning

Casos de Uso:
  - Videos explicativos sem gravacao
  - Escala massiva de producao
  - Consistencia visual
```

### 4.5 FASE 5: Publicacao e Analytics (Prioridade Baixa)

#### 4.5.1 Content Scheduler Agent

```yaml
Funcionalidade: Agendamento Inteligente
Status: Planejado
Prioridade: P2 (Media)

Integracao:
  - Instagram (via Meta API)
  - TikTok (via TikTok API)
  - YouTube (via YouTube API)
  - Twitter/X (via Twitter API)
  - LinkedIn (via LinkedIn API)

Recursos:
  - Fila de conteudo
  - Horarios otimos por plataforma
  - Cross-posting automatico
  - Adaptacao de caption por plataforma
  - Preview antes de publicar
  - Aprovacao via WhatsApp (SparkOne)

Horarios Otimos:
  - ML baseado em historico de engagement
  - Ajuste por timezone do publico
  - Evita conflito com concorrentes
```

#### 4.5.2 Performance Tracker Agent

```yaml
Funcionalidade: Analytics Unificado
Status: Planejado
Prioridade: P2 (Media)

Metricas Rastreadas:
  - Views, Likes, Comments, Shares, Saves
  - Watch time e retention curve
  - Follower growth
  - Engagement rate
  - Reach e impressions
  - Click-through rate
  - Conversion rate (se aplicavel)

Insights:
  - Melhor horario de postagem
  - Formatos com melhor performance
  - Topicos mais engajadores
  - Comparativo com concorrentes
  - Predicao de tendencias

Relatorios:
  - Daily digest (WhatsApp)
  - Weekly report (Email + PDF)
  - Monthly review (Dashboard)
  - Custom reports (MCP tool)
```

#### 4.5.3 A/B Testing

```yaml
Funcionalidade: Testes A/B Automatizados
Status: Futuro
Prioridade: P3 (Baixa)

Elementos Testaveis:
  - Thumbnails (2-4 variantes)
  - Hooks (primeiros 3s)
  - CTAs (diferentes textos)
  - Horarios de postagem
  - Hashtags
  - Captions

Automacao:
  - Gera variantes automaticamente
  - Publica para segmentos diferentes
  - Mede performance por 24-48h
  - Promove vencedor automaticamente
  - Aprende para proximas postagens
```

---

## 5. Arquitetura Tecnica v3.0

### 5.1 Arquitetura de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           VIRALFORGE v3.0                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    INGESTION LAYER                               │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │   │
│  │  │Instagram │ │ TikTok   │ │ YouTube  │ │ Twitter  │ │ Outros │ │   │
│  │  │ Scraper  │ │ Scraper  │ │ Scraper  │ │ Scraper  │ │        │ │   │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ │   │
│  │       └────────────┴────────────┴────────────┴───────────┘      │   │
│  │                               │                                  │   │
│  └───────────────────────────────┼──────────────────────────────────┘   │
│                                  │                                      │
│  ┌───────────────────────────────┼──────────────────────────────────┐   │
│  │                    PROCESSING LAYER                              │   │
│  ├───────────────────────────────┼──────────────────────────────────┤   │
│  │                               ▼                                  │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │                    MEDIA PROCESSOR                        │   │   │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐  │   │   │
│  │  │  │Download │→ │Transcribe│→ │ Analyze │→ │Extract Meta │  │   │   │
│  │  │  │ (yt-dlp)│  │(Whisper) │  │(Gemini) │  │  (FFprobe)  │  │   │   │
│  │  │  └─────────┘  └─────────┘  └─────────┘  └─────────────┘  │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  │                               │                                  │   │
│  └───────────────────────────────┼──────────────────────────────────┘   │
│                                  │                                      │
│  ┌───────────────────────────────┼──────────────────────────────────┐   │
│  │                    INTELLIGENCE LAYER                            │   │
│  ├───────────────────────────────┼──────────────────────────────────┤   │
│  │                               ▼                                  │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │   │
│  │  │   TREND    │  │  ANALYST   │  │   STYLE    │  │ COMPETITOR │ │   │
│  │  │   HUNTER   │  │            │  │   CLONER   │  │   INTEL    │ │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘ │   │
│  │                               │                                  │   │
│  └───────────────────────────────┼──────────────────────────────────┘   │
│                                  │                                      │
│  ┌───────────────────────────────┼──────────────────────────────────┐   │
│  │                    PRODUCTION LAYER                              │   │
│  ├───────────────────────────────┼──────────────────────────────────┤   │
│  │                               ▼                                  │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │   │
│  │  │ STRATEGIST │→ │  PRODUCER  │→ │  RENDERER  │→ │  EXPORTER  │ │   │
│  │  │  (GPT-4)   │  │(Veo + TTS) │  │  (FFmpeg)  │  │  (Formats) │ │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘ │   │
│  │                               │                                  │   │
│  └───────────────────────────────┼──────────────────────────────────┘   │
│                                  │                                      │
│  ┌───────────────────────────────┼──────────────────────────────────┐   │
│  │                    DISTRIBUTION LAYER                            │   │
│  ├───────────────────────────────┼──────────────────────────────────┤   │
│  │                               ▼                                  │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │   │
│  │  │ SCHEDULER  │→ │ PUBLISHER  │→ │  TRACKER   │→ │  REPORTER  │ │   │
│  │  │            │  │            │  │            │  │            │ │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘ │   │
│  │                                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  DATA LAYER                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  PostgreSQL  │  │    Redis     │  │     S3       │                  │
│  │  (Metadata)  │  │   (Cache)    │  │   (Media)    │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
├─────────────────────────────────────────────────────────────────────────┤
│  INTERFACE LAYER                                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │  MCP Server  │  │   REST API   │  │  Dashboard   │  │  SparkOne   │ │
│  │  (Claude)    │  │   (FastAPI)  │  │   (React)    │  │ (WhatsApp)  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Stack Tecnologico - Arquitetura Hibrida

O ViralForge suporta **duas opcoes** para cada servico: Open Source (gratuito) ou API Paga (premium).

```yaml
Backend:
  Framework: FastAPI + Celery
  Database: PostgreSQL 16
  Cache: Redis
  Queue: Redis (Celery broker)
  Storage: MinIO (GRATIS, self-hosted) | S3 (pago)

AI/ML - ARQUITETURA HIBRIDA:
  #-----------------------------------------------------------------------
  # OPCAO OPEN SOURCE (GRATIS)         | OPCAO PAGA (PREMIUM)
  #-----------------------------------------------------------------------
  LLM Analysis: Groq (gratis c/limites) | Gemini 1.5 Pro, Claude 3.5
  LLM Generation: Groq                  | GPT-4o, Claude
  Transcription: Groq Whisper (GRATIS)  | Whisper local (requer GPU)
  Video Generation: Veo via FAL         | Veo via FAL
  TTS: edge-tts (GRATIS)                | ElevenLabs ($0.30/1k chars)
  Voice Cloning: XTTS-v2 (GRATIS)       | ElevenLabs ($22/mes)
  Talking Head: SadTalker (GRATIS)      | HeyGen ($48/mes)
  Thumbnails: Stable Diffusion (GRATIS) | FAL.ai ($0.02/img)
  ML Models: scikit-learn, PyTorch      | -

Scraping:
  Instagram: Apify ($2.30/1000) | Instaloader (GRATIS)
  TikTok: yt-dlp (GRATIS)
  YouTube: yt-dlp (GRATIS), YouTube Data API (GRATIS)
  Twitter: snscrape (GRATIS)
  General: gallery-dl (GRATIS), playwright

Video Processing:
  Download: yt-dlp (GRATIS)
  Processing: FFmpeg (GRATIS)
  Thumbnails: Pillow + FFmpeg (GRATIS)

Interfaces:
  MCP Server: FastMCP (stdio + SSE)
  REST API: FastAPI
  Dashboard: React + Vite
  Notifications: WhatsApp (via SparkOne)
```

### 5.2.1 Comparacao de Custos - Open Source vs Pago

| Componente | Open Source | API Paga | Economia |
|------------|-------------|----------|----------|
| TTS | edge-tts (GRATIS) | ElevenLabs ($0.30/1k) | 100% |
| Voice Clone | XTTS-v2 (GRATIS) | ElevenLabs ($22/mes) | 100% |
| Talking Head | SadTalker (GRATIS) | HeyGen ($48/mes) | 100% |
| Thumbnails | Stable Diffusion | FAL.ai ($0.02/img) | 100% |
| Transcricao | Groq Whisper | Whisper local | 100% |
| Storage | MinIO | S3 ($5-10/mes) | 100% |
| **TOTAL/mes** | **~$0** | **~$80+** | **99%** |

### 5.2.2 Integracao com MACS AI

O ViralForge compartilha ferramentas com o MACS AI (persona digital):

```
ViralForge (Analise)              MACS AI (Producao)
─────────────────────             ──────────────────
src/tools/tts_tools.py      ───►  Reutilizado
src/tools/storage_tools.py  ───►  Reutilizado
src/tools/ffmpeg_tools.py   ───►  Reutilizado
src/tools/whisper_tools.py  ───►  Reutilizado

Padroes Virais Detectados   ───►  Replica com Persona Digital
```

### 5.3 Database Schema v3

```sql
-- Novos schemas para v3.0

-- Trend Detection
CREATE TABLE trends (
    id UUID PRIMARY KEY,
    trend_type VARCHAR(50), -- 'sound', 'format', 'topic', 'hashtag'
    identifier VARCHAR(255), -- sound_id, format_name, topic, hashtag
    platform VARCHAR(50),
    first_detected_at TIMESTAMP,
    peak_detected_at TIMESTAMP,
    current_score FLOAT,
    growth_rate FLOAT,
    prediction_confidence FLOAT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Style Profiles
CREATE TABLE style_profiles (
    id UUID PRIMARY KEY,
    user_id UUID,
    name VARCHAR(100),
    voice_config JSONB,
    visual_config JSONB,
    audio_config JSONB,
    structure_config JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Content Queue
CREATE TABLE content_queue (
    id UUID PRIMARY KEY,
    content_type VARCHAR(50), -- 'video', 'carousel', 'story'
    file_paths JSONB,
    platforms JSONB, -- ['instagram', 'tiktok', 'youtube']
    scheduled_at TIMESTAMP,
    published_at TIMESTAMP,
    status VARCHAR(50), -- 'draft', 'scheduled', 'publishing', 'published', 'failed'
    captions JSONB, -- caption by platform
    hashtags JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Performance Metrics
CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY,
    content_id UUID REFERENCES content_queue(id),
    platform VARCHAR(50),
    metric_type VARCHAR(50), -- 'views', 'likes', 'comments', etc.
    value BIGINT,
    measured_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- A/B Tests
CREATE TABLE ab_tests (
    id UUID PRIMARY KEY,
    name VARCHAR(200),
    test_type VARCHAR(50), -- 'thumbnail', 'hook', 'cta', etc.
    variants JSONB,
    winner_variant_id VARCHAR(50),
    status VARCHAR(50), -- 'running', 'completed', 'cancelled'
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    results JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Competitor Analysis
CREATE TABLE competitors (
    id UUID PRIMARY KEY,
    platform VARCHAR(50),
    username VARCHAR(100),
    display_name VARCHAR(200),
    follower_count BIGINT,
    avg_engagement_rate FLOAT,
    posting_frequency FLOAT, -- posts per day
    top_content_types JSONB,
    notes TEXT,
    is_active BOOLEAN DEFAULT true,
    last_scraped_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_trends_type_platform ON trends(trend_type, platform);
CREATE INDEX idx_trends_score ON trends(current_score DESC);
CREATE INDEX idx_content_queue_scheduled ON content_queue(scheduled_at) WHERE status = 'scheduled';
CREATE INDEX idx_performance_content ON performance_metrics(content_id, platform);
CREATE INDEX idx_competitors_platform ON competitors(platform, is_active);
```

---

## 6. MCP Tools v3.0

### 6.1 Tools Existentes (Mantidas)

```yaml
Scraping:
  - scrape_profile: Coleta videos de perfil Instagram
  - download_video: Baixa video especifico
  - list_videos: Lista videos coletados

Analysis:
  - analyze_video: Analise com Gemini/Claude
  - transcribe_video: Transcricao com Whisper/Groq
  - get_semantic_analysis: Analise semantica completa
  - full_pipeline: Pipeline completo

Strategy:
  - generate_strategy: Gera estrategia de replicacao
  - list_strategies: Lista estrategias

Production:
  - produce_video: Produz video final
  - get_budget_status: Status do orcamento
```

### 6.2 Novas Tools (v3.0)

```yaml
Multi-Platform:
  - scrape_tiktok_profile: Coleta videos TikTok
  - scrape_youtube_shorts: Coleta YouTube Shorts
  - scrape_instagram_stories: Captura Stories
  - scrape_instagram_carousels: Coleta Carrosseis
  - download_multi_platform: Download universal

Trend Detection:
  - get_trending_sounds: Sons em alta
  - get_trending_formats: Formatos em alta
  - get_trending_topics: Topicos por nicho
  - get_trending_hashtags: Hashtags emergentes
  - predict_virality: Predicao de viralidade

Style:
  - analyze_my_style: Analisa seu estilo
  - get_style_profile: Retorna perfil de estilo
  - apply_style: Aplica estilo a conteudo
  - update_brand_kit: Atualiza kit de marca

Production:
  - generate_carousel: Gera carrossel
  - generate_story_sequence: Gera sequencia de stories
  - generate_thumbnail_variants: Gera thumbnails A/B
  - render_multi_format: Renderiza multiplos formatos

Scheduling:
  - schedule_content: Agenda publicacao
  - get_optimal_times: Melhores horarios
  - list_scheduled: Lista agendados
  - publish_now: Publica imediatamente

Analytics:
  - get_performance_report: Relatorio de performance
  - compare_with_competitors: Benchmarking
  - get_insights: Insights acionaveis
  - export_report: Exporta relatorio PDF

Competitor:
  - add_competitor: Adiciona concorrente
  - analyze_competitor: Analise profunda
  - get_competitor_trends: Tendencias do concorrente
  - compare_competitors: Comparativo
```

---

## 7. Integracao com SparkOne

### 7.1 Fluxo de Comunicacao

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     SPARKONE ←→ VIRALFORGE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  SparkOne (WhatsApp)                    ViralForge                      │
│  ┌──────────────────┐                  ┌──────────────────┐            │
│  │                  │                  │                  │            │
│  │  "Quais trends   │ ──── MCP ────►  │  Trend Hunter    │            │
│  │   estao em alta?"│                  │  Agent           │            │
│  │                  │ ◄──── JSON ────  │                  │            │
│  │  [Resposta com   │                  │  - 3 sons        │            │
│  │   lista de trends]                  │  - 2 formatos    │            │
│  │                  │                  │  - 5 hashtags    │            │
│  └──────────────────┘                  └──────────────────┘            │
│                                                                         │
│  ┌──────────────────┐                  ┌──────────────────┐            │
│  │                  │                  │                  │            │
│  │  "Cria roteiro   │ ──── MCP ────►  │  Strategist +    │            │
│  │   baseado nesse  │                  │  Style Cloner    │            │
│  │   trend"         │ ◄──── JSON ────  │                  │            │
│  │                  │                  │  - Roteiro       │            │
│  │  [Roteiro pronto │                  │  - No seu estilo │            │
│  │   no seu estilo] │                  │  - CTAs          │            │
│  └──────────────────┘                  └──────────────────┘            │
│                                                                         │
│  ┌──────────────────┐                  ┌──────────────────┐            │
│  │                  │                  │                  │            │
│  │  "Produz video   │ ──── MCP ────►  │  Producer +      │            │
│  │   com esse       │                  │  Renderer        │            │
│  │   roteiro"       │ ◄──── File ────  │                  │            │
│  │                  │                  │  - Video MP4     │            │
│  │  [Video pronto   │                  │  - Thumbnail     │            │
│  │   para download] │                  │  - Caption       │            │
│  └──────────────────┘                  └──────────────────┘            │
│                                                                         │
│  ┌──────────────────┐                  ┌──────────────────┐            │
│  │                  │                  │                  │            │
│  │  "Agenda para    │ ──── MCP ────►  │  Scheduler       │            │
│  │   amanha 10h"    │                  │                  │            │
│  │                  │ ◄──── OK ──────  │  - Agendado      │            │
│  │  [Confirmacao]   │                  │  - Notificacao   │            │
│  │                  │                  │    pre-post      │            │
│  └──────────────────┘                  └──────────────────┘            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Comandos WhatsApp (via SparkOne)

```
/viral trends          → Lista tendencias em alta
/viral trends tiktok   → Tendencias especificas TikTok
/viral analisar [url]  → Analisa video especifico
/viral roteiro [tema]  → Gera roteiro sobre tema
/viral produzir        → Produz ultimo roteiro
/viral agendar         → Agenda ultimo video
/viral status          → Status de producao
/viral relatorio       → Relatorio de performance
```

---

## 8. Roadmap de Implementacao

### 8.1 Timeline

```
Q1 2025 (Jan-Mar)
├── FASE 1: Multi-Plataforma
│   ├── Semana 1-2: TikTok Scraper
│   ├── Semana 3-4: YouTube Shorts Scraper
│   ├── Semana 5-6: Instagram Stories + Carrosseis
│   └── Semana 7-8: Testes e estabilizacao

Q2 2025 (Abr-Jun)
├── FASE 2: Trend Detection
│   ├── Semana 1-4: Trend Hunter Agent
│   ├── Semana 5-8: Viral Score Preditivo (ML)
│   └── Semana 9-12: Alertas e Dashboard

Q3 2025 (Jul-Set)
├── FASE 3: Personalizacao
│   ├── Semana 1-4: Style Cloner Agent
│   ├── Semana 5-8: Brand Kit Integration
│   └── Semana 9-12: Voice Cloning

Q4 2025 (Out-Dez)
├── FASE 4-5: Producao + Distribuicao
│   ├── Semana 1-4: Multi-Format Production
│   ├── Semana 5-8: Content Scheduler
│   ├── Semana 9-10: Performance Tracker
│   └── Semana 11-12: A/B Testing
```

### 8.2 Marcos (Milestones)

| Marco | Data | Entregaveis |
|-------|------|-------------|
| M1: Multi-Platform | Mar 2025 | TikTok + YouTube + Stories + Carrosseis |
| M2: Trend Detection | Jun 2025 | Trend Hunter + Viral Score + Alertas |
| M3: Personalization | Set 2025 | Style Cloner + Brand Kit + Voice Clone |
| M4: Full Automation | Dez 2025 | Scheduler + Tracker + A/B Testing |

---

## 9. Metricas de Sucesso

### 9.1 KPIs do Produto

| Metrica | Meta | Medicao |
|---------|------|---------|
| Videos analisados/dia | 100+ | Dashboard |
| Precisao de trends | 80%+ | A/B retroativo |
| Tempo de producao | < 5min | Logs |
| Consistencia de estilo | 90%+ | User survey |
| Engagement uplift | +30% | Analytics |

### 9.2 KPIs Tecnicos

| Metrica | Meta | Medicao |
|---------|------|---------|
| Uptime | 99.9% | Monitoring |
| Latencia MCP | < 500ms | Prometheus |
| Taxa de erro | < 1% | Logs |
| Custo por video | < $0.50 | Budget tracking |

---

## 10. Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|--------------|---------|-----------|
| Rate limiting APIs | Alta | Medio | Multiplas contas, delays, cache |
| Mudancas em APIs | Media | Alto | Abstracoes, fallbacks, monitoring |
| Custo de IA | Media | Medio | Budget limits, modelos menores |
| Qualidade de output | Media | Alto | Validacao humana, feedback loop |
| Compliance (ToS) | Media | Alto | Uso pessoal, rate limits, disclaimers |

---

## 11. Consideracoes de Compliance

### 11.1 Termos de Servico

- Uso para pesquisa e inspiracao pessoal
- Nao republica conteudo de terceiros sem credito
- Respeita rate limits das plataformas
- Nao viola copyright de audios/musicas

### 11.2 Privacidade

- Dados de criadores sao publicos
- Nao coleta dados pessoais
- Storage criptografado
- Retencao limitada (90 dias)

### 11.3 IA Generativa

- Disclosures de conteudo gerado por IA
- Voice cloning apenas com consentimento
- Watermarks quando exigido

---

## 12. Conclusao

O ViralForge v3.0 representa uma evolucao significativa de uma ferramenta de analise para uma plataforma completa de inteligencia competitiva e producao de conteudo. As principais inovacoes sao:

1. **Multi-Plataforma**: Cobertura completa de TikTok, YouTube, Instagram, Twitter
2. **Trend Detection**: Antecipacao de tendencias antes do pico
3. **Personalizacao**: Conteudo gerado no SEU estilo unico
4. **Automacao End-to-End**: Da inspiracao a publicacao em minutos
5. **Integracao Profunda**: Controle total via WhatsApp (SparkOne) ou Claude

O objetivo final e transformar o ViralForge no co-piloto definitivo para criadores de conteudo, economizando horas de trabalho manual e maximizando o impacto de cada publicacao.

---

**Documento:** PRD-VIRALFORGE-V3.md
**Versao:** 1.0
**Autor:** Marco Cardoso
**Data:** Dezembro 2024
**Status:** Draft para Revisao
