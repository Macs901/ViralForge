"""Interface base para downloaders de video."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional


class VideoDownloaderBase(ABC):
    """Interface base para downloaders de video."""

    def __init__(self, output_dir: Path):
        """Inicializa o downloader.

        Args:
            output_dir: Diretorio onde salvar os videos
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def can_download(self, url: str) -> bool:
        """Verifica se este downloader pode baixar a URL.

        Args:
            url: URL do video

        Returns:
            True se pode baixar, False caso contrario
        """
        pass

    @abstractmethod
    def download(
        self, url: str, creator: str, metadata: Optional[dict[str, Any]] = None
    ) -> Optional[Path]:
        """Baixa um video.

        Args:
            url: URL do video
            creator: Nome do criador
            metadata: Metadados opcionais (titulo, descricao, etc)

        Returns:
            Caminho do video baixado ou None em caso de erro
        """
        pass

    @abstractmethod
    def get_platform_name(self) -> str:
        """Retorna o nome da plataforma.

        Returns:
            Nome da plataforma (ex: "Instagram", "YouTube")
        """
        pass
