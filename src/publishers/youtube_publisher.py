"""YouTube Publisher - Publicacao no YouTube Shorts."""

import os
from datetime import datetime
from typing import Optional

from config.settings import get_settings
from src.publishers.base import (
    BasePublisher,
    ContentToPublish,
    PublishResult,
    PublishStatus,
)

settings = get_settings()


class YouTubePublisher(BasePublisher):
    """Publisher para YouTube Shorts.

    Suporta:
    - Publicacao via YouTube Data API v3
    - Exportacao para publicacao manual
    - Integracao com ferramentas de terceiros (webhooks)

    Requisitos para API:
    - Google Cloud Project com YouTube Data API habilitada
    - OAuth2 credentials
    - Canal do YouTube verificado
    """

    def __init__(self):
        """Inicializa o publisher."""
        super().__init__()
        self.platform_name = "youtube"

        # Credenciais (OAuth2)
        self.client_id = os.getenv("YOUTUBE_CLIENT_ID")
        self.client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
        self.refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN")
        self.access_token = None

        # Webhook para integracao externa
        self.webhook_url = os.getenv("YOUTUBE_PUBLISH_WEBHOOK")

    def authenticate(self) -> bool:
        """Autentica com YouTube Data API via OAuth2."""
        if not self.client_id or not self.client_secret or not self.refresh_token:
            print("[YouTubePublisher] Credenciais OAuth2 nao configuradas")
            self._authenticated = False
            return False

        try:
            import httpx

            # Refresh token
            response = httpx.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")

                # Valida token
                channel_resp = httpx.get(
                    "https://www.googleapis.com/youtube/v3/channels",
                    params={
                        "part": "snippet",
                        "mine": "true",
                    },
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                    },
                    timeout=10,
                )

                if channel_resp.status_code == 200:
                    channel_data = channel_resp.json()
                    items = channel_data.get("items", [])
                    if items:
                        print(f"[YouTubePublisher] Autenticado como {items[0]['snippet']['title']}")
                        self._authenticated = True
                        return True

            print(f"[YouTubePublisher] Erro de autenticacao")
            self._authenticated = False
            return False

        except Exception as e:
            print(f"[YouTubePublisher] Erro: {e}")
            self._authenticated = False
            return False

    def publish(self, content: ContentToPublish) -> PublishResult:
        """Publica um Short no YouTube."""
        valid, error = self.validate_content(content)
        if not valid:
            return PublishResult(
                status=PublishStatus.FAILED,
                platform=self.platform_name,
                error=error,
            )

        # Webhook se disponivel
        if self.webhook_url:
            return self._publish_via_webhook(content)

        # API se autenticado
        if self._authenticated and self.access_token:
            return self._publish_via_api(content)

        # Exportacao manual
        return self._export_for_manual_publish(content)

    def _publish_via_api(self, content: ContentToPublish) -> PublishResult:
        """Publica via YouTube Data API v3 (resumable upload)."""
        import httpx
        import json

        try:
            # Prepara metadata
            title = content.title or content.caption[:100]
            description = content.description or content.get_full_caption()

            # Adiciona #Shorts no titulo/descricao para marcar como Short
            if "#shorts" not in title.lower() and "#short" not in title.lower():
                title = f"{title} #Shorts"

            metadata = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": content.hashtags[:500] if content.hashtags else [],
                    "categoryId": "22",  # People & Blogs
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False,
                },
            }

            # Step 1: Inicia resumable upload
            file_size = os.path.getsize(content.video_path)

            init_response = httpx.post(
                "https://www.googleapis.com/upload/youtube/v3/videos",
                params={
                    "uploadType": "resumable",
                    "part": "snippet,status",
                },
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                    "X-Upload-Content-Length": str(file_size),
                    "X-Upload-Content-Type": "video/*",
                },
                json=metadata,
                timeout=30,
            )

            if init_response.status_code != 200:
                return PublishResult(
                    status=PublishStatus.FAILED,
                    platform=self.platform_name,
                    error=f"Init failed: {init_response.text}",
                )

            upload_url = init_response.headers.get("Location")

            # Step 2: Upload video
            with open(content.video_path, "rb") as f:
                upload_response = httpx.put(
                    upload_url,
                    content=f.read(),
                    headers={
                        "Content-Type": "video/*",
                        "Content-Length": str(file_size),
                    },
                    timeout=600,  # 10 minutos
                )

            if upload_response.status_code in [200, 201]:
                data = upload_response.json()
                video_id = data.get("id")
                return PublishResult(
                    status=PublishStatus.PUBLISHED,
                    platform=self.platform_name,
                    post_id=video_id,
                    post_url=f"https://youtube.com/shorts/{video_id}",
                    extra_data=data,
                )
            else:
                return PublishResult(
                    status=PublishStatus.FAILED,
                    platform=self.platform_name,
                    error=f"Upload failed: {upload_response.text}",
                )

        except Exception as e:
            return PublishResult(
                status=PublishStatus.FAILED,
                platform=self.platform_name,
                error=str(e),
            )

    def _publish_via_webhook(self, content: ContentToPublish) -> PublishResult:
        """Publica via webhook externo."""
        import httpx

        try:
            response = httpx.post(
                self.webhook_url,
                json={
                    "platform": "youtube",
                    "type": "short",
                    "video_path": content.video_path,
                    "title": content.title or content.caption[:100],
                    "description": content.description or content.get_full_caption(),
                    "tags": content.hashtags,
                    "scheduled_at": content.scheduled_at.isoformat() if content.scheduled_at else None,
                },
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                return PublishResult(
                    status=PublishStatus.SCHEDULED if content.scheduled_at else PublishStatus.PENDING,
                    platform=self.platform_name,
                    post_id=data.get("id"),
                    extra_data=data,
                )
            else:
                return PublishResult(
                    status=PublishStatus.FAILED,
                    platform=self.platform_name,
                    error=f"Webhook error: {response.text}",
                )

        except Exception as e:
            return PublishResult(
                status=PublishStatus.FAILED,
                platform=self.platform_name,
                error=str(e),
            )

    def _export_for_manual_publish(self, content: ContentToPublish) -> PublishResult:
        """Exporta para publicacao manual."""
        export_dir = os.getenv("VIRALFORGE_EXPORT_DIR", "/tmp/viralforge_exports")
        result = self.prepare_export(content, export_dir)

        # Adiciona arquivo de metadata para YouTube
        metadata_file = os.path.join(result["export_dir"], "youtube_metadata.txt")
        with open(metadata_file, "w", encoding="utf-8") as f:
            f.write(f"TITULO: {content.title or content.caption[:100]} #Shorts\n\n")
            f.write(f"DESCRICAO:\n{content.description or content.get_full_caption()}\n\n")
            f.write(f"TAGS:\n{', '.join(content.hashtags)}\n")

        result["metadata_file"] = metadata_file

        return PublishResult(
            status=PublishStatus.PENDING,
            platform=self.platform_name,
            extra_data={
                "mode": "manual_export",
                "export_dir": result["export_dir"],
                "files": result,
            },
        )

    def schedule(self, content: ContentToPublish, publish_at: datetime) -> PublishResult:
        """Agenda publicacao.

        YouTube Data API suporta agendamento nativo via scheduledStartTime.
        """
        content.scheduled_at = publish_at

        if self.webhook_url:
            return self._publish_via_webhook(content)

        if self._authenticated and self.access_token:
            # YouTube suporta agendamento via API
            return self._schedule_via_api(content, publish_at)

        export_dir = os.getenv("VIRALFORGE_EXPORT_DIR", "/tmp/viralforge_exports")
        result = self.prepare_export(content, export_dir)

        return PublishResult(
            status=PublishStatus.SCHEDULED,
            platform=self.platform_name,
            scheduled_at=publish_at,
            extra_data={
                "mode": "manual_schedule",
                "scheduled_for": publish_at.isoformat(),
                "export_dir": result["export_dir"],
            },
        )

    def _schedule_via_api(self, content: ContentToPublish, publish_at: datetime) -> PublishResult:
        """Agenda via YouTube API."""
        import httpx

        try:
            title = content.title or content.caption[:100]
            if "#shorts" not in title.lower():
                title = f"{title} #Shorts"

            metadata = {
                "snippet": {
                    "title": title,
                    "description": content.description or content.get_full_caption(),
                    "tags": content.hashtags[:500] if content.hashtags else [],
                    "categoryId": "22",
                },
                "status": {
                    "privacyStatus": "private",  # Sera publicado no horario
                    "publishAt": publish_at.isoformat() + "Z",
                    "selfDeclaredMadeForKids": False,
                },
            }

            # Upload similar ao publish
            file_size = os.path.getsize(content.video_path)

            init_response = httpx.post(
                "https://www.googleapis.com/upload/youtube/v3/videos",
                params={
                    "uploadType": "resumable",
                    "part": "snippet,status",
                },
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                    "X-Upload-Content-Length": str(file_size),
                    "X-Upload-Content-Type": "video/*",
                },
                json=metadata,
                timeout=30,
            )

            if init_response.status_code != 200:
                return PublishResult(
                    status=PublishStatus.FAILED,
                    platform=self.platform_name,
                    error=f"Init failed: {init_response.text}",
                )

            upload_url = init_response.headers.get("Location")

            with open(content.video_path, "rb") as f:
                upload_response = httpx.put(
                    upload_url,
                    content=f.read(),
                    headers={
                        "Content-Type": "video/*",
                        "Content-Length": str(file_size),
                    },
                    timeout=600,
                )

            if upload_response.status_code in [200, 201]:
                data = upload_response.json()
                video_id = data.get("id")
                return PublishResult(
                    status=PublishStatus.SCHEDULED,
                    platform=self.platform_name,
                    post_id=video_id,
                    post_url=f"https://youtube.com/shorts/{video_id}",
                    scheduled_at=publish_at,
                    extra_data=data,
                )
            else:
                return PublishResult(
                    status=PublishStatus.FAILED,
                    platform=self.platform_name,
                    error=f"Upload failed: {upload_response.text}",
                )

        except Exception as e:
            return PublishResult(
                status=PublishStatus.FAILED,
                platform=self.platform_name,
                error=str(e),
            )

    def validate_content(self, content: ContentToPublish) -> tuple[bool, str]:
        """Valida conteudo para YouTube Shorts."""
        valid, error = super().validate_content(content)
        if not valid:
            return valid, error

        file_size = os.path.getsize(content.video_path)

        # YouTube: max 256 GB (mas Shorts sao curtos)
        if file_size > 256 * 1024 * 1024 * 1024:
            return False, "Video muito grande (max 256 GB)"

        # Titulo: max 100 chars
        title = content.title or content.caption[:100]
        if len(title) > 100:
            return False, f"Titulo muito longo ({len(title)}/100)"

        # Descricao: max 5000 chars
        description = content.description or content.get_full_caption()
        if len(description) > 5000:
            return False, f"Descricao muito longa ({len(description)}/5000)"

        return True, ""

    def _get_publish_instructions(self) -> str:
        """Instrucoes para publicacao manual no YouTube."""
        return """
1. Acesse https://studio.youtube.com
2. Clique em "CRIAR" > "Enviar videos"
3. Arraste o video ou clique para selecionar
4. Preencha o titulo (copie de youtube_metadata.txt)
5. Preencha a descricao
6. Adicione as tags
7. IMPORTANTE: Para Shorts, o video deve ter:
   - Duracao < 60 segundos
   - Formato vertical (9:16)
   - #Shorts no titulo ou descricao
8. Configure visibilidade (Publico/Privado/Nao listado)
9. Clique em "PUBLICAR" ou agende

DICA: Melhores horarios para YouTube Shorts:
- Seg-Sex: 12h-15h e 19h-21h
- Fim de semana: 10h-12h
"""


# Factory function
def get_youtube_publisher() -> YouTubePublisher:
    """Retorna instancia do YouTubePublisher."""
    return YouTubePublisher()
