"""Downloader de Instagram com estrategia resiliente.

Implementa fallback: Meta Graph API -> gallery-dl -> yt-dlp
"""

import hashlib
import logging
import subprocess
from pathlib import Path
from typing import Any, Optional

from src.tools.video_downloader.base import VideoDownloaderBase

logger = logging.getLogger(__name__)


class InstagramDownloader(VideoDownloaderBase):
    """Downloader de Instagram com multiplas estrategias de fallback."""

    def __init__(self, output_dir: Path, meta_api_key: Optional[str] = None):
        """Inicializa o downloader do Instagram.

        Args:
            output_dir: Diretorio de saida
            meta_api_key: Chave da API Meta Graph (opcional)
        """
        super().__init__(output_dir)
        self.meta_api_key = meta_api_key
        self.strategies = [
            ("meta_graph_api", self._download_with_meta_api),
            ("gallery_dl", self._download_with_gallery_dl),
            ("yt_dlp", self._download_with_yt_dlp),
        ]

    def can_download(self, url: str) -> bool:
        """Verifica se e uma URL do Instagram."""
        return "instagram.com" in url.lower() or "instagr.am" in url.lower()

    def get_platform_name(self) -> str:
        """Retorna o nome da plataforma."""
        return "instagram"

    def download(
        self, url: str, creator: str, metadata: Optional[dict[str, Any]] = None
    ) -> Optional[Path]:
        """Tenta baixar usando multiplas estrategias em ordem de prioridade.

        Args:
            url: URL do post/reel do Instagram
            creator: Nome do criador
            metadata: Metadados opcionais

        Returns:
            Caminho do video baixado ou None se todas as estrategias falharem
        """
        creator_dir = self.output_dir / creator
        creator_dir.mkdir(parents=True, exist_ok=True)

        errors = []
        for strategy_name, strategy_func in self.strategies:
            try:
                logger.info(f"[Instagram] Tentando estrategia: {strategy_name}")
                result = strategy_func(url, creator_dir)
                if result and result.exists():
                    logger.info(f"[Instagram] Sucesso com {strategy_name}: {result}")
                    return result
            except Exception as e:
                logger.warning(f"[Instagram] {strategy_name} falhou: {e}")
                errors.append(f"{strategy_name}: {e}")
                continue

        error_msg = "; ".join(errors)
        raise ValueError(f"Todas as estrategias falharam para {url}: {error_msg}")

    def _download_with_meta_api(self, url: str, output_dir: Path) -> Optional[Path]:
        """Tenta baixar usando Meta Graph API (mais confiavel).

        Requer conta business e token de acesso.
        """
        if not self.meta_api_key:
            raise ValueError("Meta API key nao configurada")

        # TODO: Implementar chamada a Meta Graph API
        # Por enquanto, apenas levanta excecao para tentar proxima estrategia
        raise NotImplementedError("Meta Graph API nao implementada ainda")

    def _download_with_gallery_dl(self, url: str, output_dir: Path) -> Optional[Path]:
        """Tenta baixar usando gallery-dl (CLI robusto).

        Requer: pip install gallery-dl
        """
        try:
            result = subprocess.run(
                ["gallery-dl", url, "-d", str(output_dir)],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                # gallery-dl salva em subdiretorios, precisa encontrar o arquivo
                for video_file in output_dir.rglob("*.mp4"):
                    return video_file
                # Tenta outros formatos
                for video_file in output_dir.rglob("*.webm"):
                    return video_file
                return None
            else:
                raise subprocess.CalledProcessError(
                    result.returncode, "gallery-dl", result.stderr
                )
        except FileNotFoundError:
            raise ValueError("gallery-dl nao instalado. Execute: pip install gallery-dl")
        except subprocess.TimeoutExpired:
            raise ValueError("Timeout ao baixar com gallery-dl")

    def _download_with_yt_dlp(self, url: str, output_dir: Path) -> Optional[Path]:
        """Tenta baixar usando yt-dlp (ultimo recurso, menos confiavel para Instagram).

        Requer: pip install yt-dlp
        """
        try:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            output_template = str(output_dir / f"%(title)s_{url_hash}.%(ext)s")

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
                timeout=300,
            )

            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode, "yt-dlp", result.stderr
                )

            video_files = sorted(
                output_dir.glob("*.mp4"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if video_files:
                return video_files[0]
            else:
                raise ValueError("Nenhum arquivo de video encontrado apos download")

        except FileNotFoundError:
            raise ValueError("yt-dlp nao instalado. Execute: pip install yt-dlp")
        except subprocess.TimeoutExpired:
            raise ValueError("Timeout ao baixar com yt-dlp")
