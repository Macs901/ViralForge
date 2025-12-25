"""Factory para criar downloaders apropriados baseado na URL."""

import logging
from pathlib import Path
from typing import Optional

from src.tools.video_downloader.base import VideoDownloaderBase
from src.tools.video_downloader.instagram import InstagramDownloader
from src.tools.video_downloader.tiktok import TikTokDownloader
from src.tools.video_downloader.youtube import YouTubeDownloader

logger = logging.getLogger(__name__)


class VideoDownloaderFactory:
    """Factory para criar downloaders de video."""

    # Lista de downloaders disponiveis (em ordem de prioridade)
    DOWNLOADERS = [
        InstagramDownloader,
        YouTubeDownloader,
        TikTokDownloader,
    ]

    @classmethod
    def create_downloader(
        cls, url: str, output_dir: Path, meta_api_key: Optional[str] = None
    ) -> Optional[VideoDownloaderBase]:
        """Cria um downloader apropriado para a URL.

        Args:
            url: URL do video
            output_dir: Diretorio de saida
            meta_api_key: Chave da API Meta (opcional, para Instagram)

        Returns:
            Downloader apropriado ou None se nenhum suportar a URL
        """
        for downloader_class in cls.DOWNLOADERS:
            if downloader_class == InstagramDownloader:
                temp_instance = downloader_class(output_dir, meta_api_key)
            else:
                temp_instance = downloader_class(output_dir)

            if temp_instance.can_download(url):
                logger.info(
                    f"Downloader selecionado: {temp_instance.get_platform_name()}"
                )
                return temp_instance

        logger.warning(f"Nenhum downloader encontrado para URL: {url}")
        return None

    @classmethod
    def get_supported_platforms(cls) -> list[str]:
        """Retorna lista de plataformas suportadas.

        Returns:
            Lista de nomes de plataformas
        """
        platforms = []
        temp_dir = Path("/tmp")
        for downloader_class in cls.DOWNLOADERS:
            try:
                if downloader_class == InstagramDownloader:
                    instance = downloader_class(temp_dir)
                else:
                    instance = downloader_class(temp_dir)
                platforms.append(instance.get_platform_name())
            except Exception as e:
                logger.warning(
                    f"Falha ao inicializar {downloader_class.__name__}: {e}"
                )
        return platforms

    @classmethod
    def download_video(
        cls,
        url: str,
        creator: str,
        output_dir: Path,
        meta_api_key: Optional[str] = None,
    ) -> Optional[Path]:
        """Metodo de conveniencia para baixar video diretamente.

        Args:
            url: URL do video
            creator: Nome do criador
            output_dir: Diretorio de saida
            meta_api_key: Chave da API Meta (opcional)

        Returns:
            Caminho do video baixado ou None
        """
        downloader = cls.create_downloader(url, output_dir, meta_api_key)
        if downloader:
            return downloader.download(url, creator)
        return None
