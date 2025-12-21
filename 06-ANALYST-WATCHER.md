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
