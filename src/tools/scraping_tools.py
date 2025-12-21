"""Tools para scraping de videos do Instagram usando Apify."""

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from apify_client import ApifyClient

from config.settings import get_settings

settings = get_settings()


@dataclass
class ScrapedVideo:
    """Video coletado do Instagram."""

    platform_id: str
    shortcode: str
    source_url: str
    video_url: str
    thumbnail_url: Optional[str]

    # Metricas
    views_count: int
    likes_count: int
    comments_count: int
    shares_count: int

    # Conteudo
    caption: Optional[str]
    hashtags: list[str]
    mentions: list[str]
    first_comment: Optional[str]

    # Metadados
    duration_seconds: Optional[int]
    posted_at: Optional[datetime]
    owner_username: str
    owner_id: str


@dataclass
class ScrapingResult:
    """Resultado de uma operacao de scraping."""

    videos: list[ScrapedVideo]
    total_collected: int
    profile_username: str
    cost_usd: float
    duration_seconds: float


class ScrapingTools:
    """Gerenciador de scraping usando Apify Instagram Scraper."""

    ACTOR_ID = "apify/instagram-scraper"
    COST_PER_1000 = Decimal("2.30")  # $2.30 por 1000 resultados

    def __init__(self):
        """Inicializa cliente Apify."""
        if not settings.apify_token:
            raise RuntimeError("APIFY_TOKEN nao configurado")
        self.client = ApifyClient(settings.apify_token)

    def scrape_profile_videos(
        self,
        username: str,
        max_videos: int = 50,
        min_views: Optional[int] = None,
        min_likes: Optional[int] = None,
    ) -> ScrapingResult:
        """Coleta videos de um perfil do Instagram.

        Args:
            username: Username do perfil (sem @)
            max_videos: Maximo de videos a coletar
            min_views: Filtro minimo de views
            min_likes: Filtro minimo de likes

        Returns:
            ScrapingResult com videos coletados
        """
        min_views = min_views or settings.min_views_threshold
        min_likes = min_likes or settings.min_likes_threshold

        start_time = datetime.now()

        # Configura input do actor
        run_input = {
            "directUrls": [f"https://www.instagram.com/{username}/"],
            "resultsType": "posts",
            "resultsLimit": max_videos,
            "searchType": "user",
            "searchLimit": 1,
            "addParentData": True,
        }

        # Executa actor
        run = self.client.actor(self.ACTOR_ID).call(run_input=run_input)

        # Coleta resultados
        videos = []
        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            # Filtra apenas videos (Reels)
            if item.get("type") not in ["Video", "Reel", "video"]:
                continue

            # Extrai dados
            video = self._parse_video_item(item, username)
            if video is None:
                continue

            # Aplica filtros
            if video.views_count < min_views:
                continue
            if video.likes_count < min_likes:
                continue

            videos.append(video)

        # Calcula metricas
        duration = (datetime.now() - start_time).total_seconds()
        cost = self._calculate_cost(len(videos))

        return ScrapingResult(
            videos=videos,
            total_collected=len(videos),
            profile_username=username,
            cost_usd=cost,
            duration_seconds=duration,
        )

    def scrape_hashtag_videos(
        self,
        hashtag: str,
        max_videos: int = 50,
        min_views: Optional[int] = None,
    ) -> ScrapingResult:
        """Coleta videos de uma hashtag.

        Args:
            hashtag: Hashtag (sem #)
            max_videos: Maximo de videos
            min_views: Filtro minimo de views

        Returns:
            ScrapingResult
        """
        min_views = min_views or settings.min_views_threshold
        start_time = datetime.now()

        run_input = {
            "directUrls": [f"https://www.instagram.com/explore/tags/{hashtag}/"],
            "resultsType": "posts",
            "resultsLimit": max_videos,
            "searchType": "hashtag",
        }

        run = self.client.actor(self.ACTOR_ID).call(run_input=run_input)

        videos = []
        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            if item.get("type") not in ["Video", "Reel", "video"]:
                continue

            video = self._parse_video_item(item, hashtag)
            if video is None:
                continue

            if video.views_count < min_views:
                continue

            videos.append(video)

        duration = (datetime.now() - start_time).total_seconds()
        cost = self._calculate_cost(len(videos))

        return ScrapingResult(
            videos=videos,
            total_collected=len(videos),
            profile_username=f"#{hashtag}",
            cost_usd=cost,
            duration_seconds=duration,
        )

    def _parse_video_item(self, item: dict, source: str) -> Optional[ScrapedVideo]:
        """Parseia item do Apify para ScrapedVideo."""
        try:
            # ID unico
            platform_id = item.get("id") or item.get("pk")
            if not platform_id:
                platform_id = hashlib.md5(item.get("url", "").encode()).hexdigest()

            shortcode = item.get("shortCode") or item.get("shortcode", "")

            # URLs
            source_url = item.get("url") or f"https://www.instagram.com/p/{shortcode}/"
            video_url = item.get("videoUrl") or item.get("video_url", "")

            if not video_url:
                return None

            # Metricas
            views = item.get("videoViewCount") or item.get("video_view_count") or 0
            likes = item.get("likesCount") or item.get("likes_count") or 0
            comments = item.get("commentsCount") or item.get("comments_count") or 0

            # Caption e hashtags
            caption = item.get("caption") or ""
            hashtags = self._extract_hashtags(caption)
            mentions = self._extract_mentions(caption)

            # Owner
            owner = item.get("ownerUsername") or item.get("owner_username") or source
            owner_id = item.get("ownerId") or item.get("owner_id") or ""

            # Data de postagem
            posted_at = None
            timestamp = item.get("timestamp") or item.get("taken_at_timestamp")
            if timestamp:
                if isinstance(timestamp, int):
                    posted_at = datetime.fromtimestamp(timestamp)
                elif isinstance(timestamp, str):
                    try:
                        posted_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    except ValueError:
                        pass

            # Duracao
            duration = item.get("videoDuration") or item.get("video_duration")

            return ScrapedVideo(
                platform_id=str(platform_id),
                shortcode=shortcode,
                source_url=source_url,
                video_url=video_url,
                thumbnail_url=item.get("displayUrl") or item.get("thumbnail_url"),
                views_count=int(views),
                likes_count=int(likes),
                comments_count=int(comments),
                shares_count=0,  # Instagram nao expoe shares
                caption=caption,
                hashtags=hashtags,
                mentions=mentions,
                first_comment=None,  # Precisaria de request extra
                duration_seconds=int(duration) if duration else None,
                posted_at=posted_at,
                owner_username=owner,
                owner_id=str(owner_id),
            )
        except Exception as e:
            print(f"[Scraping] Erro ao parsear item: {e}")
            return None

    def _extract_hashtags(self, text: str) -> list[str]:
        """Extrai hashtags do texto."""
        if not text:
            return []
        pattern = r"#(\w+)"
        return re.findall(pattern, text)

    def _extract_mentions(self, text: str) -> list[str]:
        """Extrai mentions do texto."""
        if not text:
            return []
        pattern = r"@(\w+)"
        return re.findall(pattern, text)

    def _calculate_cost(self, results_count: int) -> float:
        """Calcula custo do scraping."""
        return float(self.COST_PER_1000 * results_count / 1000)

    def download_video(self, video_url: str, output_path: str) -> bool:
        """Download de video do Instagram.

        Args:
            video_url: URL do video
            output_path: Caminho local de saida

        Returns:
            True se sucesso
        """
        import httpx
        from pathlib import Path

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            with httpx.Client(follow_redirects=True, timeout=60) as client:
                response = client.get(video_url, headers=headers)
                response.raise_for_status()

                output = Path(output_path)
                output.parent.mkdir(parents=True, exist_ok=True)

                with open(output, "wb") as f:
                    f.write(response.content)

            return True
        except Exception as e:
            print(f"[Scraping] Erro ao baixar video: {e}")
            return False

    def estimate_cost(self, num_profiles: int, videos_per_profile: int = 50) -> float:
        """Estima custo de uma operacao de scraping.

        Args:
            num_profiles: Numero de perfis a scrapear
            videos_per_profile: Videos por perfil

        Returns:
            Custo estimado em USD
        """
        total_videos = num_profiles * videos_per_profile
        return self._calculate_cost(total_videos)


# Singleton para uso global
scraping_tools = ScrapingTools()
