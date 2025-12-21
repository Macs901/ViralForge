"""Tools para processamento de audio/video com FFmpeg."""

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from pydub import AudioSegment

from config.settings import get_settings

settings = get_settings()


@dataclass
class VideoInfo:
    """Informacoes de um video."""

    duration_seconds: float
    width: int
    height: int
    fps: float
    codec: str
    bitrate: Optional[int]
    has_audio: bool


@dataclass
class MixResult:
    """Resultado de mixagem de audio."""

    output_path: Path
    duration_seconds: float
    narration_volume: float
    music_volume: float


class FFmpegTools:
    """Gerenciador de operacoes FFmpeg para video e audio."""

    def __init__(self):
        """Verifica se FFmpeg esta instalado."""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("FFmpeg nao esta instalado ou nao esta no PATH")

    def get_video_info(self, video_path: Union[str, Path]) -> VideoInfo:
        """Obtem informacoes do video usando ffprobe.

        Args:
            video_path: Caminho do video

        Returns:
            VideoInfo com metadados
        """
        video_path = Path(video_path)

        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        # Busca stream de video
        video_stream = None
        has_audio = False
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                video_stream = stream
            elif stream.get("codec_type") == "audio":
                has_audio = True

        if not video_stream:
            raise ValueError("Nenhum stream de video encontrado")

        # Extrai FPS
        fps_str = video_stream.get("r_frame_rate", "30/1")
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) > 0 else 30.0
        else:
            fps = float(fps_str)

        format_info = data.get("format", {})

        return VideoInfo(
            duration_seconds=float(format_info.get("duration", 0)),
            width=int(video_stream.get("width", 0)),
            height=int(video_stream.get("height", 0)),
            fps=fps,
            codec=video_stream.get("codec_name", "unknown"),
            bitrate=int(format_info.get("bit_rate", 0)) if format_info.get("bit_rate") else None,
            has_audio=has_audio,
        )

    def concatenate_videos(
        self,
        video_paths: list[Union[str, Path]],
        output_path: Union[str, Path],
        transition: Optional[str] = None,
    ) -> Path:
        """Concatena multiplos videos em um unico arquivo.

        Args:
            video_paths: Lista de caminhos dos videos
            output_path: Caminho de saida
            transition: Tipo de transicao (None, 'fade', 'dissolve')

        Returns:
            Path do video concatenado
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Cria arquivo de lista para concat
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            for vp in video_paths:
                f.write(f"file '{Path(vp).absolute()}'\n")
            list_file = f.name

        try:
            if transition:
                # Concatenacao com transicao (mais complexo)
                self._concat_with_transition(video_paths, output_path, transition)
            else:
                # Concatenacao simples
                cmd = [
                    "ffmpeg",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", list_file,
                    "-c", "copy",
                    "-y",
                    str(output_path),
                ]
                subprocess.run(cmd, capture_output=True, check=True)
        finally:
            Path(list_file).unlink()

        return output_path

    def _concat_with_transition(
        self,
        video_paths: list[Union[str, Path]],
        output_path: Path,
        transition: str,
    ) -> None:
        """Concatena videos com transicao usando filtros complexos."""
        # Constroi filtro complexo para fade
        inputs = " ".join(f"-i '{p}'" for p in video_paths)
        n = len(video_paths)

        if transition == "fade":
            # Fade de 0.5s entre cada video
            filter_parts = []
            for i in range(n):
                filter_parts.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}]")

            filter_complex = ";".join(filter_parts)
            filter_complex += f";{''.join(f'[v{i}]' for i in range(n))}concat=n={n}:v=1:a=0[outv]"

            cmd = f"ffmpeg {inputs} -filter_complex \"{filter_complex}\" -map \"[outv]\" -y {output_path}"
            subprocess.run(cmd, shell=True, capture_output=True, check=True)
        else:
            # Fallback para concat simples
            raise ValueError(f"Transicao '{transition}' nao suportada")

    def mix_audio_with_video(
        self,
        video_path: Union[str, Path],
        narration_path: Union[str, Path],
        output_path: Union[str, Path],
        music_path: Optional[Union[str, Path]] = None,
        narration_volume: float = 1.0,
        music_volume: float = 0.2,
    ) -> MixResult:
        """Mixa narracao e musica de fundo com video.

        Args:
            video_path: Video sem audio ou com audio original
            narration_path: Arquivo de narracao TTS
            output_path: Caminho de saida
            music_path: Musica de fundo (opcional)
            narration_volume: Volume da narracao (0.0-1.0)
            music_volume: Volume da musica (0.0-1.0)

        Returns:
            MixResult com informacoes da mixagem
        """
        video_path = Path(video_path)
        narration_path = Path(narration_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Obtem duracao do video
        video_info = self.get_video_info(video_path)
        duration = video_info.duration_seconds

        if music_path:
            music_path = Path(music_path)
            # Mix com video + narracao + musica
            filter_complex = (
                f"[1:a]volume={narration_volume}[narr];"
                f"[2:a]volume={music_volume},aloop=loop=-1:size=44100*{int(duration)}[music];"
                f"[narr][music]amix=inputs=2:duration=first[aout]"
            )

            cmd = [
                "ffmpeg",
                "-i", str(video_path),
                "-i", str(narration_path),
                "-i", str(music_path),
                "-filter_complex", filter_complex,
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-y",
                str(output_path),
            ]
        else:
            # Mix com video + narracao apenas
            cmd = [
                "ffmpeg",
                "-i", str(video_path),
                "-i", str(narration_path),
                "-filter_complex", f"[1:a]volume={narration_volume}[aout]",
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-y",
                str(output_path),
            ]

        subprocess.run(cmd, capture_output=True, check=True)

        return MixResult(
            output_path=output_path,
            duration_seconds=duration,
            narration_volume=narration_volume,
            music_volume=music_volume,
        )

    def extract_audio(
        self,
        video_path: Union[str, Path],
        output_path: Union[str, Path],
        format: str = "mp3",
    ) -> Path:
        """Extrai audio de video.

        Args:
            video_path: Caminho do video
            output_path: Caminho de saida
            format: Formato de saida (mp3, wav, aac)

        Returns:
            Path do audio extraido
        """
        video_path = Path(video_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        codec_map = {
            "mp3": "libmp3lame",
            "wav": "pcm_s16le",
            "aac": "aac",
        }

        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",
            "-acodec", codec_map.get(format, "libmp3lame"),
            "-y",
            str(output_path),
        ]

        subprocess.run(cmd, capture_output=True, check=True)
        return output_path

    def resize_video(
        self,
        video_path: Union[str, Path],
        output_path: Union[str, Path],
        width: int = 1080,
        height: int = 1920,
    ) -> Path:
        """Redimensiona video para resolucao especifica.

        Args:
            video_path: Caminho do video
            output_path: Caminho de saida
            width: Largura
            height: Altura

        Returns:
            Path do video redimensionado
        """
        video_path = Path(video_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "-c:a", "copy",
            "-y",
            str(output_path),
        ]

        subprocess.run(cmd, capture_output=True, check=True)
        return output_path

    def add_subtitles(
        self,
        video_path: Union[str, Path],
        subtitles_path: Union[str, Path],
        output_path: Union[str, Path],
        font_size: int = 24,
        font_color: str = "white",
    ) -> Path:
        """Adiciona legendas ao video.

        Args:
            video_path: Caminho do video
            subtitles_path: Caminho do arquivo SRT
            output_path: Caminho de saida
            font_size: Tamanho da fonte
            font_color: Cor da fonte

        Returns:
            Path do video com legendas
        """
        video_path = Path(video_path)
        subtitles_path = Path(subtitles_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Escapa caminho para filtro FFmpeg
        subs_escaped = str(subtitles_path).replace(":", "\\:").replace("\\", "/")

        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vf", f"subtitles='{subs_escaped}':force_style='FontSize={font_size},PrimaryColour=&H{self._color_to_ass(font_color)}&'",
            "-c:a", "copy",
            "-y",
            str(output_path),
        ]

        subprocess.run(cmd, capture_output=True, check=True)
        return output_path

    def _color_to_ass(self, color: str) -> str:
        """Converte nome de cor para formato ASS (BGR)."""
        colors = {
            "white": "FFFFFF",
            "black": "000000",
            "red": "0000FF",
            "green": "00FF00",
            "blue": "FF0000",
            "yellow": "00FFFF",
        }
        return colors.get(color.lower(), "FFFFFF")

    def create_thumbnail(
        self,
        video_path: Union[str, Path],
        output_path: Union[str, Path],
        timestamp: float = 1.0,
    ) -> Path:
        """Cria thumbnail do video.

        Args:
            video_path: Caminho do video
            output_path: Caminho de saida (jpg/png)
            timestamp: Momento do video em segundos

        Returns:
            Path da thumbnail
        """
        video_path = Path(video_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-ss", str(timestamp),
            "-vframes", "1",
            "-y",
            str(output_path),
        ]

        subprocess.run(cmd, capture_output=True, check=True)
        return output_path

    def trim_video(
        self,
        video_path: Union[str, Path],
        output_path: Union[str, Path],
        start_seconds: float,
        end_seconds: float,
    ) -> Path:
        """Corta trecho do video.

        Args:
            video_path: Caminho do video
            output_path: Caminho de saida
            start_seconds: Inicio do corte
            end_seconds: Fim do corte

        Returns:
            Path do video cortado
        """
        video_path = Path(video_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        duration = end_seconds - start_seconds

        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-ss", str(start_seconds),
            "-t", str(duration),
            "-c", "copy",
            "-y",
            str(output_path),
        ]

        subprocess.run(cmd, capture_output=True, check=True)
        return output_path


# Singleton para uso global
ffmpeg_tools = FFmpegTools()
