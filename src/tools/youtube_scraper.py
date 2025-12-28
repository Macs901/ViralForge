"""Scraper completo do YouTube - Shorts, Videos, Channels."""

import hashlib
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from config.settings import get_settings

settings = get_settings()


@dataclass
class YouTubeChannel:
    """Canal do YouTube."""
    channel_id: str
    username: Optional[str] = None
    title: str = ""
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    banner_url: Optional[str] = None

    # Contadores
    subscriber_count: int = 0
    video_count: int = 0
    view_count: int = 0

    # Status
    is_verified: bool = False

    # Metricas calculadas
    avg_views: Optional[float] = None
    avg_likes: Optional[float] = None
    engagement_rate: Optional[float] = None


@dataclass
class YouTubeVideo:
    """Video/Short do YouTube."""
    video_id: str
    channel_id: str
    channel_title: str

    # URLs
    video_url: str
    thumbnail_url: Optional[str] = None

    # Conteudo
    title: str = ""
    description: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)

    # Tipo
    is_short: bool = False

    # Metricas
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0

    # Metadados
    duration_seconds: Optional[int] = None
    published_at: Optional[datetime] = None

    # Categorias
    category_id: Optional[str] = None
    category_name: Optional[str] = None


@dataclass
class YouTubeScrapingResult:
    """Resultado de scraping do YouTube."""
    channel: Optional[YouTubeChannel] = None
    videos: list[YouTubeVideo] = field(default_factory=list)
    shorts: list[YouTubeVideo] = field(default_factory=list)

    total_videos: int = 0
    total_shorts: int = 0
    duration_seconds: float = 0.0


class YouTubeScraper:
    """Scraper do YouTube usando yt-dlp e YouTube Data API."""

    YOUTUBE_CATEGORIES = {
        "1": "Film & Animation",
        "2": "Autos & Vehicles",
        "10": "Music",
        "15": "Pets & Animals",
        "17": "Sports",
        "19": "Travel & Events",
        "20": "Gaming",
        "22": "People & Blogs",
        "23": "Comedy",
        "24": "Entertainment",
        "25": "News & Politics",
        "26": "Howto & Style",
        "27": "Education",
        "28": "Science & Technology",
        "29": "Nonprofits & Activism",
    }

    def __init__(self):
        """Inicializa o scraper."""
        self.download_dir = Path(settings.video_output_dir) / "youtube"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = getattr(settings, 'youtube_api_key', None)

    def scrape_channel(self, channel_id: str) -> YouTubeChannel:
        """Coleta dados de um canal usando yt-dlp.

        Args:
            channel_id: ID do canal ou @username

        Returns:
            YouTubeChannel
        """
        try:
            # Usa yt-dlp para extrair info do canal
            if channel_id.startswith("@"):
                url = f"https://www.youtube.com/{channel_id}"
            else:
                url = f"https://www.youtube.com/channel/{channel_id}"

            result = subprocess.run(
                [
                    "yt-dlp",
                    url,
                    "--dump-json",
                    "--flat-playlist",
                    "--playlist-items", "0",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                raise ValueError(f"yt-dlp error: {result.stderr}")

            import json
            data = json.loads(result.stdout.split('\n')[0])

            return YouTubeChannel(
                channel_id=data.get("channel_id", channel_id),
                username=data.get("uploader_id"),
                title=data.get("channel", "") or data.get("uploader", ""),
                description=data.get("description"),
                thumbnail_url=data.get("thumbnail"),
                subscriber_count=data.get("channel_follower_count", 0),
            )
        except Exception as e:
            print(f"[YouTube] Erro ao coletar canal: {e}")
            raise

    def scrape_shorts(
        self,
        channel_id: str,
        max_shorts: int = 50,
        min_views: int = 0,
    ) -> list[YouTubeVideo]:
        """Coleta Shorts de um canal.

        Args:
            channel_id: ID do canal ou @username
            max_shorts: Maximo de shorts
            min_views: Filtro minimo de views

        Returns:
            Lista de YouTubeVideo (apenas shorts)
        """
        try:
            # Constroi URL dos Shorts do canal
            if channel_id.startswith("@"):
                url = f"https://www.youtube.com/{channel_id}/shorts"
            else:
                url = f"https://www.youtube.com/channel/{channel_id}/shorts"

            result = subprocess.run(
                [
                    "yt-dlp",
                    url,
                    "--dump-json",
                    "--flat-playlist",
                    "--playlist-items", f"1:{max_shorts}",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                raise ValueError(f"yt-dlp error: {result.stderr}")

            import json
            shorts = []

            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    short = self._parse_video(data, is_short=True)
                    if short and short.view_count >= min_views:
                        shorts.append(short)
                except json.JSONDecodeError:
                    continue

            return shorts
        except Exception as e:
            print(f"[YouTube] Erro ao coletar shorts: {e}")
            return []

    def scrape_videos(
        self,
        channel_id: str,
        max_videos: int = 50,
        min_views: int = 0,
    ) -> list[YouTubeVideo]:
        """Coleta videos de um canal.

        Args:
            channel_id: ID do canal ou @username
            max_videos: Maximo de videos
            min_views: Filtro minimo de views

        Returns:
            Lista de YouTubeVideo
        """
        try:
            if channel_id.startswith("@"):
                url = f"https://www.youtube.com/{channel_id}/videos"
            else:
                url = f"https://www.youtube.com/channel/{channel_id}/videos"

            result = subprocess.run(
                [
                    "yt-dlp",
                    url,
                    "--dump-json",
                    "--flat-playlist",
                    "--playlist-items", f"1:{max_videos}",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                raise ValueError(f"yt-dlp error: {result.stderr}")

            import json
            videos = []

            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    video = self._parse_video(data, is_short=False)
                    if video and video.view_count >= min_views:
                        # Filtra shorts (duracao < 60s)
                        if video.duration_seconds and video.duration_seconds < 60:
                            video.is_short = True
                        videos.append(video)
                except json.JSONDecodeError:
                    continue

            return videos
        except Exception as e:
            print(f"[YouTube] Erro ao coletar videos: {e}")
            return []

    def _parse_video(self, data: dict, is_short: bool = False) -> Optional[YouTubeVideo]:
        """Parseia dados de um video."""
        try:
            video_id = data.get("id") or data.get("url", "").split("v=")[-1][:11]
            if not video_id:
                return None

            description = data.get("description", "") or ""
            title = data.get("title", "")

            published_at = None
            if data.get("upload_date"):
                try:
                    published_at = datetime.strptime(data["upload_date"], "%Y%m%d")
                except:
                    pass

            return YouTubeVideo(
                video_id=video_id,
                channel_id=data.get("channel_id", ""),
                channel_title=data.get("channel", "") or data.get("uploader", ""),
                video_url=f"https://www.youtube.com/watch?v={video_id}",
                thumbnail_url=data.get("thumbnail"),
                title=title,
                description=description[:500] if description else None,
                tags=data.get("tags", []) or [],
                hashtags=self._extract_hashtags(description + " " + title),
                is_short=is_short or (data.get("duration", 0) < 60),
                view_count=data.get("view_count", 0),
                like_count=data.get("like_count", 0),
                comment_count=data.get("comment_count", 0),
                duration_seconds=data.get("duration"),
                published_at=published_at,
                category_id=data.get("category_id"),
                category_name=self.YOUTUBE_CATEGORIES.get(str(data.get("category_id", ""))),
            )
        except Exception as e:
            print(f"[YouTube] Erro ao parsear video: {e}")
            return None

    def scrape_trending_shorts(self, country: str = "BR", limit: int = 50) -> list[YouTubeVideo]:
        """Coleta Shorts trending.

        Args:
            country: Codigo do pais
            limit: Maximo de shorts

        Returns:
            Lista de YouTubeVideo
        """
        try:
            url = f"https://www.youtube.com/feed/trending?bp=4gIKGgJ7cg%3D%3D"  # Shorts trending

            result = subprocess.run(
                [
                    "yt-dlp",
                    url,
                    "--dump-json",
                    "--flat-playlist",
                    "--playlist-items", f"1:{limit}",
                    "--geo-bypass-country", country,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                raise ValueError(f"yt-dlp error: {result.stderr}")

            import json
            shorts = []

            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    short = self._parse_video(data, is_short=True)
                    if short:
                        shorts.append(short)
                except json.JSONDecodeError:
                    continue

            return shorts
        except Exception as e:
            print(f"[YouTube] Erro ao coletar trending: {e}")
            return []

    def scrape_search(
        self,
        query: str,
        max_results: int = 50,
        shorts_only: bool = False,
    ) -> list[YouTubeVideo]:
        """Busca videos por query.

        Args:
            query: Termo de busca
            max_results: Maximo de resultados
            shorts_only: Apenas Shorts

        Returns:
            Lista de YouTubeVideo
        """
        try:
            search_url = f"ytsearch{max_results}:{query}"
            if shorts_only:
                search_url = f"ytsearch{max_results}:{query} #shorts"

            result = subprocess.run(
                [
                    "yt-dlp",
                    search_url,
                    "--dump-json",
                    "--flat-playlist",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                raise ValueError(f"yt-dlp error: {result.stderr}")

            import json
            videos = []

            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    video = self._parse_video(data, is_short=shorts_only)
                    if video:
                        videos.append(video)
                except json.JSONDecodeError:
                    continue

            return videos
        except Exception as e:
            print(f"[YouTube] Erro na busca: {e}")
            return []

    def scrape_full_channel(
        self,
        channel_id: str,
        max_videos: int = 50,
        max_shorts: int = 50,
    ) -> YouTubeScrapingResult:
        """Coleta tudo de um canal.

        Args:
            channel_id: ID do canal ou @username
            max_videos: Maximo de videos
            max_shorts: Maximo de shorts

        Returns:
            YouTubeScrapingResult
        """
        start_time = datetime.now()
        result = YouTubeScrapingResult()

        # 1. Canal
        print(f"[YouTube] Coletando canal {channel_id}...")
        try:
            result.channel = self.scrape_channel(channel_id)
        except Exception as e:
            print(f"[YouTube] Erro ao coletar canal: {e}")

        # 2. Shorts
        print(f"[YouTube] Coletando shorts...")
        try:
            result.shorts = self.scrape_shorts(channel_id, max_shorts)
            result.total_shorts = len(result.shorts)
        except Exception as e:
            print(f"[YouTube] Erro ao coletar shorts: {e}")

        # 3. Videos
        print(f"[YouTube] Coletando videos...")
        try:
            result.videos = self.scrape_videos(channel_id, max_videos)
            result.total_videos = len(result.videos)
        except Exception as e:
            print(f"[YouTube] Erro ao coletar videos: {e}")

        result.duration_seconds = (datetime.now() - start_time).total_seconds()

        print(f"[YouTube] Scraping completo!")
        print(f"  - Canal: {'OK' if result.channel else 'ERRO'}")
        print(f"  - Videos: {result.total_videos}")
        print(f"  - Shorts: {result.total_shorts}")

        return result

    def download_video(self, video_url: str, creator: str) -> Optional[Path]:
        """Baixa video do YouTube.

        Args:
            video_url: URL do video
            creator: Nome do criador

        Returns:
            Path do arquivo baixado
        """
        creator_dir = self.download_dir / creator
        creator_dir.mkdir(parents=True, exist_ok=True)

        try:
            url_hash = hashlib.md5(video_url.encode()).hexdigest()[:8]
            output_template = str(creator_dir / f"%(title)s_{url_hash}.%(ext)s")

            result = subprocess.run(
                [
                    "yt-dlp",
                    video_url,
                    "-o", output_template,
                    "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                    "--no-playlist",
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode != 0:
                raise ValueError(f"yt-dlp error: {result.stderr}")

            video_files = sorted(
                creator_dir.glob("*.mp4"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if video_files:
                return video_files[0]

            return None
        except Exception as e:
            print(f"[YouTube] Erro ao baixar video: {e}")
            return None

    def _extract_hashtags(self, text: str) -> list[str]:
        """Extrai hashtags do texto."""
        if not text:
            return []
        return re.findall(r"#(\w+)", text)


# Singleton
youtube_scraper = YouTubeScraper()
