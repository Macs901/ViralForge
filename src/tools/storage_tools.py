"""Tools para storage no MinIO (S3-compatible)."""

import io
import os
from pathlib import Path
from typing import BinaryIO, Optional, Union
from urllib.parse import urljoin

from minio import Minio
from minio.error import S3Error

from config.settings import get_settings

settings = get_settings()


class StorageTools:
    """Gerenciador de storage usando MinIO."""

    def __init__(self):
        """Inicializa conexao com MinIO."""
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket = settings.minio_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Garante que o bucket existe."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as e:
            raise RuntimeError(f"Erro ao criar bucket {self.bucket}: {e}")

    def upload_file(
        self,
        local_path: Union[str, Path],
        remote_path: str,
        content_type: Optional[str] = None,
    ) -> str:
        """Upload de arquivo local para MinIO.

        Args:
            local_path: Caminho do arquivo local
            remote_path: Caminho no MinIO (ex: 'videos/2024/video_001.mp4')
            content_type: MIME type do arquivo

        Returns:
            URL completa do arquivo no MinIO
        """
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"Arquivo nao encontrado: {local_path}")

        # Detecta content-type se nao informado
        if content_type is None:
            content_type = self._guess_content_type(local_path.suffix)

        file_size = local_path.stat().st_size

        with open(local_path, "rb") as f:
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=remote_path,
                data=f,
                length=file_size,
                content_type=content_type,
            )

        return f"{self.bucket}/{remote_path}"

    def upload_bytes(
        self,
        data: bytes,
        remote_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload de bytes diretamente para MinIO.

        Args:
            data: Bytes a serem enviados
            remote_path: Caminho no MinIO
            content_type: MIME type

        Returns:
            URL completa do arquivo no MinIO
        """
        data_stream = io.BytesIO(data)
        self.client.put_object(
            bucket_name=self.bucket,
            object_name=remote_path,
            data=data_stream,
            length=len(data),
            content_type=content_type,
        )
        return f"{self.bucket}/{remote_path}"

    def download_file(
        self,
        remote_path: str,
        local_path: Union[str, Path],
    ) -> Path:
        """Download de arquivo do MinIO para local.

        Args:
            remote_path: Caminho no MinIO
            local_path: Caminho local de destino

        Returns:
            Path do arquivo baixado
        """
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)

        self.client.fget_object(
            bucket_name=self.bucket,
            object_name=remote_path,
            file_path=str(local_path),
        )
        return local_path

    def download_bytes(self, remote_path: str) -> bytes:
        """Download de arquivo do MinIO como bytes.

        Args:
            remote_path: Caminho no MinIO

        Returns:
            Bytes do arquivo
        """
        response = self.client.get_object(
            bucket_name=self.bucket,
            object_name=remote_path,
        )
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_file(self, remote_path: str) -> bool:
        """Remove arquivo do MinIO.

        Args:
            remote_path: Caminho no MinIO

        Returns:
            True se removido com sucesso
        """
        try:
            self.client.remove_object(
                bucket_name=self.bucket,
                object_name=remote_path,
            )
            return True
        except S3Error:
            return False

    def file_exists(self, remote_path: str) -> bool:
        """Verifica se arquivo existe no MinIO.

        Args:
            remote_path: Caminho no MinIO

        Returns:
            True se existe
        """
        try:
            self.client.stat_object(
                bucket_name=self.bucket,
                object_name=remote_path,
            )
            return True
        except S3Error:
            return False

    def get_file_url(self, remote_path: str, expires_hours: int = 24) -> str:
        """Gera URL pre-assinada para acesso ao arquivo.

        Args:
            remote_path: Caminho no MinIO
            expires_hours: Horas ate expirar (default: 24)

        Returns:
            URL pre-assinada
        """
        from datetime import timedelta

        return self.client.presigned_get_object(
            bucket_name=self.bucket,
            object_name=remote_path,
            expires=timedelta(hours=expires_hours),
        )

    def list_files(self, prefix: str = "", recursive: bool = True) -> list[str]:
        """Lista arquivos no bucket.

        Args:
            prefix: Prefixo para filtrar (ex: 'videos/')
            recursive: Se True, lista subpastas

        Returns:
            Lista de caminhos de arquivos
        """
        objects = self.client.list_objects(
            bucket_name=self.bucket,
            prefix=prefix,
            recursive=recursive,
        )
        return [obj.object_name for obj in objects]

    def get_file_size(self, remote_path: str) -> int:
        """Retorna tamanho do arquivo em bytes.

        Args:
            remote_path: Caminho no MinIO

        Returns:
            Tamanho em bytes
        """
        stat = self.client.stat_object(
            bucket_name=self.bucket,
            object_name=remote_path,
        )
        return stat.size

    def copy_file(self, source_path: str, dest_path: str) -> str:
        """Copia arquivo dentro do MinIO.

        Args:
            source_path: Caminho de origem
            dest_path: Caminho de destino

        Returns:
            Caminho do arquivo copiado
        """
        from minio.commonconfig import CopySource

        self.client.copy_object(
            bucket_name=self.bucket,
            object_name=dest_path,
            source=CopySource(self.bucket, source_path),
        )
        return f"{self.bucket}/{dest_path}"

    def _guess_content_type(self, suffix: str) -> str:
        """Adivinha content-type baseado na extensao."""
        content_types = {
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".mov": "video/quicktime",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".ogg": "audio/ogg",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".json": "application/json",
            ".txt": "text/plain",
        }
        return content_types.get(suffix.lower(), "application/octet-stream")

    # === Metodos de conveniencia para tipos especificos ===

    def upload_video(self, local_path: Union[str, Path], video_id: int) -> str:
        """Upload de video com path padronizado.

        Args:
            local_path: Caminho do video local
            video_id: ID do video no banco

        Returns:
            Caminho no MinIO
        """
        local_path = Path(local_path)
        remote_path = f"videos/{video_id}/original{local_path.suffix}"
        return self.upload_file(local_path, remote_path)

    def upload_audio(self, local_path: Union[str, Path], video_id: int, audio_type: str = "tts") -> str:
        """Upload de audio com path padronizado.

        Args:
            local_path: Caminho do audio local
            video_id: ID do video no banco
            audio_type: Tipo (tts, music, extracted)

        Returns:
            Caminho no MinIO
        """
        local_path = Path(local_path)
        remote_path = f"audio/{video_id}/{audio_type}{local_path.suffix}"
        return self.upload_file(local_path, remote_path)

    def upload_production(self, local_path: Union[str, Path], production_id: int, file_type: str = "final") -> str:
        """Upload de video produzido com path padronizado.

        Args:
            local_path: Caminho do video local
            production_id: ID da producao no banco
            file_type: Tipo (clip_001, concatenated, final)

        Returns:
            Caminho no MinIO
        """
        local_path = Path(local_path)
        remote_path = f"productions/{production_id}/{file_type}{local_path.suffix}"
        return self.upload_file(local_path, remote_path)


# Singleton para uso global
storage_tools = StorageTools()
