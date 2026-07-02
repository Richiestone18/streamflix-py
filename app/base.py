"""Base classes and HTTP client for all providers."""
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Optional
import httpx
import cloudscraper


@dataclass
class Movie:
    id: str
    title: str
    poster: Optional[str] = None
    banner: Optional[str] = None
    overview: Optional[str] = None
    rating: Optional[float] = None
    year: Optional[str] = None
    genres: list = field(default_factory=list)


@dataclass
class TvShow:
    id: str
    title: str
    poster: Optional[str] = None
    banner: Optional[str] = None
    overview: Optional[str] = None
    rating: Optional[float] = None
    year: Optional[str] = None
    genres: list = field(default_factory=list)


@dataclass
class Episode:
    id: str
    number: int
    title: str = ""
    poster: Optional[str] = None
    released: Optional[str] = None


@dataclass
class Season:
    id: str
    number: int
    title: str = ""
    episodes: list = field(default_factory=list)


@dataclass
class Server:
    id: str
    name: str = "Server"


@dataclass
class Category:
    name: str
    items: list = field(default_factory=list)


class HttpClient:
    """Shared HTTP client with Cloudflare bypass support."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False},
            delay=2,
        )
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/124.0.0.0 Safari/537.36",
            },
            follow_redirects=True,
            timeout=30.0,
        )

    async def get(self, url: str) -> str:
        """Fetch page content, falling back to cloudscraper if httpx fails."""
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            return resp.text
        except Exception:
            # cloudscraper handles Cloudflare challenges (sync)
            return self.scraper.get(url).text

    def get_sync(self, url: str) -> str:
        """Synchronous fetch with cloudscraper."""
        return self.scraper.get(url).text

    async def get_json(self, url: str) -> dict:
        resp = await self.client.get(url, headers={"Accept": "application/json"})
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        await self.client.aclose()


class BaseProvider(ABC):
    name: str = ""
    base_url: str = ""
    language: str = "es"

    def __init__(self):
        self.http = HttpClient(self.base_url)

    async def _get(self, url: str) -> str:
        return await self.http.get(url)

    async def get_home(self) -> list[Category]:
        return []

    async def search(self, query: str, page: int = 1) -> list:
        return []

    async def get_movies(self, page: int = 1) -> list[Movie]:
        return []

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        return []

    async def get_servers(self, movie_id: str) -> list[Server]:
        return []

    async def get_video(self, server: Server) -> str:
        return server.id