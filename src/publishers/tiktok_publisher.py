"""TikTok Publisher - Publicacao no TikTok."""

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


class TikTokPublisher(BasePublisher):
    """Publisher para TikTok.

    Suporta:
    - Publicacao via TikTok Content Posting API (beta)
    - Exportacao para publicacao manual
    - Integracao com ferramentas de terceiros (webhooks)

    Requisitos para API:
    - TikTok for Developers account
    - App aprovado para Content Posting API
    - Access Token valido
    """

    def __init__(self):
        """Inicializa o publisher."""
        super().__init__()
        self.platform_name = "tiktok"

        # Credenciais
        self.access_token = os.getenv("TIKTOK_ACCESS_TOKEN")
        self.open_id = os.getenv("TIKTOK_OPEN_ID")

        # Webhook para integracao externa
        self.webhook_url = os.getenv("TIKTOK_PUBLISH_WEBHOOK")

    def authenticate(self) -> bool:
        """Verifica autenticacao com TikTok API."""
        if not self.access_token:
            print("[TikTokPublisher] Credenciais nao configuradas")
            self._authenticated = False
            return False

        try:
            import httpx

            response = httpx.get(
                "https://open.tiktokapis.com/v2/user/info/",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                },
                params={
                    "fields": "open_id,display_name,avatar_url",
                },
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json().get("data", {}).get("user", {})
                print(f"[TikTokPublisher] Autenticado como {data.get('display_name')}")
                self._authenticated = True
                return True
            else:
                print(f"[TikTokPublisher] Erro: {response.text}")
                self._authenticated = False
                return False

        except Exception as e:
            print(f"[TikTokPublisher] Erro: {e}")
            self._authenticated = False
            return False

    def publish(self, content: ContentToPublish) -> PublishResult:
        """Publica video no TikTok."""
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
        if self._authenticated:
            return self._publish_via_api(content)

        # Exportacao manual
        return self._export_for_manual_publish(content)

    def _publish_via_api(self, content: ContentToPublish) -> PublishResult:
        """Publica via TikTok Content Posting API."""
        import httpx
        import time

        try:
            # Step 1: Inicia upload
            file_size = os.path.getsize(content.video_path)

            init_response = httpx.post(
                "https://open.tiktokapis.com/v2/post/publish/video/init/",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "post_info": {
                        "title": content.caption[:150],
                        "privacy_level": "PUBLIC_TO_EVERYONE",
                        "disable_duet": False,
                        "disable_comment": False,
                        "disable_stitch": False,
                    },
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": file_size,
                        "chunk_size": file_size,
                        "total_chunk_count": 1,
                    },
                },
                timeout=30,
            )

            if init_response.status_code != 200:
                return PublishResult(
                    status=PublishStatus.FAILED,
                    platform=self.platform_name,
                    error=f"Init failed: {init_response.text}",
                )

            data = init_response.json().get("data", {})
            publish_id = data.get("publish_id")
            upload_url = data.get("upload_url")

            # Step 2: Upload video
            with open(content.video_path, "rb") as f:
                upload_response = httpx.put(
                    upload_url,
                    content=f.read(),
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Range": f"bytes 0-{file_size-1}/{file_size}",
                    },
                    timeout=300,
                )

            if upload_response.status_code not in [200, 201]:
                return PublishResult(
                    status=PublishStatus.FAILED,
                    platform=self.platform_name,
                    error=f"Upload failed: {upload_response.text}",
                )

            # Step 3: Verifica status
            for _ in range(30):
                status_response = httpx.post(
                    "https://open.tiktokapis.com/v2/post/publish/status/fetch/",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json",
                    },
                    json={"publish_id": publish_id},
                    timeout=10,
                )

                status_data = status_response.json().get("data", {})
                status = status_data.get("status")

                if status == "PUBLISH_COMPLETE":
                    return PublishResult(
                        status=PublishStatus.PUBLISHED,
                        platform=self.platform_name,
                        post_id=publish_id,
                        extra_data=status_data,
                    )
                elif status in ["FAILED", "PUBLISH_FAILED"]:
                    return PublishResult(
                        status=PublishStatus.FAILED,
                        platform=self.platform_name,
                        error=status_data.get("fail_reason", "Unknown error"),
                    )

                time.sleep(10)

            return PublishResult(
                status=PublishStatus.PROCESSING,
                platform=self.platform_name,
                post_id=publish_id,
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
                    "platform": "tiktok",
                    "video_path": content.video_path,
                    "caption": content.get_full_caption(2200),
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
        """Agenda publicacao."""
        content.scheduled_at = publish_at

        if self.webhook_url:
            return self._publish_via_webhook(content)

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

    def validate_content(self, content: ContentToPublish) -> tuple[bool, str]:
        """Valida conteudo para TikTok."""
        valid, error = super().validate_content(content)
        if not valid:
            return valid, error

        file_size = os.path.getsize(content.video_path)

        # TikTok: max 287.6 MB via web, 72 min via app
        if file_size > 287.6 * 1024 * 1024:
            return False, "Video muito grande (max 287.6 MB)"

        # Caption: max 2200 chars
        full_caption = content.get_full_caption()
        if len(full_caption) > 2200:
            return False, f"Caption muito longa ({len(full_caption)}/2200)"

        return True, ""

    def _get_publish_instructions(self) -> str:
        """Instrucoes para publicacao manual no TikTok."""
        return """
1. Abra o app do TikTok no celular
2. Toque no + no centro inferior
3. Toque em "Carregar" e selecione o video
4. Edite o video se desejar (cortes, filtros, etc)
5. Toque em "Avancar"
6. Cole a caption do arquivo caption.txt
7. Adicione sons/efeitos se desejar
8. Configure privacidade e outras opcoes
9. Toque em "Publicar"

DICA: Melhores horarios para TikTok:
- Ter-Qui: 10h-12h e 19h-21h
- Sexta: 17h-19h
- Fim de semana: variavel
"""


# Factory function
def get_tiktok_publisher() -> TikTokPublisher:
    """Retorna instancia do TikTokPublisher."""
    return TikTokPublisher()
