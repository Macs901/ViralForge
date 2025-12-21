"""Tools para Text-to-Speech usando edge-tts e ElevenLabs."""

import asyncio
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Union

import edge_tts
from elevenlabs import ElevenLabs
from pydub import AudioSegment

from config.settings import get_settings

settings = get_settings()


@dataclass
class TTSResult:
    """Resultado de geracao TTS."""

    file_path: Path
    duration_seconds: float
    provider: str
    characters: int
    cost_usd: float


class TTSTools:
    """Gerenciador de Text-to-Speech com edge-tts (gratuito) e ElevenLabs (fallback)."""

    def __init__(self):
        """Inicializa TTS tools."""
        self.elevenlabs_client: Optional[ElevenLabs] = None
        if settings.elevenlabs_api_key:
            self.elevenlabs_client = ElevenLabs(api_key=settings.elevenlabs_api_key)

    async def generate_tts(
        self,
        text: str,
        output_path: Union[str, Path],
        provider: Optional[Literal["edge-tts", "elevenlabs"]] = None,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
    ) -> TTSResult:
        """Gera audio TTS usando provider configurado.

        Args:
            text: Texto para converter em audio
            output_path: Caminho de saida do arquivo MP3
            provider: Provider a usar (default: settings.tts_provider)
            voice: Voz especifica (default: settings.tts_voice_pt_br)
            rate: Taxa de fala (default: settings.tts_rate)
            pitch: Tom da voz (default: settings.tts_pitch)

        Returns:
            TTSResult com informacoes do audio gerado
        """
        provider = provider or settings.tts_provider
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if provider == "edge-tts":
                return await self._generate_edge_tts(text, output_path, voice, rate, pitch)
            elif provider == "elevenlabs":
                return await self._generate_elevenlabs(text, output_path, voice)
            else:
                raise ValueError(f"Provider desconhecido: {provider}")
        except Exception as e:
            # Fallback para outro provider
            fallback = settings.tts_fallback_provider
            if fallback and fallback != provider:
                print(f"[TTS] Erro com {provider}, usando fallback {fallback}: {e}")
                if fallback == "edge-tts":
                    return await self._generate_edge_tts(text, output_path, voice, rate, pitch)
                else:
                    return await self._generate_elevenlabs(text, output_path, voice)
            raise

    async def _generate_edge_tts(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
    ) -> TTSResult:
        """Gera audio usando edge-tts (Microsoft, gratuito).

        Args:
            text: Texto para converter
            output_path: Caminho de saida
            voice: Voz (default: pt-BR-FranciscaNeural)
            rate: Taxa de fala (default: +0%)
            pitch: Tom (default: +0Hz)

        Returns:
            TTSResult
        """
        voice = voice or settings.tts_voice_pt_br
        rate = rate or settings.tts_rate
        pitch = pitch or settings.tts_pitch

        # Cria comunicator edge-tts
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            pitch=pitch,
        )

        # Gera audio
        await communicate.save(str(output_path))

        # Calcula duracao
        duration = self._get_audio_duration(output_path)

        return TTSResult(
            file_path=output_path,
            duration_seconds=duration,
            provider="edge-tts",
            characters=len(text),
            cost_usd=0.0,  # edge-tts e gratuito
        )

    async def _generate_elevenlabs(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None,
    ) -> TTSResult:
        """Gera audio usando ElevenLabs (premium).

        Args:
            text: Texto para converter
            output_path: Caminho de saida
            voice: Voice ID (default: settings.elevenlabs_voice_id)

        Returns:
            TTSResult
        """
        if not self.elevenlabs_client:
            raise RuntimeError("ElevenLabs API key nao configurada")

        voice = voice or settings.elevenlabs_voice_id

        # Gera audio (sincrono, rodamos em thread)
        audio = await asyncio.to_thread(
            self.elevenlabs_client.text_to_speech.convert,
            voice_id=voice,
            text=text,
            model_id="eleven_multilingual_v2",
        )

        # Salva audio
        with open(output_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)

        # Calcula duracao e custo
        duration = self._get_audio_duration(output_path)
        cost = self._calculate_elevenlabs_cost(len(text))

        return TTSResult(
            file_path=output_path,
            duration_seconds=duration,
            provider="elevenlabs",
            characters=len(text),
            cost_usd=cost,
        )

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Retorna duracao do audio em segundos."""
        try:
            audio = AudioSegment.from_file(str(audio_path))
            return len(audio) / 1000.0
        except Exception:
            return 0.0

    def _calculate_elevenlabs_cost(self, characters: int) -> float:
        """Calcula custo do ElevenLabs ($0.30/1000 chars)."""
        return float(settings.cost_elevenlabs_per_1k_chars * characters / 1000)

    # === Metodos de conveniencia ===

    async def generate_narration(
        self,
        script: str,
        output_dir: Union[str, Path],
        strategy_id: int,
    ) -> TTSResult:
        """Gera narracao completa para uma estrategia.

        Args:
            script: Roteiro completo para narrar
            output_dir: Diretorio de saida
            strategy_id: ID da estrategia

        Returns:
            TTSResult
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"narration_{strategy_id}.mp3"

        return await self.generate_tts(
            text=script,
            output_path=output_path,
        )

    async def generate_segments(
        self,
        segments: list[dict],
        output_dir: Union[str, Path],
        strategy_id: int,
    ) -> list[TTSResult]:
        """Gera multiplos segmentos de audio (hook, development, cta).

        Args:
            segments: Lista de dicts com 'name' e 'text'
            output_dir: Diretorio de saida
            strategy_id: ID da estrategia

        Returns:
            Lista de TTSResult
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        for segment in segments:
            name = segment.get("name", "segment")
            text = segment.get("text", "")

            if not text.strip():
                continue

            output_path = output_dir / f"{name}_{strategy_id}.mp3"
            result = await self.generate_tts(
                text=text,
                output_path=output_path,
            )
            results.append(result)

        return results

    @staticmethod
    async def list_edge_voices(language_filter: Optional[str] = "pt-BR") -> list[dict]:
        """Lista vozes disponiveis no edge-tts.

        Args:
            language_filter: Filtro de idioma (ex: 'pt-BR', 'en-US')

        Returns:
            Lista de vozes com name, gender, locale
        """
        voices = await edge_tts.list_voices()

        if language_filter:
            voices = [v for v in voices if language_filter in v.get("Locale", "")]

        return [
            {
                "name": v.get("ShortName"),
                "gender": v.get("Gender"),
                "locale": v.get("Locale"),
            }
            for v in voices
        ]

    def estimate_cost(self, text: str, provider: Optional[str] = None) -> float:
        """Estima custo de geracao TTS.

        Args:
            text: Texto a ser convertido
            provider: Provider (default: settings.tts_provider)

        Returns:
            Custo estimado em USD
        """
        provider = provider or settings.tts_provider

        if provider == "edge-tts":
            return 0.0
        elif provider == "elevenlabs":
            return self._calculate_elevenlabs_cost(len(text))
        else:
            return 0.0


# Singleton para uso global
tts_tools = TTSTools()


# Funcao auxiliar para uso sincrono
def generate_tts_sync(
    text: str,
    output_path: Union[str, Path],
    **kwargs,
) -> TTSResult:
    """Versao sincrona do generate_tts."""
    return asyncio.run(tts_tools.generate_tts(text, output_path, **kwargs))
