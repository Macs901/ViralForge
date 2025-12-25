"""Tools para transcricao de audio usando Whisper local ou Groq API."""

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Union

from pydub import AudioSegment

from config.settings import get_settings

settings = get_settings()


def _import_whisper():
    """Import whisper lazily to avoid loading when using Groq."""
    import whisper
    return whisper


def _import_groq():
    """Import groq lazily."""
    from groq import Groq
    return Groq


@dataclass
class TranscriptionResult:
    """Resultado de transcricao."""

    text: str
    language: str
    confidence: float
    duration_seconds: float
    segments: list[dict]


class GroqWhisperTools:
    """Gerenciador de transcricao usando Groq Whisper API (gratis e mais rapido)."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Inicializa cliente Groq.

        Args:
            api_key: Groq API key
            model: Modelo Whisper (whisper-large-v3 ou whisper-large-v3-turbo)
        """
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_whisper_model
        self._client = None

    @property
    def client(self):
        """Lazy loading do cliente Groq."""
        if self._client is None:
            if not self.api_key:
                raise RuntimeError("GROQ_API_KEY nao configurado")
            Groq = _import_groq()
            self._client = Groq(api_key=self.api_key)
            print(f"[Groq Whisper] Cliente inicializado com modelo '{self.model}'")
        return self._client

    def transcribe(
        self,
        audio_path: Union[str, Path],
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcreve audio usando Groq Whisper API.

        Args:
            audio_path: Caminho do arquivo de audio
            language: Idioma do audio (ex: "pt", "en")

        Returns:
            TranscriptionResult com texto e metadados
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio nao encontrado: {audio_path}")

        # Groq aceita mp3, mp4, m4a, wav, webm - converte se necessario
        supported_formats = [".mp3", ".mp4", ".m4a", ".wav", ".webm", ".ogg"]
        if audio_path.suffix.lower() not in supported_formats:
            audio_path = self._convert_to_mp3(audio_path)

        # Transcreve com Groq
        with open(audio_path, "rb") as f:
            transcription = self.client.audio.transcriptions.create(
                file=(audio_path.name, f.read()),
                model=self.model,
                language=language or "pt",
                response_format="verbose_json",  # Inclui timestamps
            )

        # Extrai segmentos se disponiveis
        segments = []
        if hasattr(transcription, "segments") and transcription.segments:
            segments = [
                {
                    "start": seg.get("start", 0),
                    "end": seg.get("end", 0),
                    "text": seg.get("text", "").strip(),
                }
                for seg in transcription.segments
            ]

        # Calcula duracao
        duration = self._get_audio_duration(audio_path)

        return TranscriptionResult(
            text=transcription.text.strip() if hasattr(transcription, "text") else str(transcription),
            language=language or "pt",
            confidence=0.95,  # Groq nao retorna confianca, assume alta
            duration_seconds=duration,
            segments=segments,
        )

    def transcribe_video(
        self,
        video_path: Union[str, Path],
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Extrai audio de video e transcreve com Groq.

        Args:
            video_path: Caminho do arquivo de video
            language: Idioma do audio

        Returns:
            TranscriptionResult
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video nao encontrado: {video_path}")

        # Extrai audio para arquivo temporario
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            self._extract_audio_from_video(video_path, tmp_path)
            return self.transcribe(tmp_path, language=language)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def _convert_to_mp3(self, audio_path: Path) -> Path:
        """Converte audio para MP3."""
        output_path = audio_path.with_suffix(".mp3")
        audio = AudioSegment.from_file(str(audio_path))
        audio.export(str(output_path), format="mp3")
        return output_path

    def _extract_audio_from_video(self, video_path: Path, output_path: Path) -> None:
        """Extrai audio de video usando ffmpeg."""
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",
            "-acodec", "libmp3lame",
            "-ar", "16000",
            "-ac", "1",
            "-y",
            str(output_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True)

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Retorna duracao do audio em segundos."""
        try:
            audio = AudioSegment.from_file(str(audio_path))
            return len(audio) / 1000.0
        except Exception:
            return 0.0


class LocalWhisperTools:
    """Gerenciador de transcricao usando Whisper local."""

    def __init__(self, model_name: Optional[str] = None):
        """Inicializa Whisper.

        Args:
            model_name: Nome do modelo (tiny, base, small, medium, large, large-v2, large-v3)
        """
        self.model_name = model_name or settings.whisper_model
        self._model = None

    @property
    def model(self):
        """Lazy loading do modelo Whisper."""
        if self._model is None:
            whisper = _import_whisper()
            print(f"[Whisper Local] Carregando modelo '{self.model_name}'...")
            self._model = whisper.load_model(self.model_name)
            print(f"[Whisper Local] Modelo carregado!")
        return self._model

    def transcribe(
        self,
        audio_path: Union[str, Path],
        language: Optional[str] = None,
        task: str = "transcribe",
    ) -> TranscriptionResult:
        """Transcreve audio usando Whisper local.

        Args:
            audio_path: Caminho do arquivo de audio
            language: Idioma do audio (None = auto-detect)
            task: 'transcribe' ou 'translate' (para ingles)

        Returns:
            TranscriptionResult com texto e metadados
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio nao encontrado: {audio_path}")

        # Converte para WAV se necessario (Whisper prefere WAV)
        if audio_path.suffix.lower() not in [".wav", ".mp3", ".m4a", ".flac"]:
            audio_path = self._convert_to_wav(audio_path)

        # Opcoes de transcricao
        options = {
            "task": task,
            "verbose": False,
        }
        if language:
            options["language"] = language

        # Transcreve
        result = self.model.transcribe(str(audio_path), **options)

        # Calcula confianca media dos segmentos
        segments = result.get("segments", [])
        if segments:
            avg_confidence = sum(
                seg.get("no_speech_prob", 0) for seg in segments
            ) / len(segments)
            confidence = 1.0 - avg_confidence
        else:
            confidence = 0.5

        # Calcula duracao
        duration = self._get_audio_duration(audio_path)

        return TranscriptionResult(
            text=result.get("text", "").strip(),
            language=result.get("language", "unknown"),
            confidence=round(confidence, 2),
            duration_seconds=duration,
            segments=[
                {
                    "start": seg.get("start", 0),
                    "end": seg.get("end", 0),
                    "text": seg.get("text", "").strip(),
                }
                for seg in segments
            ],
        )

    def transcribe_video(
        self,
        video_path: Union[str, Path],
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Extrai audio de video e transcreve.

        Args:
            video_path: Caminho do arquivo de video
            language: Idioma do audio (None = auto-detect)

        Returns:
            TranscriptionResult
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video nao encontrado: {video_path}")

        # Extrai audio para arquivo temporario
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            self._extract_audio_from_video(video_path, tmp_path)
            return self.transcribe(tmp_path, language=language)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def _convert_to_wav(self, audio_path: Path) -> Path:
        """Converte audio para WAV."""
        output_path = audio_path.with_suffix(".wav")
        audio = AudioSegment.from_file(str(audio_path))
        audio.export(str(output_path), format="wav")
        return output_path

    def _extract_audio_from_video(self, video_path: Path, output_path: Path) -> None:
        """Extrai audio de video usando pydub/ffmpeg."""
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-y",
            str(output_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True)

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Retorna duracao do audio em segundos."""
        try:
            audio = AudioSegment.from_file(str(audio_path))
            return len(audio) / 1000.0
        except Exception:
            return 0.0

    def detect_language(self, audio_path: Union[str, Path]) -> tuple[str, float]:
        """Detecta idioma do audio sem transcrever completamente.

        Args:
            audio_path: Caminho do audio

        Returns:
            Tuple (language_code, confidence)
        """
        whisper = _import_whisper()
        audio_path = Path(audio_path)

        # Carrega audio e pega apenas os primeiros 30 segundos
        audio = whisper.load_audio(str(audio_path))
        audio = whisper.pad_or_trim(audio)

        # Gera mel spectrogram
        mel = whisper.log_mel_spectrogram(audio).to(self.model.device)

        # Detecta idioma
        _, probs = self.model.detect_language(mel)
        detected_lang = max(probs, key=probs.get)
        confidence = probs[detected_lang]

        return detected_lang, round(confidence, 2)

    @staticmethod
    def get_available_models() -> list[dict]:
        """Lista modelos Whisper disponiveis."""
        return [
            {
                "name": "tiny",
                "parameters": "39M",
                "vram": "~1GB",
                "speed": "~32x",
                "quality": "Baixa",
            },
            {
                "name": "base",
                "parameters": "74M",
                "vram": "~1GB",
                "speed": "~16x",
                "quality": "Baixa-Media",
            },
            {
                "name": "small",
                "parameters": "244M",
                "vram": "~2GB",
                "speed": "~6x",
                "quality": "Media",
            },
            {
                "name": "medium",
                "parameters": "769M",
                "vram": "~5GB",
                "speed": "~2x",
                "quality": "Alta",
                "recommended_cpu": True,
            },
            {
                "name": "large",
                "parameters": "1550M",
                "vram": "~10GB",
                "speed": "~1x",
                "quality": "Muito Alta",
            },
            {
                "name": "large-v2",
                "parameters": "1550M",
                "vram": "~10GB",
                "speed": "~1x",
                "quality": "Muito Alta",
            },
            {
                "name": "large-v3",
                "parameters": "1550M",
                "vram": "~10GB",
                "speed": "~1x",
                "quality": "Maxima",
            },
        ]


class WhisperTools:
    """Gerenciador unificado de transcricao - escolhe provider baseado em config."""

    def __init__(
        self,
        provider: Optional[Literal["local", "groq"]] = None,
        model_name: Optional[str] = None,
    ):
        """Inicializa WhisperTools.

        Args:
            provider: Provider de transcricao (local ou groq). Se None, usa config.
            model_name: Nome do modelo (para local Whisper)
        """
        self.provider = provider or settings.whisper_provider
        self._local_tools: Optional[LocalWhisperTools] = None
        self._groq_tools: Optional[GroqWhisperTools] = None
        self._model_name = model_name

    @property
    def _tools(self):
        """Retorna o provider apropriado."""
        if self.provider == "groq":
            if self._groq_tools is None:
                self._groq_tools = GroqWhisperTools()
            return self._groq_tools
        else:
            if self._local_tools is None:
                self._local_tools = LocalWhisperTools(self._model_name)
            return self._local_tools

    def transcribe(
        self,
        audio_path: Union[str, Path],
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcreve audio usando o provider configurado.

        Args:
            audio_path: Caminho do arquivo de audio
            language: Idioma do audio

        Returns:
            TranscriptionResult
        """
        return self._tools.transcribe(audio_path, language=language)

    def transcribe_video(
        self,
        video_path: Union[str, Path],
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Extrai audio de video e transcreve.

        Args:
            video_path: Caminho do arquivo de video
            language: Idioma do audio

        Returns:
            TranscriptionResult
        """
        return self._tools.transcribe_video(video_path, language=language)

    def with_provider(self, provider: Literal["local", "groq"]) -> "WhisperTools":
        """Retorna nova instancia com provider especifico.

        Args:
            provider: Provider desejado

        Returns:
            Nova instancia WhisperTools
        """
        return WhisperTools(provider=provider, model_name=self._model_name)


# Singleton para uso global
whisper_tools = WhisperTools()


def transcribe_audio(
    audio_path: Union[str, Path],
    language: Optional[str] = None,
    provider: Optional[Literal["local", "groq"]] = None,
) -> TranscriptionResult:
    """Funcao de conveniencia para transcricao.

    Args:
        audio_path: Caminho do audio
        language: Idioma
        provider: Provider especifico (sobrescreve config)

    Returns:
        TranscriptionResult
    """
    tools = whisper_tools if provider is None else whisper_tools.with_provider(provider)
    return tools.transcribe(audio_path, language=language)


def transcribe_video(
    video_path: Union[str, Path],
    language: Optional[str] = None,
    provider: Optional[Literal["local", "groq"]] = None,
) -> TranscriptionResult:
    """Funcao de conveniencia para transcricao de video.

    Args:
        video_path: Caminho do video
        language: Idioma
        provider: Provider especifico (sobrescreve config)

    Returns:
        TranscriptionResult
    """
    tools = whisper_tools if provider is None else whisper_tools.with_provider(provider)
    return tools.transcribe_video(video_path, language=language)
