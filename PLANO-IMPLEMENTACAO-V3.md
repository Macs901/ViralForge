# ViralForge v3.0 - Plano de Implementacao Completo

## Status Atual

### Implementado
| Componente | Status | Arquivos |
|------------|--------|----------|
| TikTok Scraper | ✅ | `src/tools/tiktok_scraper.py` |
| YouTube Scraper | ✅ | `src/tools/youtube_scraper.py` |
| Instagram Scraper (expandido) | ✅ | `src/tools/instagram_scraper.py` |
| Trend Hunter Agent | ✅ | `src/agents/trend_hunter_agent.py` |
| Content Scheduler Agent | ✅ | `src/agents/scheduler_agent.py` |
| 48 MCP Tools | ✅ | `src/mcp/server.py` |
| 28 Database Models | ✅ | `src/db/models/` |

### Pendente
| Componente | Prioridade | Esforco |
|------------|------------|---------|
| Database Migrations | P0 | 1h |
| Style Cloner Agent | P1 | 4h |
| Performance Tracker Agent | P1 | 3h |
| Competitor Intel Agent | P2 | 3h |
| Publishing Integration | P1 | 4h |
| Twitter/X Scraper | P2 | 2h |
| Viral Score ML | P3 | 6h |
| A/B Testing | P3 | 4h |
| Dashboard React | P3 | 8h |

---

## Fases de Implementacao

### FASE 1: Database & Infraestrutura (1-2 horas)

#### 1.1 Criar Migrations Alembic
```bash
# Gerar migrations para novos models
alembic revision --autogenerate -m "Add trends, scheduling, and instagram models"
alembic upgrade head
```

**Models a migrar:**
- `src/db/models/trends.py` - Trend, TrendSound, TrendFormat, TrendTopic
- `src/db/models/instagram.py` - InstagramStory, InstagramCarousel, InstagramComment
- Tabelas de scheduling (content_queue, etc.)

#### 1.2 Verificar Conexoes
- [ ] Testar conexao PostgreSQL
- [ ] Testar conexao Redis
- [ ] Testar conexao MinIO/S3

---

### FASE 2: Style Cloner Agent (4 horas)

#### 2.1 Estrutura
```
src/agents/style_cloner_agent.py
src/db/models/style_profile.py
src/tools/style_tools.py
```

#### 2.2 Funcionalidades
| Feature | Descricao |
|---------|-----------|
| `analyze_my_style()` | Analisa ultimos 50 videos do usuario |
| `create_style_profile()` | Cria perfil de estilo (tom, visual, audio) |
| `apply_style()` | Aplica estilo a roteiros gerados |
| `update_brand_kit()` | Atualiza cores, fontes, logos |

#### 2.3 Style Profile Schema
```python
StyleProfile:
  voice:
    tone: str  # "energetico", "calmo", "didatico"
    vocabulary_level: str  # "simples", "tecnico"
    catchphrases: list[str]
    avoid: list[str]

  visual:
    primary_colors: list[str]
    framing: str
    text_style: str
    transitions: list[str]

  audio:
    music_genres: list[str]
    voice_pace: int  # WPM
    sound_effects: list[str]

  structure:
    hook_duration: str
    avg_video_length: str
    cta_position: str
```

#### 2.4 MCP Tools
- `analyze_my_style` - Analisa estilo do usuario
- `get_style_profile` - Retorna perfil ativo
- `apply_style_to_script` - Aplica estilo a roteiro
- `update_brand_colors` - Atualiza paleta

---

### FASE 3: Performance Tracker Agent (3 horas)

#### 3.1 Estrutura
```
src/agents/performance_tracker_agent.py
src/db/models/performance.py
src/tools/analytics_tools.py
```

#### 3.2 Funcionalidades
| Feature | Descricao |
|---------|-----------|
| `collect_metrics()` | Coleta metricas de plataformas |
| `generate_report()` | Gera relatorio de performance |
| `get_insights()` | Insights acionaveis |
| `compare_periods()` | Compara periodos |

#### 3.3 Metricas Rastreadas
- Views, Likes, Comments, Shares, Saves
- Engagement rate
- Watch time / Retention
- Follower growth
- Reach / Impressions

#### 3.4 MCP Tools
- `get_performance_report` - Relatorio completo
- `get_content_metrics` - Metricas por conteudo
- `get_platform_insights` - Insights por plataforma
- `export_report_pdf` - Exporta PDF

---

### FASE 4: Competitor Intel Agent (3 horas)

#### 4.1 Estrutura
```
src/agents/competitor_intel_agent.py
src/db/models/competitor.py
src/tools/competitor_tools.py
```

#### 4.2 Funcionalidades
| Feature | Descricao |
|---------|-----------|
| `add_competitor()` | Adiciona concorrente para monitorar |
| `analyze_competitor()` | Analise profunda |
| `get_competitor_trends()` | Tendencias do concorrente |
| `benchmark()` | Comparativo com voce |

#### 4.3 Dados Coletados
- Frequencia de postagem
- Horarios de publicacao
- Formatos mais usados
- Engagement medio
- Crescimento de seguidores
- Hashtags frequentes
- Sons/musicas usadas

#### 4.4 MCP Tools
- `add_competitor` - Adiciona concorrente
- `list_competitors` - Lista monitorados
- `analyze_competitor` - Analise profunda
- `compare_with_competitors` - Benchmarking

---

### FASE 5: Publishing Integration (4 horas)

#### 5.1 Estrutura
```
src/services/publishers/
├── __init__.py
├── base.py
├── instagram_publisher.py
├── tiktok_publisher.py
├── youtube_publisher.py
└── linkedin_publisher.py
```

#### 5.2 Instagram Publishing (Meta Graph API)
```python
# Requer Instagram Business Account + Facebook Page
# Endpoints:
# POST /me/media - Cria container
# POST /me/media_publish - Publica

Funcionalidades:
- Publicar Reels
- Publicar Carrosséis
- Publicar Stories (limitado)
- Agendar (via container)
```

#### 5.3 TikTok Publishing (Content Posting API)
```python
# Requer TikTok Developer Account
# Endpoints:
# POST /v2/post/publish/video/init
# POST /v2/post/publish/video/upload

Funcionalidades:
- Publicar videos
- Adicionar caption/hashtags
- Adicionar musica (limitado)
```

#### 5.4 YouTube Publishing (Data API v3)
```python
# Requer Google Cloud Project + OAuth
# Endpoints:
# POST /youtube/v3/videos

Funcionalidades:
- Upload de Shorts
- Definir titulo, descricao, tags
- Definir thumbnail
- Agendar publicacao
```

#### 5.5 MCP Tools Atualizadas
- `publish_to_instagram` - Publica no Instagram
- `publish_to_tiktok` - Publica no TikTok
- `publish_to_youtube` - Publica no YouTube
- `publish_to_all` - Publica em todas

---

### FASE 6: Twitter/X Scraper (2 horas)

#### 6.1 Estrutura
```
src/tools/twitter_scraper.py
src/db/models/twitter.py
```

#### 6.2 Funcionalidades
| Feature | Descricao |
|---------|-----------|
| `scrape_twitter_profile()` | Perfil e tweets recentes |
| `scrape_twitter_videos()` | Videos do perfil |
| `scrape_trending_tweets()` | Tweets virais |
| `search_twitter()` | Busca por termo |

#### 6.3 Implementacao
- Usar `snscrape` (gratuito, sem API)
- Fallback para `nitter` instances
- Rate limiting respeitoso

---

### FASE 7: Viral Score ML (6 horas) - OPCIONAL

#### 7.1 Estrutura
```
src/ml/
├── __init__.py
├── viral_predictor.py
├── feature_extractor.py
└── models/
    └── viral_score_model.pkl
```

#### 7.2 Features
- Hook quality (primeiros 3s)
- Audio trending score
- Visual elements
- Posting time
- Creator history
- Engagement velocity

#### 7.3 Modelo
- Gradient Boosting + Neural Network ensemble
- Treinado com 10k+ videos
- Output: Viral Score (0-100)

---

### FASE 8: A/B Testing (4 horas) - OPCIONAL

#### 8.1 Estrutura
```
src/services/ab_testing.py
src/db/models/ab_test.py
```

#### 8.2 Elementos Testaveis
- Thumbnails (2-4 variantes)
- Hooks (primeiros 3s)
- CTAs
- Horarios
- Hashtags

---

### FASE 9: Dashboard React (8 horas) - OPCIONAL

#### 9.1 Estrutura
```
frontend/
├── src/
│   ├── components/
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Trends.tsx
│   │   ├── Competitors.tsx
│   │   ├── Analytics.tsx
│   │   └── Settings.tsx
│   └── services/
└── package.json
```

---

## Ordem de Execucao Recomendada

```
PRIORIDADE ALTA (Hoje):
├── [1] Database Migrations (1h)
├── [2] Style Cloner Agent (4h)
└── [3] Performance Tracker Agent (3h)

PRIORIDADE MEDIA (Proximo):
├── [4] Competitor Intel Agent (3h)
├── [5] Publishing Integration (4h)
└── [6] Twitter/X Scraper (2h)

PRIORIDADE BAIXA (Futuro):
├── [7] Viral Score ML (6h)
├── [8] A/B Testing (4h)
└── [9] Dashboard React (8h)
```

---

## Estimativa Total

| Prioridade | Componentes | Tempo |
|------------|-------------|-------|
| Alta | Migrations + Style + Performance | 8h |
| Media | Competitor + Publishing + Twitter | 9h |
| Baixa | ML + A/B + Dashboard | 18h |
| **TOTAL** | **9 componentes** | **35h** |

---

## Proximos Passos Imediatos

1. **Rodar migrations** para criar tabelas novas
2. **Implementar Style Cloner** para personalizacao
3. **Implementar Performance Tracker** para analytics
4. **Testar sistema completo**

---

*Plano criado em: 2024-12-28*
*Autor: Claude Code*
