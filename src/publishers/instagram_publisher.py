"""Instagram Publisher - Publicacao no Instagram."""

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


class InstagramPublisher(BasePublisher):
    """Publisher para Instagram Reels.

    Suporta:
    - Publicacao via Instagram Graph API (requer Business Account)
    - Exportacao para publicacao manual
    - Integracao com ferramentas de terceiros (webhooks)

    Requisitos para API:
    - Instagram Business ou Creator Account
    - Facebook Page vinculada
    - Access Token com permissoes de publish
    """

    def __init__(self):
        """Inicializa o publisher."""
        super().__init__()
        self.platform_name = "instagram"

        # Credenciais
        self.access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.account_id = os.getenv("INSTAGRAM_ACCOUNT_ID")

        # Webhook para integracao externa
        self.webhook_url = os.getenv("INSTAGRAM_PUBLISH_WEBHOOK")

    def authenticate(self) -> bool:
        """Verifica autenticacao com Instagram Graph API."""
        if not self.access_token or not self.account_id:
            print("[InstagramPublisher] Credenciais nao configuradas")
            self._authenticated = False
            return False

        try:
            import httpx

            # Valida token
            response = httpx.get(
                f"https://graph.facebook.com/v18.0/{self.account_id}",
                params={
                    "fields": "username,followers_count",
                    "access_token": self.access_token,
                },
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                print(f"[InstagramPublisher] Autenticado como @{data.get('username')}")
                self._authenticated = True
                return True
            else:
                print(f"[InstagramPublisher] Erro de autenticacao: {response.text}")
                self._authenticated = False
                return False

        except Exception as e:
            print(f"[InstagramPublisher] Erro: {e}")
            self._authenticated = False
            return False

    def publish(self, content: ContentToPublish) -> PublishResult:
        """Publica um Reel no Instagram.

        Fluxo da API:
        1. Upload do video para container
        2. Aguarda processamento
        3. Publica o container
        """
        # Valida conteudo
        valid, error = self.validate_content(content)
        if not valid:
            return PublishResult(
                status=PublishStatus.FAILED,
                platform=self.platform_name,
                error=error,
            )

        # Se nao tem API, tenta webhook
        if self.webhook_url:
            return self._publish_via_webhook(content)

        # Se nao tem API nem webhook, exporta
        if not self._authenticated:
            return self._export_for_manual_publish(content)

        # Publicacao via API
        try:
            return self._publish_via_api(content)
        except Exception as e:
            return PublishResult(
                status=PublishStatus.FAILED,
                platform=self.platform_name,
                error=str(e),
            )

    def _publish_via_api(self, content: ContentToPublish) -> PublishResult:
        """Publica via Instagram Graph API."""
        import httpx
        import time

        # Step 1: Cria container
        # Nota: Para Reels, o video precisa estar em URL publica
        # Por isso, primeiro fazemos upload para um storage

        video_url = self._upload_to_temp_storage(content.video_path)
        if not video_url:
            return PublishResult(
                status=PublishStatus.FAILED,
                platform=self.platform_name,
                error="Falha no upload do video para storage temporario",
            )

        try:
            # Cria container
            response = httpx.post(
                f"https://graph.facebook.com/v18.0/{self.account_id}/media",
                data={
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": content.get_full_caption(2200),
                    "share_to_feed": "true",
                    "access_token": self.access_token,
                },
                timeout=60,
            )

            if response.status_code != 200:
                return PublishResult(
                    status=PublishStatus.FAILED,
                    platform=self.platform_name,
                    error=f"Erro ao criar container: {response.text}",
                )

            container_id = response.json().get("id")
            print(f"[InstagramPublisher] Container criado: {container_id}")

            # Step 2: Aguarda processamento
            for _ in range(30):  # Max 5 minutos
                status_resp = httpx.get(
                    f"https://graph.facebook.com/v18.0/{container_id}",
                    params={
                        "fields": "status_code",
                        "access_token": self.access_token,
                    },
                    timeout=10,
                )

                status = status_resp.json().get("status_code")
                if status == "FINISHED":
                    break
                elif status == "ERROR":
                    return PublishResult(
                        status=PublishStatus.FAILED,
                        platform=self.platform_name,
                        error="Erro no processamento do video",
                    )

                time.sleep(10)

            # Step 3: Publica
            publish_resp = httpx.post(
                f"https://graph.facebook.com/v18.0/{self.account_id}/media_publish",
                data={
                    "creation_id": container_id,
                    "access_token": self.access_token,
                },
                timeout=60,
            )

            if publish_resp.status_code == 200:
                post_id = publish_resp.json().get("id")
                return PublishResult(
                    status=PublishStatus.PUBLISHED,
                    platform=self.platform_name,
                    post_id=post_id,
                    post_url=f"https://www.instagram.com/reel/{post_id}/",
                )
            else:
                return PublishResult(
                    status=PublishStatus.FAILED,
                    platform=self.platform_name,
                    error=f"Erro ao publicar: {publish_resp.text}",
                )

        except Exception as e:
            return PublishResult(
                status=PublishStatus.FAILED,
                platform=self.platform_name,
                error=str(e),
            )

    def _publish_via_webhook(self, content: ContentToPublish) -> PublishResult:
        """Publica via webhook externo (ex: Publer, Later)."""
        import httpx

        try:
            response = httpx.post(
                self.webhook_url,
                json={
                    "platform": "instagram",
                    "type": "reel",
                    "video_path": content.video_path,
                    "caption": content.get_full_caption(),
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
                "instructions": "Publique manualmente usando os arquivos exportados",
            },
        )

    def _upload_to_temp_storage(self, video_path: str) -> Optional[str]:
        """Upload para storage temporario (MinIO/S3)."""
        try:
            from src.tools.storage_tools import storage_tools

            # Upload para MinIO
            result = storage_tools.upload_file(video_path, "temp-videos")
            return result.get("public_url")

        except Exception as e:
            print(f"[InstagramPublisher] Erro no upload: {e}")
            return None

    def schedule(self, content: ContentToPublish, publish_at: datetime) -> PublishResult:
        """Agenda publicacao.

        Nota: Instagram Graph API nao suporta agendamento nativo.
        Usamos webhook ou exportamos para ferramentas externas.
        """
        content.scheduled_at = publish_at

        if self.webhook_url:
            return self._publish_via_webhook(content)

        # Exporta com instrucoes de agendamento
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
                "instructions": f"Publique em {publish_at.strftime('%d/%m/%Y %H:%M')}",
            },
        )

    def validate_content(self, content: ContentToPublish) -> tuple[bool, str]:
        """Valida conteudo para Instagram Reels."""
        valid, error = super().validate_content(content)
        if not valid:
            return valid, error

        # Limites do Instagram
        file_size = os.path.getsize(content.video_path)

        # Reels: max 1GB
        if file_size > 1024 * 1024 * 1024:
            return False, "Video muito grande para Reels (max 1GB)"

        # Caption: max 2200 chars
        full_caption = content.get_full_caption()
        if len(full_caption) > 2200:
            return False, f"Caption muito longa ({len(full_caption)}/2200 chars)"

        # Hashtags: max 30
        if len(content.hashtags) > 30:
            return False, f"Muitas hashtags ({len(content.hashtags)}/30)"

        return True, ""

    def _get_publish_instructions(self) -> str:
        """Instrucoes para publicacao manual no Instagram."""
        return """
1. Abra o app do Instagram no celular
2. Toque no + no centro inferior
3. Selecione "Reel"
4. Escolha o video da pasta de exportacao
5. Adicione efeitos/musica se desejar
6. Na tela de compartilhamento, cole a caption do arquivo caption.txt
7. Ajuste configuracoes (compartilhar no Feed, capa, etc)
8. Toque em "Compartilhar"

DICA: Para melhores resultados, poste nos horarios de pico:
- Seg-Sex: 12h-14h e 19h-21h
- Sabado: 10h-12h
- Domingo: 17h-19h
"""


# Factory function
def get_instagram_publisher() -> InstagramPublisher:
    """Retorna instancia do InstagramPublisher."""
    return InstagramPublisher()
