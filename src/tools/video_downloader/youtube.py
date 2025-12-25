"""Downloader de YouTube usando yt-dlp."""

import hashlib
import logging
import subprocess
from pathlib import Path
from typing import Any, Optional

from src.tools.video_downloader.base import VideoDownloaderBase

logger = logging.getLogger(__name__)


class YouTubeDownloader(VideoDownloaderBase):
    """Downloader de YouTube usando yt-dlp."""

    def can_download(self, url: str) -> bool:
        """Verifica se e uma URL do YouTube."""
        return "youtube.com" in url.lower() or "youtu.be" in url.lower()

    def get_platform_name(self) -> str:
        """Retorna o nome da plataforma."""
        return "youtube"

    def download(
        self, url: str, creator: str, metadata: Optional[dict[str, Any]] = None
    ) -> Optional[Path]:
        """Baixa video do YouTube usando yt-dlp.

        Args:
            url: URL do video do YouTube
            creator: Nome do criador
            metadata: Metadados opcionais

        Returns:
            Caminho do video baixado ou None em caso de erro
        """
        creator_dir = self.output_dir / creator
        creator_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Gera nome de arquivo unico
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            output_template = str(creator_dir / f"%(title)s_{url_hash}.%(ext)s")

            logger.info(f"[YouTube] Baixando: {url}")
            result = subprocess.run(
                [
                    "yt-dlp",
                    url,
                    "-o",
                    output_template,
                    "--format",
                    "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                    "--no-playlist",
                ],
                capture_output=True,
                text=True,
                timeout=600,  # YouTube pode demorar mais
            )

            if result.returncode != 0:
                logger.error(f"[YouTube] Erro: {result.stderr}")
                raise subprocess.CalledProcessError(
                    result.returncode, "yt-dlp", result.stderr
                )

            # Procura o arquivo mais recente
            video_files = sorted(
                creator_dir.glob("*.mp4"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if video_files:
                logger.info(f"[YouTube] Sucesso: {video_files[0]}")
                return video_files[0]
            else:
                raise ValueError("Nenhum arquivo de video encontrado apos download")

        except FileNotFoundError:
            raise ValueError("yt-dlp nao instalado. Execute: pip install yt-dlp")
        except subprocess.TimeoutExpired:
            raise ValueError("Timeout ao baixar video do YouTube")
        except Exception as e:
            logger.error(f"[YouTube] Erro ao baixar: {e}")
            raise ValueError(f"Erro ao baixar do YouTube: {e}")
