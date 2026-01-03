"""Scraper completo do TikTok - Perfis, Videos, Trending."""

import hashlib
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from apify_client import ApifyClient

from config.settings import get_settings

settings = get_settings()


@dataclass
class TikTokProfile:
    """Perfil completo do TikTok."""
    user_id: str
    username: str
    nickname: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None

    # Contadores
    follower_count: int = 0
    following_count: int = 0
    likes_count: int = 0  # Total de likes recebidos
    video_count: int = 0

    # Status
    is_verified: bool = False
    is_private: bool = False

    # Metricas calculadas
    avg_views: Optional[float] = None
    avg_likes: Optional[float] = None
    avg_comments: Optional[float] = None
    engagement_rate: Optional[float] = None


@dataclass
class TikTokVideo:
    """Video do TikTok."""
    video_id: str
    author_username: str

    # URLs
    video_url: str
    share_url: str
    thumbnail_url: Optional[str] = None

    # Conteudo
    description: Optional[str] = None
    hashtags: list[str] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)

    # Metricas
    views_count: int = 0
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    saves_count: int = 0

    # Audio
    music_id: Optional[str] = None
    music_title: Optional[str] = None
    music_author: Optional[str] = None
    is_original_sound: bool = False

    # Metadados
    duration_seconds: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None

    # Timestamps
    created_at: Optional[datetime] = None


@dataclass
class TikTokSound:
    """Som/musica do TikTok."""
    sound_id: str
    title: Optional[str] = None
    author: Optional[str] = None
    duration_seconds: Optional[int] = None
    cover_url: Optional[str] = None
    video_count: int = 0  # Quantos videos usam
    is_original: bool = False
    is_trending: bool = False


@dataclass
class TikTokHashtag:
    """Hashtag do TikTok."""
    hashtag_id: str
    name: str
    video_count: int = 0
    view_count: int = 0
    is_trending: bool = False


@dataclass
class TikTokScrapingResult:
    """Resultado de scraping do TikTok."""
    profile: Optional[TikTokProfile] = None
    videos: list[TikTokVideo] = field(default_factory=list)
    sounds: list[TikTokSound] = field(default_factory=list)
    hashtags: list[TikTokHashtag] = field(default_factory=list)

    total_videos: int = 0
    cost_usd: float = 0.0
    duration_seconds: float = 0.0


class TikTokScraper:
    """Scraper completo do TikTok."""

    # Apify Actors
    PROFILE_SCRAPER = "clockworks/tiktok-scraper"
    VIDEO_SCRAPER = "clockworks/tiktok-scraper"
    HASHTAG_SCRAPER = "clockworks/tiktok-hashtag-scraper"

    COST_PER_1000 = Decimal("2.50")

    def __init__(self):
        """Inicializa cliente Apify."""
        if not settings.apify_token:
            raise RuntimeError("APIFY_TOKEN nao configurado")
        self.client = ApifyClient(settings.apify_token)
        self.download_dir = Path(settings.video_output_dir) / "tiktok"
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def scrape_profile(self, username: str) -> TikTokProfile:
        """Coleta dados completos de um perfil.

        Args:
            username: Username sem @

        Returns:
            TikTokProfile
        """
        run_input = {
            "profiles": [username],
            "resultsPerPage": 1,
            "shouldDownloadVideos": False,
        }

        run = self.client.actor(self.PROFILE_SCRAPER).call(run_input=run_input)

        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            if item.get("authorMeta"):
                author = item["authorMeta"]
                return TikTokProfile(
                    user_id=str(author.get("id", "")),
                    username=author.get("name", username),
                    nickname=author.get("nickName"),
                    bio=author.get("signature"),
                    avatar_url=author.get("avatar"),
                    follower_count=author.get("fans", 0),
                    following_count=author.get("following", 0),
                    likes_count=author.get("heart", 0),
                    video_count=author.get("video", 0),
                    is_verified=author.get("verified", False),
                    is_private=author.get("privateAccount", False),
                )

        raise ValueError(f"Perfil @{username} nao encontrado")

    def scrape_videos(
        self,
        username: str,
        max_videos: int = 50,
        min_views: int = 0,
    ) -> list[TikTokVideo]:
        """Coleta videos de um perfil.

        Args:
            username: Username sem @
            max_videos: Maximo de videos
            min_views: Filtro minimo de views

        Returns:
            Lista de TikTokVideo
        """
        run_input = {
            "profiles": [username],
            "resultsPerPage": max_videos,
            "shouldDownloadVideos": False,
        }

        run = self.client.actor(self.VIDEO_SCRAPER).call(run_input=run_input)

        videos = []
        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            video = self._parse_video(item)
            if video and video.views_count >= min_views:
                videos.append(video)

        return videos

    def _parse_video(self, item: dict) -> Optional[TikTokVideo]:
        """Parseia dados de um video."""
        try:
            video_id = item.get("id") or item.get("videoId")
            if not video_id:
                return None

            author = item.get("authorMeta", {})
            music = item.get("musicMeta", {})
            stats = item.get("stats", {}) or item.get("statsV2", {})

            description = item.get("text", "") or item.get("desc", "")

            created_at = None
            if item.get("createTime"):
                created_at = datetime.fromtimestamp(item["createTime"])

            return TikTokVideo(
                video_id=str(video_id),
                author_username=author.get("name", ""),
                video_url=item.get("videoUrl", ""),
                share_url=item.get("webVideoUrl", "") or f"https://www.tiktok.com/@{author.get('name')}/video/{video_id}",
                thumbnail_url=item.get("covers", {}).get("default") or item.get("cover"),
                description=description,
                hashtags=self._extract_hashtags(description),
                mentions=self._extract_mentions(description),
                views_count=stats.get("playCount", 0) or stats.get("plays", 0),
                likes_count=stats.get("diggCount", 0) or stats.get("likes", 0),
                comments_count=stats.get("commentCount", 0) or stats.get("comments", 0),
                shares_count=stats.get("shareCount", 0) or stats.get("shares", 0),
                saves_count=stats.get("collectCount", 0) or stats.get("saves", 0),
                music_id=str(music.get("musicId", "")),
                music_title=music.get("musicName"),
                music_author=music.get("musicAuthor"),
                is_original_sound=music.get("musicOriginal", False),
                duration_seconds=item.get("videoMeta", {}).get("duration"),
                width=item.get("videoMeta", {}).get("width"),
                height=item.get("videoMeta", {}).get("height"),
                created_at=created_at,
            )
        except Exception as e:
            print(f"[TikTok] Erro ao parsear video: {e}")
            return None

    def scrape_hashtag(
        self,
        hashtag: str,
        max_videos: int = 100,
    ) -> TikTokScrapingResult:
        """Coleta videos de uma hashtag.

        Args:
            hashtag: Hashtag sem #
            max_videos: Maximo de videos

        Returns:
            TikTokScrapingResult
        """
        start_time = datetime.now()

        run_input = {
            "hashtags": [hashtag],
            "resultsPerPage": max_videos,
            "shouldDownloadVideos": False,
        }

        run = self.client.actor(self.HASHTAG_SCRAPER).call(run_input=run_input)

        result = TikTokScrapingResult()

        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            video = self._parse_video(item)
            if video:
                result.videos.append(video)

        result.total_videos = len(result.videos)
        result.cost_usd = float(self.COST_PER_1000 * len(result.videos) / 1000)
        result.duration_seconds = (datetime.now() - start_time).total_seconds()

        return result

    def scrape_trending_sounds(self, limit: int = 50) -> list[TikTokSound]:
        """Coleta sons trending.

        Args:
            limit: Maximo de sons

        Returns:
            Lista de TikTokSound
        """
        # Scrape trending videos e extrai os sons
        run_input = {
            "hashtags": ["fyp", "foryou", "viral"],
            "resultsPerPage": limit * 2,  # Pega mais para filtrar duplicados
            "shouldDownloadVideos": False,
        }

        run = self.client.actor(self.HASHTAG_SCRAPER).call(run_input=run_input)

        sounds_map = {}
        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            music = item.get("musicMeta", {})
            music_id = str(music.get("musicId", ""))

            if music_id and music_id not in sounds_map:
                sounds_map[music_id] = TikTokSound(
                    sound_id=music_id,
                    title=music.get("musicName"),
                    author=music.get("musicAuthor"),
                    duration_seconds=music.get("duration"),
                    cover_url=music.get("coverMedium"),
                    is_original=music.get("musicOriginal", False),
                    is_trending=True,
                )
            elif music_id in sounds_map:
                sounds_map[music_id].video_count += 1

        # Ordena por quantidade de videos usando
        sounds = sorted(sounds_map.values(), key=lambda s: s.video_count, reverse=True)
        return sounds[:limit]

    def scrape_full_profile(
        self,
        username: str,
        max_videos: int = 50,
        include_sounds: bool = True,
    ) -> TikTokScrapingResult:
        """Coleta tudo de um perfil.

        Args:
            username: Username sem @
            max_videos: Maximo de videos
            include_sounds: Extrair sons dos videos

        Returns:
            TikTokScrapingResult
        """
        start_time = datetime.now()
        result = TikTokScrapingResult()

        # 1. Perfil
        print(f"[TikTok] Coletando perfil @{username}...")
        try:
            result.profile = self.scrape_profile(username)
        except Exception as e:
            print(f"[TikTok] Erro ao coletar perfil: {e}")

        # 2. Videos
        print(f"[TikTok] Coletando videos...")
        try:
            result.videos = self.scrape_videos(username, max_videos)
            result.total_videos = len(result.videos)
        except Exception as e:
            print(f"[TikTok] Erro ao coletar videos: {e}")

        # 3. Extrair sons unicos dos videos
        if include_sounds and result.videos:
            print(f"[TikTok] Extraindo sons...")
            sounds_map = {}
            for video in result.videos:
                if video.music_id and video.music_id not in sounds_map:
                    sounds_map[video.music_id] = TikTokSound(
                        sound_id=video.music_id,
                        title=video.music_title,
                        author=video.music_author,
                        is_original=video.is_original_sound,
                    )
                elif video.music_id in sounds_map:
                    sounds_map[video.music_id].video_count += 1

            result.sounds = list(sounds_map.values())

        # 4. Extrair hashtags unicos
        hashtags_count = {}
        for video in result.videos:
            for tag in video.hashtags:
                hashtags_count[tag] = hashtags_count.get(tag, 0) + 1

        result.hashtags = [
            TikTokHashtag(hashtag_id=tag, name=tag, video_count=count)
            for tag, count in sorted(hashtags_count.items(), key=lambda x: x[1], reverse=True)[:20]
        ]

        result.cost_usd = float(self.COST_PER_1000 * result.total_videos / 1000)
        result.duration_seconds = (datetime.now() - start_time).total_seconds()

        print(f"[TikTok] Scraping completo!")
        print(f"  - Perfil: {'OK' if result.profile else 'ERRO'}")
        print(f"  - Videos: {result.total_videos}")
        print(f"  - Sons: {len(result.sounds)}")
        print(f"  - Hashtags: {len(result.hashtags)}")

        return result

    def download_video(self, video_url: str, creator: str) -> Optional[Path]:
        """Baixa video do TikTok.

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
                    "--format", "bv+ba/best",
                    "--no-playlist",
                ],
                capture_output=True,
                text=True,
                timeout=300,
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
            print(f"[TikTok] Erro ao baixar video: {e}")
            return None

    def _extract_hashtags(self, text: str) -> list[str]:
        """Extrai hashtags do texto."""
        if not text:
            return []
        return re.findall(r"#(\w+)", text)

    def _extract_mentions(self, text: str) -> list[str]:
        """Extrai mentions do texto."""
        if not text:
            return []
        return re.findall(r"@(\w+)", text)

    def get_video_info(self, video_url: str) -> Optional[TikTokVideo]:
        """Coleta metricas atualizadas de um video especifico.

        Args:
            video_url: URL do video TikTok

        Returns:
            TikTokVideo com metricas atualizadas ou None
        """
        try:
            # Tenta extrair video ID da URL
            patterns = [
                r"tiktok\.com/@[\w.]+/video/(\d+)",
                r"tiktok\.com/t/(\w+)",
                r"vm\.tiktok\.com/(\w+)",
            ]

            video_id = None
            for pattern in patterns:
                match = re.search(pattern, video_url)
                if match:
                    video_id = match.group(1)
                    break

            # Primeiro tenta com yt-dlp (mais rapido e sem custo)
            try:
                import json
                result = subprocess.run(
                    [
                        "yt-dlp",
                        video_url,
                        "--dump-json",
                        "--no-download",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    return TikTokVideo(
                        video_id=str(data.get("id", video_id or "")),
                        author_username=data.get("uploader_id", ""),
                        video_url=data.get("url", video_url),
                        share_url=video_url,
                        thumbnail_url=data.get("thumbnail"),
                        description=data.get("description", ""),
                        views_count=data.get("view_count", 0),
                        likes_count=data.get("like_count", 0),
                        comments_count=data.get("comment_count", 0),
                        shares_count=data.get("repost_count", 0),
                        duration_seconds=data.get("duration"),
                    )
            except Exception as e:
                print(f"[TikTok] yt-dlp falhou, tentando Apify: {e}")

            # Fallback para Apify
            run_input = {
                "postURLs": [video_url],
                "resultsPerPage": 1,
                "shouldDownloadVideos": False,
            }

            run = self.client.actor(self.VIDEO_SCRAPER).call(run_input=run_input)

            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                return self._parse_video(item)

            return None

        except Exception as e:
            print(f"[TikTok] Erro ao coletar info do video: {e}")
            return None

    def estimate_cost(self, profiles: int, videos_per_profile: int = 50) -> dict:
        """Estima custo de scraping."""
        total_videos = profiles * videos_per_profile
        return {
            "profiles": float(self.COST_PER_1000 * profiles / 1000),
            "videos": float(self.COST_PER_1000 * total_videos / 1000),
            "total": float(self.COST_PER_1000 * (profiles + total_videos) / 1000),
        }


# Singleton
tiktok_scraper = TikTokScraper()
