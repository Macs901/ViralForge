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
