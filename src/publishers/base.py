"""Base Publisher - Classe base para publicacao em plataformas."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import os


class PublishStatus(str, Enum):
    """Status de publicacao."""
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    PUBLISHED = "published"
    SCHEDULED = "scheduled"
    FAILED = "failed"


@dataclass
class PublishResult:
    """Resultado de publicacao."""
    status: PublishStatus
    platform: str
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    error: Optional[str] = None
    extra_data: dict = field(default_factory=dict)


@dataclass
class ContentToPublish:
    """Conteudo a ser publicado."""
    video_path: str
    caption: str
    hashtags: list[str] = field(default_factory=list)
    thumbnail_path: Optional[str] = None
    title: Optional[str] = None  # Para YouTube
    description: Optional[str] = None  # Para YouTube
    scheduled_at: Optional[datetime] = None
    extra_options: dict = field(default_factory=dict)

    def get_full_caption(self, max_length: int = 2200) -> str:
        """Retorna caption com hashtags."""
        hashtag_text = " ".join(f"#{h}" if not h.startswith("#") else h for h in self.hashtags)
        full = f"{self.caption}\n\n{hashtag_text}"
        return full[:max_length]


class BasePublisher(ABC):
    """Classe base para publishers."""

    def __init__(self):
        """Inicializa o publisher."""
        self.platform_name = "base"
        self._authenticated = False

    @abstractmethod
    def authenticate(self) -> bool:
        """Autentica com a plataforma.

        Returns:
            True se autenticado com sucesso
        """
        pass

    @abstractmethod
    def publish(self, content: ContentToPublish) -> PublishResult:
        """Publica o conteudo.

        Args:
            content: Conteudo a ser publicado

        Returns:
            PublishResult
        """
        pass

    @abstractmethod
    def schedule(self, content: ContentToPublish, publish_at: datetime) -> PublishResult:
        """Agenda publicacao.

        Args:
            content: Conteudo a ser publicado
            publish_at: Data/hora para publicar

        Returns:
            PublishResult
        """
        pass

    def is_authenticated(self) -> bool:
        """Verifica se esta autenticado."""
        return self._authenticated

    def validate_content(self, content: ContentToPublish) -> tuple[bool, str]:
        """Valida se o conteudo pode ser publicado.

        Args:
            content: Conteudo para validar

        Returns:
            Tupla (valido, mensagem_erro)
        """
        # Verifica se arquivo existe
        if not os.path.exists(content.video_path):
            return False, f"Video nao encontrado: {content.video_path}"

        # Verifica tamanho
        file_size = os.path.getsize(content.video_path)
        if file_size > 4 * 1024 * 1024 * 1024:  # 4GB
            return False, "Video muito grande (max 4GB)"

        # Verifica caption
        if not content.caption:
            return False, "Caption vazia"

        return True, ""

    def prepare_export(self, content: ContentToPublish, output_dir: str) -> dict:
        """Prepara conteudo para exportacao manual.

        Cria pasta com todos os arquivos necessarios para publicacao manual.

        Args:
            content: Conteudo
            output_dir: Diretorio de saida

        Returns:
            Dict com paths dos arquivos gerados
        """
        import shutil

        # Cria diretorio
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_dir = os.path.join(output_dir, f"export_{self.platform_name}_{timestamp}")
        os.makedirs(export_dir, exist_ok=True)

        result = {"export_dir": export_dir}

        # Copia video
        video_ext = os.path.splitext(content.video_path)[1]
        video_dest = os.path.join(export_dir, f"video{video_ext}")
        shutil.copy2(content.video_path, video_dest)
        result["video"] = video_dest

        # Copia thumbnail se existir
        if content.thumbnail_path and os.path.exists(content.thumbnail_path):
            thumb_ext = os.path.splitext(content.thumbnail_path)[1]
            thumb_dest = os.path.join(export_dir, f"thumbnail{thumb_ext}")
            shutil.copy2(content.thumbnail_path, thumb_dest)
            result["thumbnail"] = thumb_dest

        # Gera arquivo com caption
        caption_file = os.path.join(export_dir, "caption.txt")
        with open(caption_file, "w", encoding="utf-8") as f:
            f.write(content.get_full_caption())
        result["caption_file"] = caption_file

        # Gera arquivo com hashtags
        if content.hashtags:
            hashtags_file = os.path.join(export_dir, "hashtags.txt")
            with open(hashtags_file, "w", encoding="utf-8") as f:
                f.write("\n".join(f"#{h}" if not h.startswith("#") else h for h in content.hashtags))
            result["hashtags_file"] = hashtags_file

        # Gera instrucoes
        instructions_file = os.path.join(export_dir, "INSTRUCTIONS.txt")
        with open(instructions_file, "w", encoding="utf-8") as f:
            f.write(f"=== PUBLICACAO {self.platform_name.upper()} ===\n\n")
            f.write(f"Data de geracao: {datetime.now().isoformat()}\n\n")
            f.write("ARQUIVOS:\n")
            f.write(f"- Video: video{video_ext}\n")
            if content.thumbnail_path:
                f.write(f"- Thumbnail: thumbnail{thumb_ext}\n")
            f.write("- Caption: caption.txt\n")
            if content.hashtags:
                f.write("- Hashtags: hashtags.txt\n")
            f.write("\n")
            f.write("INSTRUCOES:\n")
            f.write(self._get_publish_instructions())
        result["instructions_file"] = instructions_file

        return result

    def _get_publish_instructions(self) -> str:
        """Retorna instrucoes de publicacao especificas da plataforma."""
        return "1. Abra o app da plataforma\n2. Faca upload do video\n3. Cole a caption\n4. Publique!"
