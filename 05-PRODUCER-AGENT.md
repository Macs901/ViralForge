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
