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
