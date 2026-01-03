"""Scraper completo do Instagram - Stories, Carroseis, Comentarios, Perfis."""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from apify_client import ApifyClient

from config.settings import get_settings

settings = get_settings()


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ScrapedProfile:
    """Perfil completo do Instagram."""
    instagram_id: str
    username: str
    full_name: Optional[str] = None
    biography: Optional[str] = None
    external_url: Optional[str] = None
    profile_pic_url: Optional[str] = None
    profile_pic_url_hd: Optional[str] = None

    # Contadores
    follower_count: int = 0
    following_count: int = 0
    media_count: int = 0
    igtv_count: int = 0
    reels_count: int = 0

    # Status
    is_private: bool = False
    is_verified: bool = False
    is_business: bool = False
    business_category: Optional[str] = None
    business_email: Optional[str] = None
    business_phone: Optional[str] = None

    # Metricas calculadas
    avg_likes: Optional[float] = None
    avg_comments: Optional[float] = None
    avg_views: Optional[float] = None
    engagement_rate: Optional[float] = None
    posting_frequency: Optional[float] = None

    # Analise
    top_hashtags: list[str] = field(default_factory=list)
    best_posting_times: list[str] = field(default_factory=list)


@dataclass
class ScrapedStory:
    """Story do Instagram."""
    story_id: str
    story_pk: Optional[str] = None
    owner_username: str = ""

    # Media
    media_type: str = "image"  # image, video
    is_video: bool = False
    media_url: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

    # Dimensoes
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None

    # Audio
    has_audio: bool = False
    has_music: bool = False
    music_info: Optional[dict] = None

    # Interacoes
    has_poll: bool = False
    has_question: bool = False
    has_quiz: bool = False
    has_countdown: bool = False
    has_link: bool = False
    link_url: Optional[str] = None
    stickers: list[dict] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)

    # Timestamps
    taken_at: Optional[datetime] = None
    expiring_at: Optional[datetime] = None


@dataclass
class CarouselSlide:
    """Slide individual de um carrossel."""
    index: int
    media_type: str  # image, video
    url: str
    thumbnail_url: Optional[str] = None
    is_video: bool = False
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None


@dataclass
class ScrapedCarousel:
    """Carrossel do Instagram."""
    carousel_id: str
    shortcode: str
    source_url: str
    owner_username: str

    # Metricas
    likes_count: int = 0
    comments_count: int = 0
    saves_count: int = 0
    shares_count: int = 0

    # Conteudo
    caption: Optional[str] = None
    hashtags: list[str] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)

    # Slides
    slides: list[CarouselSlide] = field(default_factory=list)

    # Timestamps
    posted_at: Optional[datetime] = None


@dataclass
class ScrapedComment:
    """Comentario do Instagram."""
    comment_id: str
    comment_pk: Optional[str] = None

    # Autor
    author_id: Optional[str] = None
    author_username: str = ""
    author_full_name: Optional[str] = None
    author_profile_pic: Optional[str] = None
    is_author_verified: bool = False

    # Conteudo
    text: str = ""
    mentions: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)

    # Metricas
    likes_count: int = 0
    replies_count: int = 0

    # Flags
    is_reply: bool = False
    is_pinned: bool = False
    is_from_creator: bool = False
    parent_comment_id: Optional[str] = None

    # Replies (nested)
    replies: list["ScrapedComment"] = field(default_factory=list)

    # Timestamps
    created_at: Optional[datetime] = None


@dataclass
class ScrapedAudio:
    """Audio/musica de Reel."""
    audio_id: str
    audio_cluster_id: Optional[str] = None
    title: Optional[str] = None
    artist_name: Optional[str] = None
    artist_username: Optional[str] = None
    duration_seconds: Optional[int] = None
    cover_art_url: Optional[str] = None
    reels_count: int = 0
    is_trending: bool = False
    is_original: bool = False


@dataclass
class FullScrapingResult:
    """Resultado completo de scraping."""
    profile: Optional[ScrapedProfile] = None
    videos: list[dict] = field(default_factory=list)  # ViralVideos
    stories: list[ScrapedStory] = field(default_factory=list)
    carousels: list[ScrapedCarousel] = field(default_factory=list)
    comments: list[ScrapedComment] = field(default_factory=list)
    audios: list[ScrapedAudio] = field(default_factory=list)

    # Metricas
    total_posts: int = 0
    total_videos: int = 0
    total_stories: int = 0
    total_carousels: int = 0
    total_comments: int = 0

    # Custos
    cost_usd: float = 0.0
    duration_seconds: float = 0.0


# ============================================================================
# SCRAPER PRINCIPAL
# ============================================================================

class InstagramScraper:
    """Scraper completo do Instagram usando Apify."""

    # Actors do Apify
    PROFILE_SCRAPER = "apify/instagram-profile-scraper"
    POST_SCRAPER = "apify/instagram-scraper"
    STORY_SCRAPER = "apify/instagram-story-scraper"
    COMMENT_SCRAPER = "apify/instagram-comment-scraper"
    HASHTAG_SCRAPER = "apify/instagram-hashtag-scraper"

    # Custos por 1000 resultados
    COSTS = {
        "profile": Decimal("1.50"),
        "post": Decimal("2.30"),
        "story": Decimal("2.00"),
        "comment": Decimal("1.80"),
        "hashtag": Decimal("2.30"),
    }

    def __init__(self):
        """Inicializa cliente Apify."""
        if not settings.apify_token:
            raise RuntimeError("APIFY_TOKEN nao configurado")
        self.client = ApifyClient(settings.apify_token)

    # ========================================================================
    # PROFILE SCRAPING
    # ========================================================================

    def scrape_profile(self, username: str) -> ScrapedProfile:
        """Coleta dados completos de um perfil.

        Args:
            username: Username sem @

        Returns:
            ScrapedProfile com todos os dados
        """
        run_input = {
            "usernames": [username],
            "resultsLimit": 1,
        }

        run = self.client.actor(self.PROFILE_SCRAPER).call(run_input=run_input)

        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            return self._parse_profile(item)

        raise ValueError(f"Perfil @{username} nao encontrado")

    def _parse_profile(self, item: dict) -> ScrapedProfile:
        """Parseia dados do perfil."""
        return ScrapedProfile(
            instagram_id=str(item.get("id", "")),
            username=item.get("username", ""),
            full_name=item.get("fullName"),
            biography=item.get("biography"),
            external_url=item.get("externalUrl"),
            profile_pic_url=item.get("profilePicUrl"),
            profile_pic_url_hd=item.get("profilePicUrlHD"),
            follower_count=item.get("followersCount", 0),
            following_count=item.get("followsCount", 0),
            media_count=item.get("postsCount", 0),
            is_private=item.get("private", False),
            is_verified=item.get("verified", False),
            is_business=item.get("isBusinessAccount", False),
            business_category=item.get("businessCategory"),
        )

    # ========================================================================
    # STORIES SCRAPING
    # ========================================================================

    def scrape_stories(self, username: str) -> list[ScrapedStory]:
        """Coleta stories ativos de um perfil.

        Args:
            username: Username sem @

        Returns:
            Lista de ScrapedStory
        """
        run_input = {
            "usernames": [username],
            "resultsLimit": 100,
        }

        run = self.client.actor(self.STORY_SCRAPER).call(run_input=run_input)

        stories = []
        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            story = self._parse_story(item, username)
            if story:
                stories.append(story)

        return stories

    def _parse_story(self, item: dict, username: str) -> Optional[ScrapedStory]:
        """Parseia dados de um story."""
        try:
            story_id = item.get("id") or item.get("pk")
            if not story_id:
                return None

            is_video = item.get("media_type") == 2 or item.get("is_video", False)

            # Detecta elementos interativos
            stickers = item.get("story_cta", []) or []
            has_link = any(s.get("webUri") for s in stickers if isinstance(s, dict))
            link_url = None
            for s in stickers:
                if isinstance(s, dict) and s.get("webUri"):
                    link_url = s.get("webUri")
                    break

            # Timestamps
            taken_at = None
            if item.get("taken_at"):
                taken_at = datetime.fromtimestamp(item["taken_at"])

            expiring_at = None
            if item.get("expiring_at"):
                expiring_at = datetime.fromtimestamp(item["expiring_at"])

            # Musica
            music_info = None
            has_music = False
            if item.get("story_music_stickers"):
                has_music = True
                music_sticker = item["story_music_stickers"][0] if item["story_music_stickers"] else {}
                music_info = {
                    "title": music_sticker.get("music_asset_info", {}).get("title"),
                    "artist": music_sticker.get("music_asset_info", {}).get("display_artist"),
                    "duration": music_sticker.get("music_asset_info", {}).get("duration_in_ms"),
                }

            return ScrapedStory(
                story_id=str(story_id),
                story_pk=str(item.get("pk", "")),
                owner_username=username,
                media_type="video" if is_video else "image",
                is_video=is_video,
                media_url=item.get("image_versions2", {}).get("candidates", [{}])[0].get("url"),
                video_url=item.get("video_versions", [{}])[0].get("url") if is_video else None,
                thumbnail_url=item.get("image_versions2", {}).get("candidates", [{}])[0].get("url"),
                width=item.get("original_width"),
                height=item.get("original_height"),
                duration_seconds=item.get("video_duration"),
                has_audio=item.get("has_audio", False),
                has_music=has_music,
                music_info=music_info,
                has_poll="story_polls" in item,
                has_question="story_questions" in item,
                has_quiz="story_quizs" in item,
                has_countdown="story_countdowns" in item,
                has_link=has_link,
                link_url=link_url,
                stickers=stickers,
                mentions=self._extract_mentions(item.get("caption", {}).get("text", "") if item.get("caption") else ""),
                hashtags=self._extract_hashtags(item.get("caption", {}).get("text", "") if item.get("caption") else ""),
                taken_at=taken_at,
                expiring_at=expiring_at,
            )
        except Exception as e:
            print(f"[Instagram] Erro ao parsear story: {e}")
            return None

    # ========================================================================
    # CAROUSELS SCRAPING
    # ========================================================================

    def scrape_carousels(
        self,
        username: str,
        max_posts: int = 50,
    ) -> list[ScrapedCarousel]:
        """Coleta carrosseis de um perfil.

        Args:
            username: Username sem @
            max_posts: Maximo de posts a verificar

        Returns:
            Lista de ScrapedCarousel
        """
        run_input = {
            "directUrls": [f"https://www.instagram.com/{username}/"],
            "resultsType": "posts",
            "resultsLimit": max_posts,
        }

        run = self.client.actor(self.POST_SCRAPER).call(run_input=run_input)

        carousels = []
        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            # Filtra apenas carrosseis
            if item.get("type") not in ["Sidecar", "GraphSidecar", "carousel"]:
                continue

            carousel = self._parse_carousel(item, username)
            if carousel:
                carousels.append(carousel)

        return carousels

    def _parse_carousel(self, item: dict, username: str) -> Optional[ScrapedCarousel]:
        """Parseia dados de um carrossel."""
        try:
            carousel_id = item.get("id") or item.get("pk")
            shortcode = item.get("shortCode") or item.get("shortcode")

            if not carousel_id or not shortcode:
                return None

            # Parse slides
            slides = []
            sidecar_children = item.get("childPosts", []) or item.get("edge_sidecar_to_children", {}).get("edges", [])

            for idx, child in enumerate(sidecar_children):
                if isinstance(child, dict) and "node" in child:
                    child = child["node"]

                is_video = child.get("is_video", False) or child.get("media_type") == 2
                slide = CarouselSlide(
                    index=idx,
                    media_type="video" if is_video else "image",
                    url=child.get("video_url") if is_video else child.get("display_url", ""),
                    thumbnail_url=child.get("display_url"),
                    is_video=is_video,
                    duration_seconds=child.get("video_duration"),
                    width=child.get("dimensions", {}).get("width"),
                    height=child.get("dimensions", {}).get("height"),
                )
                slides.append(slide)

            caption = item.get("caption", "")
            posted_at = None
            if item.get("timestamp"):
                if isinstance(item["timestamp"], int):
                    posted_at = datetime.fromtimestamp(item["timestamp"])

            return ScrapedCarousel(
                carousel_id=str(carousel_id),
                shortcode=shortcode,
                source_url=f"https://www.instagram.com/p/{shortcode}/",
                owner_username=username,
                likes_count=item.get("likesCount", 0),
                comments_count=item.get("commentsCount", 0),
                saves_count=0,  # Nao disponivel publicamente
                caption=caption,
                hashtags=self._extract_hashtags(caption),
                mentions=self._extract_mentions(caption),
                slides=slides,
                posted_at=posted_at,
            )
        except Exception as e:
            print(f"[Instagram] Erro ao parsear carousel: {e}")
            return None

    # ========================================================================
    # COMMENTS SCRAPING
    # ========================================================================

    def scrape_comments(
        self,
        post_url: str,
        max_comments: int = 100,
        include_replies: bool = True,
    ) -> list[ScrapedComment]:
        """Coleta comentarios de um post.

        Args:
            post_url: URL do post
            max_comments: Maximo de comentarios
            include_replies: Incluir respostas

        Returns:
            Lista de ScrapedComment
        """
        run_input = {
            "directUrls": [post_url],
            "resultsLimit": max_comments,
            "includeNestedComments": include_replies,
        }

        run = self.client.actor(self.COMMENT_SCRAPER).call(run_input=run_input)

        comments = []
        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            comment = self._parse_comment(item)
            if comment:
                comments.append(comment)

        return comments

    def _parse_comment(self, item: dict, parent_id: Optional[str] = None) -> Optional[ScrapedComment]:
        """Parseia dados de um comentario."""
        try:
            comment_id = item.get("id") or item.get("pk")
            if not comment_id:
                return None

            text = item.get("text", "")
            created_at = None
            if item.get("created_at"):
                created_at = datetime.fromtimestamp(item["created_at"])

            # Parse owner
            owner = item.get("owner", {}) or item.get("user", {})

            # Parse replies
            replies = []
            child_comments = item.get("edge_threaded_comments", {}).get("edges", []) or item.get("child_comments", [])
            for child in child_comments:
                if isinstance(child, dict) and "node" in child:
                    child = child["node"]
                reply = self._parse_comment(child, parent_id=str(comment_id))
                if reply:
                    replies.append(reply)

            return ScrapedComment(
                comment_id=str(comment_id),
                comment_pk=str(item.get("pk", "")),
                author_id=str(owner.get("id", "")),
                author_username=owner.get("username", ""),
                author_full_name=owner.get("full_name"),
                author_profile_pic=owner.get("profile_pic_url"),
                is_author_verified=owner.get("is_verified", False),
                text=text,
                mentions=self._extract_mentions(text),
                hashtags=self._extract_hashtags(text),
                likes_count=item.get("like_count", 0) or item.get("likes_count", 0),
                replies_count=len(replies),
                is_reply=parent_id is not None,
                is_pinned=item.get("is_pinned", False),
                parent_comment_id=parent_id,
                replies=replies,
                created_at=created_at,
            )
        except Exception as e:
            print(f"[Instagram] Erro ao parsear comment: {e}")
            return None

    # ========================================================================
    # AUDIO/MUSIC SCRAPING
    # ========================================================================

    def scrape_audio_from_reel(self, reel_url: str) -> Optional[ScrapedAudio]:
        """Extrai info do audio de um Reel.

        Args:
            reel_url: URL do reel

        Returns:
            ScrapedAudio ou None
        """
        run_input = {
            "directUrls": [reel_url],
            "resultsType": "posts",
            "resultsLimit": 1,
        }

        run = self.client.actor(self.POST_SCRAPER).call(run_input=run_input)

        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            music = item.get("musicInfo") or item.get("clips_music_attribution_info")
            if music:
                return ScrapedAudio(
                    audio_id=str(music.get("audio_id", "") or music.get("audio_cluster_id", "")),
                    audio_cluster_id=str(music.get("audio_cluster_id", "")),
                    title=music.get("title") or music.get("song_name"),
                    artist_name=music.get("artist_name") or music.get("artist", {}).get("name"),
                    artist_username=music.get("artist", {}).get("username"),
                    duration_seconds=music.get("duration_in_ms", 0) // 1000 if music.get("duration_in_ms") else None,
                    cover_art_url=music.get("cover_artwork_uri"),
                    is_original=music.get("is_original_audio_on_ig", False),
                )

        return None

    def scrape_trending_audios(self, limit: int = 50) -> list[ScrapedAudio]:
        """Coleta audios trending.

        Nota: Requer scraping de reels populares para extrair audios.
        """
        # Por enquanto, retorna lista vazia - implementacao completa requer
        # scraping de explore page ou hashtags trending
        return []

    # ========================================================================
    # FULL PROFILE SCRAPING
    # ========================================================================

    def scrape_full_profile(
        self,
        username: str,
        include_stories: bool = True,
        include_carousels: bool = True,
        include_comments: bool = True,
        max_videos: int = 50,
        max_comments_per_post: int = 50,
    ) -> FullScrapingResult:
        """Coleta TUDO de um perfil.

        Args:
            username: Username sem @
            include_stories: Coletar stories
            include_carousels: Coletar carrosseis
            include_comments: Coletar comentarios
            max_videos: Maximo de videos/reels
            max_comments_per_post: Comentarios por post

        Returns:
            FullScrapingResult com todos os dados
        """
        start_time = datetime.now()
        result = FullScrapingResult()
        total_cost = Decimal("0")

        # 1. Perfil
        print(f"[Instagram] Coletando perfil @{username}...")
        try:
            result.profile = self.scrape_profile(username)
            total_cost += self.COSTS["profile"]
        except Exception as e:
            print(f"[Instagram] Erro ao coletar perfil: {e}")

        # 2. Videos/Reels (usando o scraper existente)
        print(f"[Instagram] Coletando videos/reels...")
        try:
            from src.tools.scraping_tools import scraping_tools
            video_result = scraping_tools.scrape_profile_videos(
                username=username,
                max_videos=max_videos,
            )
            result.videos = [v.__dict__ for v in video_result.videos]
            result.total_videos = len(result.videos)
            total_cost += Decimal(str(video_result.cost_usd))
        except Exception as e:
            print(f"[Instagram] Erro ao coletar videos: {e}")

        # 3. Stories
        if include_stories:
            print(f"[Instagram] Coletando stories...")
            try:
                result.stories = self.scrape_stories(username)
                result.total_stories = len(result.stories)
                total_cost += self.COSTS["story"] * len(result.stories) / 1000
            except Exception as e:
                print(f"[Instagram] Erro ao coletar stories: {e}")

        # 4. Carrosseis
        if include_carousels:
            print(f"[Instagram] Coletando carrosseis...")
            try:
                result.carousels = self.scrape_carousels(username, max_posts=max_videos)
                result.total_carousels = len(result.carousels)
            except Exception as e:
                print(f"[Instagram] Erro ao coletar carrosseis: {e}")

        # 5. Comentarios dos videos
        if include_comments and result.videos:
            print(f"[Instagram] Coletando comentarios...")
            for video in result.videos[:10]:  # Limita a 10 videos para nao estourar custo
                try:
                    url = video.get("source_url")
                    if url:
                        comments = self.scrape_comments(url, max_comments=max_comments_per_post)
                        result.comments.extend(comments)
                        total_cost += self.COSTS["comment"] * len(comments) / 1000
                except Exception as e:
                    print(f"[Instagram] Erro ao coletar comentarios: {e}")

            result.total_comments = len(result.comments)

        # 6. Extrai audios dos videos
        print(f"[Instagram] Extraindo audios...")
        seen_audio_ids = set()
        for video in result.videos[:20]:  # Limita para nao demorar muito
            try:
                url = video.get("source_url")
                if url:
                    audio = self.scrape_audio_from_reel(url)
                    if audio and audio.audio_id not in seen_audio_ids:
                        result.audios.append(audio)
                        seen_audio_ids.add(audio.audio_id)
            except Exception:
                pass

        # Calcula totais
        result.total_posts = result.total_videos + result.total_carousels
        result.cost_usd = float(total_cost)
        result.duration_seconds = (datetime.now() - start_time).total_seconds()

        print(f"[Instagram] Scraping completo!")
        print(f"  - Perfil: {'OK' if result.profile else 'ERRO'}")
        print(f"  - Videos: {result.total_videos}")
        print(f"  - Stories: {result.total_stories}")
        print(f"  - Carrosseis: {result.total_carousels}")
        print(f"  - Comentarios: {result.total_comments}")
        print(f"  - Audios: {len(result.audios)}")
        print(f"  - Custo: ${result.cost_usd:.2f}")
        print(f"  - Duracao: {result.duration_seconds:.1f}s")

        return result

    # ========================================================================
    # HASHTAG SCRAPING
    # ========================================================================

    def scrape_hashtag(
        self,
        hashtag: str,
        max_posts: int = 100,
        content_type: str = "all",  # all, video, image
    ) -> FullScrapingResult:
        """Coleta posts de uma hashtag.

        Args:
            hashtag: Hashtag sem #
            max_posts: Maximo de posts
            content_type: Filtro de tipo

        Returns:
            FullScrapingResult
        """
        start_time = datetime.now()
        result = FullScrapingResult()

        run_input = {
            "directUrls": [f"https://www.instagram.com/explore/tags/{hashtag}/"],
            "resultsType": "posts",
            "resultsLimit": max_posts,
        }

        run = self.client.actor(self.HASHTAG_SCRAPER).call(run_input=run_input)

        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            item_type = item.get("type", "")

            if item_type in ["Video", "Reel", "video"]:
                result.videos.append(item)
            elif item_type in ["Sidecar", "GraphSidecar", "carousel"]:
                carousel = self._parse_carousel(item, item.get("ownerUsername", ""))
                if carousel:
                    result.carousels.append(carousel)

        result.total_videos = len(result.videos)
        result.total_carousels = len(result.carousels)
        result.total_posts = result.total_videos + result.total_carousels
        result.cost_usd = float(self.COSTS["hashtag"] * result.total_posts / 1000)
        result.duration_seconds = (datetime.now() - start_time).total_seconds()

        return result

    # ========================================================================
    # HELPERS
    # ========================================================================

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

    def get_post_metrics(self, post_url: str) -> Optional[dict]:
        """Coleta metricas atualizadas de um post especifico.

        Args:
            post_url: URL do post (reel, post, etc)

        Returns:
            Dict com metricas {views, likes, comments, shares, saves} ou None
        """
        try:
            # Extrai shortcode da URL
            import re
            patterns = [
                r"instagram\.com/p/([A-Za-z0-9_-]+)",
                r"instagram\.com/reel/([A-Za-z0-9_-]+)",
                r"instagram\.com/reels/([A-Za-z0-9_-]+)",
            ]

            shortcode = None
            for pattern in patterns:
                match = re.search(pattern, post_url)
                if match:
                    shortcode = match.group(1)
                    break

            if not shortcode:
                print(f"[Instagram] Nao foi possivel extrair shortcode de: {post_url}")
                return None

            # Usa Apify para coletar info do post
            run_input = {
                "directUrls": [post_url],
                "resultsType": "posts",
                "resultsLimit": 1,
            }

            run = self.client.actor(self.POST_SCRAPER).call(run_input=run_input)

            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                return {
                    "views": item.get("videoPlayCount", 0) or item.get("playCount", 0),
                    "likes": item.get("likesCount", 0),
                    "comments": item.get("commentsCount", 0),
                    "shares": item.get("sharesCount", 0),
                    "saves": item.get("savesCount", 0),
                    "shortcode": shortcode,
                    "collected_at": datetime.now().isoformat(),
                }

            return None

        except Exception as e:
            print(f"[Instagram] Erro ao coletar metricas do post: {e}")
            return None

    def estimate_cost(
        self,
        profiles: int = 0,
        videos_per_profile: int = 50,
        include_stories: bool = True,
        include_comments: bool = True,
        comments_per_post: int = 50,
    ) -> dict:
        """Estima custo de uma operacao de scraping.

        Returns:
            Dict com breakdown de custos
        """
        costs = {
            "profiles": float(self.COSTS["profile"] * profiles),
            "videos": float(self.COSTS["post"] * profiles * videos_per_profile / 1000),
            "stories": float(self.COSTS["story"] * profiles * 10 / 1000) if include_stories else 0,
            "comments": float(self.COSTS["comment"] * profiles * 10 * comments_per_post / 1000) if include_comments else 0,
        }
        costs["total"] = sum(costs.values())
        return costs


# Singleton
instagram_scraper = InstagramScraper()
