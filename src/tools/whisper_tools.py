"""Tools para transcricao de audio usando Whisper local."""

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import whisper
from pydub import AudioSegment

from config.settings import get_settings

settings = get_settings()


@dataclass
class TranscriptionResult:
    """Resultado de transcricao."""

    text: str
    language: str
    confidence: float
    duration_seconds: float
    segments: list[dict]


class WhisperTools:
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
            print(f"[Whisper] Carregando modelo '{self.model_name}'...")
            self._model = whisper.load_model(self.model_name)
            print(f"[Whisper] Modelo carregado!")
        return self._model

    def transcribe(
        self,
        audio_path: Union[str, Path],
        language: Optional[str] = None,
        task: str = "transcribe",
    ) -> TranscriptionResult:
        """Transcreve audio usando Whisper.

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
            confidence = 1.0 - avg_confidence  # Inverte (no_speech_prob baixo = alta confianca)
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
            # Limpa arquivo temporario
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
        import subprocess

        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",  # Sem video
            "-acodec", "pcm_s16le",  # Codec WAV
            "-ar", "16000",  # 16kHz (ideal para Whisper)
            "-ac", "1",  # Mono
            "-y",  # Sobrescreve
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

    @staticmethod
    def get_available_models() -> list[dict]:
        """Lista modelos Whisper disponiveis.

        Returns:
            Lista de modelos com nome, parametros e requisitos
        """
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

    def detect_language(self, audio_path: Union[str, Path]) -> tuple[str, float]:
        """Detecta idioma do audio sem transcrever completamente.

        Args:
            audio_path: Caminho do audio

        Returns:
            Tuple (language_code, confidence)
        """
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


# Singleton para uso global
whisper_tools = WhisperTools()


def transcribe_audio(
    audio_path: Union[str, Path],
    language: Optional[str] = None,
) -> TranscriptionResult:
    """Funcao de conveniencia para transcricao."""
    return whisper_tools.transcribe(audio_path, language=language)


def transcribe_video(
    video_path: Union[str, Path],
    language: Optional[str] = None,
) -> TranscriptionResult:
    """Funcao de conveniencia para transcricao de video."""
    return whisper_tools.transcribe_video(video_path, language=language)
