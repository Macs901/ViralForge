"""Twitter/X Scraper - Coleta dados de tendencias e videos do Twitter/X."""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP

# MCP Server para Twitter Tools
twitter_mcp = FastMCP("twitter-tools")


@dataclass
class TwitterVideo:
    """Video do Twitter/X."""
    tweet_id: str
    author: str
    author_name: Optional[str] = None
    text: str = ""
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    views: int = 0
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    quotes: int = 0
    created_at: Optional[datetime] = None
    hashtags: list[str] = field(default_factory=list)
    url: Optional[str] = None


@dataclass
class TwitterTrend:
    """Trending topic do Twitter/X."""
    name: str
    tweet_volume: Optional[int] = None
    category: Optional[str] = None
    url: Optional[str] = None


@dataclass
class TwitterProfile:
    """Perfil do Twitter/X."""
    username: str
    name: str
    description: str = ""
    followers_count: int = 0
    following_count: int = 0
    tweet_count: int = 0
    verified: bool = False
    profile_image_url: Optional[str] = None
    banner_url: Optional[str] = None
    created_at: Optional[datetime] = None


class TwitterScraper:
    """Scraper para Twitter/X.

    Suporta:
    - API oficial do Twitter (requer credenciais)
    - Nitter (frontend alternativo open-source)
    - Syndication API (dados publicos limitados)

    Nota: Twitter/X tem restricoes fortes. Use com moderacao.
    """

    def __init__(self):
        """Inicializa o scraper."""
        # Credenciais da API oficial
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self.api_key = os.getenv("TWITTER_API_KEY")
        self.api_secret = os.getenv("TWITTER_API_SECRET")

        # Nitter instances para fallback
        self.nitter_instances = [
            "https://nitter.net",
            "https://nitter.privacydev.net",
            "https://nitter.poast.org",
        ]

        self._authenticated = False

    def authenticate(self) -> bool:
        """Verifica autenticacao com Twitter API."""
        if not self.bearer_token:
            print("[TwitterScraper] Bearer token nao configurado")
            return False

        try:
            import httpx

            response = httpx.get(
                "https://api.twitter.com/2/users/me",
                headers={
                    "Authorization": f"Bearer {self.bearer_token}",
                },
                timeout=10,
            )

            if response.status_code == 200:
                self._authenticated = True
                return True

        except Exception as e:
            print(f"[TwitterScraper] Erro de autenticacao: {e}")

        return False

    def get_trending(self, location: str = "worldwide") -> list[TwitterTrend]:
        """Busca trending topics.

        Args:
            location: Localizacao (worldwide, brazil, usa, etc)

        Returns:
            Lista de TwitterTrend
        """
        # Tenta API oficial primeiro
        if self._authenticated:
            return self._get_trending_api(location)

        # Fallback para Nitter
        return self._get_trending_nitter()

    def _get_trending_api(self, location: str) -> list[TwitterTrend]:
        """Busca trends via API oficial."""
        import httpx

        # WOEIDs comuns
        woeid_map = {
            "worldwide": 1,
            "brazil": 23424768,
            "usa": 23424977,
            "uk": 23424975,
        }

        woeid = woeid_map.get(location.lower(), 1)

        try:
            response = httpx.get(
                f"https://api.twitter.com/1.1/trends/place.json",
                params={"id": woeid},
                headers={
                    "Authorization": f"Bearer {self.bearer_token}",
                },
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                trends = []
                for item in data[0].get("trends", []):
                    trends.append(TwitterTrend(
                        name=item.get("name"),
                        tweet_volume=item.get("tweet_volume"),
                        url=item.get("url"),
                    ))
                return trends

        except Exception as e:
            print(f"[TwitterScraper] Erro API trends: {e}")

        return []

    def _get_trending_nitter(self) -> list[TwitterTrend]:
        """Busca trends via Nitter."""
        import httpx
        from bs4 import BeautifulSoup

        for instance in self.nitter_instances:
            try:
                response = httpx.get(
                    f"{instance}/search",
                    params={"f": "trends"},
                    timeout=10,
                    follow_redirects=True,
                )

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    trends = []

                    # Parse trends da pagina
                    trend_elements = soup.select(".trend-link")
                    for elem in trend_elements[:20]:
                        trends.append(TwitterTrend(
                            name=elem.get_text(strip=True),
                            url=f"https://twitter.com/search?q={elem.get_text(strip=True)}",
                        ))

                    if trends:
                        return trends

            except Exception as e:
                print(f"[TwitterScraper] Erro Nitter {instance}: {e}")
                continue

        return []

    def search_videos(
        self,
        query: str,
        max_results: int = 20,
    ) -> list[TwitterVideo]:
        """Busca videos por query.

        Args:
            query: Termo de busca
            max_results: Maximo de resultados

        Returns:
            Lista de TwitterVideo
        """
        if self._authenticated:
            return self._search_videos_api(query, max_results)

        return self._search_videos_syndication(query, max_results)

    def _search_videos_api(self, query: str, max_results: int) -> list[TwitterVideo]:
        """Busca videos via API oficial."""
        import httpx

        try:
            response = httpx.get(
                "https://api.twitter.com/2/tweets/search/recent",
                params={
                    "query": f"{query} has:video",
                    "max_results": min(max_results, 100),
                    "tweet.fields": "created_at,public_metrics,entities",
                    "expansions": "author_id,attachments.media_keys",
                    "media.fields": "preview_image_url,url,variants",
                    "user.fields": "username,name",
                },
                headers={
                    "Authorization": f"Bearer {self.bearer_token}",
                },
                timeout=30,
            )

            if response.status_code != 200:
                return []

            data = response.json()
            tweets = data.get("data", [])
            users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
            media = {m["media_key"]: m for m in data.get("includes", {}).get("media", [])}

            videos = []
            for tweet in tweets:
                author_id = tweet.get("author_id")
                author = users.get(author_id, {})
                metrics = tweet.get("public_metrics", {})

                # Extrai hashtags
                entities = tweet.get("entities", {})
                hashtags = [h["tag"] for h in entities.get("hashtags", [])]

                # Extrai video URL
                video_url = None
                media_keys = tweet.get("attachments", {}).get("media_keys", [])
                for key in media_keys:
                    m = media.get(key, {})
                    if m.get("type") == "video":
                        variants = m.get("variants", [])
                        # Pega maior qualidade
                        mp4_variants = [v for v in variants if v.get("content_type") == "video/mp4"]
                        if mp4_variants:
                            video_url = max(mp4_variants, key=lambda x: x.get("bit_rate", 0)).get("url")

                videos.append(TwitterVideo(
                    tweet_id=tweet["id"],
                    author=author.get("username", ""),
                    author_name=author.get("name", ""),
                    text=tweet.get("text", ""),
                    video_url=video_url,
                    views=metrics.get("impression_count", 0),
                    likes=metrics.get("like_count", 0),
                    retweets=metrics.get("retweet_count", 0),
                    replies=metrics.get("reply_count", 0),
                    quotes=metrics.get("quote_count", 0),
                    created_at=datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00")) if tweet.get("created_at") else None,
                    hashtags=hashtags,
                    url=f"https://twitter.com/{author.get('username')}/status/{tweet['id']}",
                ))

            return videos

        except Exception as e:
            print(f"[TwitterScraper] Erro API search: {e}")
            return []

    def _search_videos_syndication(self, query: str, max_results: int) -> list[TwitterVideo]:
        """Busca videos via Syndication API (publico, limitado)."""
        import httpx

        try:
            # Syndication API para embed
            response = httpx.get(
                "https://syndication.twitter.com/srv/timeline-profile/screen-name/viral",
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0",
                },
            )

            # Syndication e muito limitado, retorna vazio na maioria dos casos
            return []

        except Exception as e:
            print(f"[TwitterScraper] Erro syndication: {e}")
            return []

    def get_profile(self, username: str) -> Optional[TwitterProfile]:
        """Busca perfil de usuario.

        Args:
            username: Username do perfil

        Returns:
            TwitterProfile ou None
        """
        if self._authenticated:
            return self._get_profile_api(username)

        return self._get_profile_nitter(username)

    def _get_profile_api(self, username: str) -> Optional[TwitterProfile]:
        """Busca perfil via API oficial."""
        import httpx

        try:
            response = httpx.get(
                f"https://api.twitter.com/2/users/by/username/{username}",
                params={
                    "user.fields": "description,profile_image_url,public_metrics,verified,created_at",
                },
                headers={
                    "Authorization": f"Bearer {self.bearer_token}",
                },
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json().get("data", {})
                metrics = data.get("public_metrics", {})

                return TwitterProfile(
                    username=data.get("username", username),
                    name=data.get("name", ""),
                    description=data.get("description", ""),
                    followers_count=metrics.get("followers_count", 0),
                    following_count=metrics.get("following_count", 0),
                    tweet_count=metrics.get("tweet_count", 0),
                    verified=data.get("verified", False),
                    profile_image_url=data.get("profile_image_url"),
                    created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")) if data.get("created_at") else None,
                )

        except Exception as e:
            print(f"[TwitterScraper] Erro API profile: {e}")

        return None

    def _get_profile_nitter(self, username: str) -> Optional[TwitterProfile]:
        """Busca perfil via Nitter."""
        import httpx
        from bs4 import BeautifulSoup

        for instance in self.nitter_instances:
            try:
                response = httpx.get(
                    f"{instance}/{username}",
                    timeout=10,
                    follow_redirects=True,
                )

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")

                    name_elem = soup.select_one(".profile-card-fullname")
                    bio_elem = soup.select_one(".profile-bio")

                    # Parse stats
                    stats = {}
                    for stat in soup.select(".profile-stat"):
                        label = stat.select_one(".profile-stat-header")
                        value = stat.select_one(".profile-stat-num")
                        if label and value:
                            stats[label.get_text(strip=True).lower()] = self._parse_number(value.get_text(strip=True))

                    return TwitterProfile(
                        username=username,
                        name=name_elem.get_text(strip=True) if name_elem else username,
                        description=bio_elem.get_text(strip=True) if bio_elem else "",
                        followers_count=stats.get("followers", 0),
                        following_count=stats.get("following", 0),
                        tweet_count=stats.get("tweets", 0),
                    )

            except Exception as e:
                print(f"[TwitterScraper] Erro Nitter profile: {e}")
                continue

        return None

    def _parse_number(self, text: str) -> int:
        """Converte texto como '1.2K' para numero."""
        text = text.strip().upper()
        multipliers = {"K": 1000, "M": 1000000, "B": 1000000000}

        for suffix, mult in multipliers.items():
            if text.endswith(suffix):
                return int(float(text[:-1]) * mult)

        try:
            return int(text.replace(",", "").replace(".", ""))
        except ValueError:
            return 0


# Instancia global
twitter_scraper = TwitterScraper()


# ==================
# MCP TOOLS
# ==================

@twitter_mcp.tool()
def get_twitter_trending(location: str = "worldwide") -> dict:
    """Busca trending topics do Twitter/X.

    Args:
        location: Localizacao (worldwide, brazil, usa, uk)

    Returns:
        Lista de trending topics
    """
    trends = twitter_scraper.get_trending(location)

    return {
        "location": location,
        "count": len(trends),
        "trends": [
            {
                "name": t.name,
                "tweet_volume": t.tweet_volume,
                "url": t.url,
            }
            for t in trends
        ],
    }


@twitter_mcp.tool()
def search_twitter_videos(
    query: str,
    max_results: int = 20,
) -> dict:
    """Busca videos no Twitter/X.

    Args:
        query: Termo de busca
        max_results: Maximo de resultados

    Returns:
        Lista de videos encontrados
    """
    videos = twitter_scraper.search_videos(query, max_results)

    return {
        "query": query,
        "count": len(videos),
        "videos": [
            {
                "tweet_id": v.tweet_id,
                "author": v.author,
                "text": v.text[:200],
                "views": v.views,
                "likes": v.likes,
                "retweets": v.retweets,
                "hashtags": v.hashtags,
                "url": v.url,
                "video_url": v.video_url,
            }
            for v in videos
        ],
    }


@twitter_mcp.tool()
def get_twitter_profile(username: str) -> dict:
    """Busca perfil do Twitter/X.

    Args:
        username: Username do perfil

    Returns:
        Dados do perfil
    """
    profile = twitter_scraper.get_profile(username)

    if not profile:
        return {"error": f"Perfil @{username} nao encontrado"}

    return {
        "username": profile.username,
        "name": profile.name,
        "description": profile.description,
        "followers_count": profile.followers_count,
        "following_count": profile.following_count,
        "tweet_count": profile.tweet_count,
        "verified": profile.verified,
        "profile_image_url": profile.profile_image_url,
    }


@twitter_mcp.tool()
def check_twitter_auth() -> dict:
    """Verifica status de autenticacao com Twitter API.

    Returns:
        Status de autenticacao
    """
    authenticated = twitter_scraper.authenticate()

    return {
        "authenticated": authenticated,
        "has_bearer_token": bool(twitter_scraper.bearer_token),
        "fallback_available": "nitter" if twitter_scraper.nitter_instances else None,
    }


# Export
__all__ = ["twitter_mcp", "twitter_scraper", "TwitterVideo", "TwitterTrend", "TwitterProfile"]
