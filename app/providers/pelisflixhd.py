"""
PelisflixHD provider (Spanish movies/series).
Ported from streamflix-reborn/streamflix Kotlin project.
URL: https://pelisflixhd.win
"""
import re
import base64
import urllib.parse
from bs4 import BeautifulSoup
from ..base import BaseProvider, Movie, TvShow, Category, Server, Episode, Season, MediaDetails
from typing import Optional


class PelisflixHdProvider(BaseProvider):
    name = "PelisflixHD"
    base_url = "https://pelisflixhd.win"
    language = "es"

    def _normalize_url(self, url: str) -> str:
        if not url:
            return ""
        url = url.strip()
        if url.startswith("http://") or url.startswith("https://"):
            return url
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.base_url + url
        return f"{self.base_url}/{url.lstrip('/')}"

    def _parse_show_links(self, links: list) -> list:
        items = {}
        for link in links:
            href = self._normalize_url(link.get("href", ""))
            if not href:
                continue

            title = None
            detail = link.select_one(".item-detail p")
            if detail and detail.get_text(strip=True):
                title = detail.get_text(strip=True)
            if not title:
                img = link.select_one("img")
                if img:
                    title = img.get("alt", "").replace("Poster ", "").strip()
            if not title:
                continue

            poster = self._normalize_url(
                (link.select_one("img.poster, img") or {}).get("src", "") if link.select_one("img.poster, img") else ""
            )

            if "/pelicula/" in href:
                items[href] = Movie(id=href, title=title, poster=poster)
            elif "/serie/" in href:
                items[href] = TvShow(id=href, title=title, poster=poster)

        return list(items.values())

    def _build_paged_url(self, base: str, page: int) -> str:
        if page <= 1:
            return base.rstrip("/")
        return f"{base.rstrip('/')}/page/{page}"

    async def get_home(self) -> list[Category]:
        try:
            html = await self._get(self.base_url)
            soup = BeautifulSoup(html, "lxml")
            cats = []
            for section in soup.select("section.section-separator.container"):
                title_el = section.select_one("dt.section-title")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                shows = self._parse_show_links(section.select("a[href*='/pelicula/'], a[href*='/serie/']"))
                if shows:
                    cats.append(Category(title, shows))
            return cats
        except Exception:
            return []

    async def search(self, query: str, page: int = 1) -> list:
        if not query:
            try:
                html = await self._get(self.base_url)
                soup = BeautifulSoup(html, "lxml")
                genres = []
                for link in soup.select(".showcase-sidebar-navigation a[href*='/genero/']"):
                    href = self._normalize_url(link.get("href", ""))
                    name = link.get_text(strip=True)
                    if href and name:
                        genres.append({"id": href, "name": name, "type": "genre"})
                return genres
            except Exception:
                return []
        try:
            encoded = urllib.parse.quote(query)
            url = self._build_paged_url(f"{self.base_url}/busqueda/{encoded}", page)
            html = await self._get(url)
            soup = BeautifulSoup(html, "lxml")
            return self._parse_show_links(soup.select("a[href*='/pelicula/'], a[href*='/serie/']"))
        except Exception:
            return []

    async def get_movies(self, page: int = 1) -> list[Movie]:
        try:
            url = self._build_paged_url(f"{self.base_url}/peliculas", page)
            html = await self._get(url)
            soup = BeautifulSoup(html, "lxml")
            shows = self._parse_show_links(soup.select("a[href*='/pelicula/']"))
            return [s for s in shows if isinstance(s, Movie)]
        except Exception:
            return []

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        try:
            url = self._build_paged_url(f"{self.base_url}/series", page)
            html = await self._get(url)
            soup = BeautifulSoup(html, "lxml")
            shows = self._parse_show_links(soup.select("a[href*='/serie/']"))
            return [s for s in shows if isinstance(s, TvShow)]
        except Exception:
            return []

    async def get_genre(self, genre_id: str, page: int = 1) -> list:
        try:
            url = self._build_paged_url(self._normalize_url(genre_id), page)
            html = await self._get(url)
            soup = BeautifulSoup(html, "lxml")
            return self._parse_show_links(soup.select("a[href*='/pelicula/'], a[href*='/serie/']"))
        except Exception:
            return []

    async def get_details(self, item_id: str) -> Optional[MediaDetails]:
        try:
            url = self._normalize_url(item_id)
            html = await self._get(url)
            soup = BeautifulSoup(html, "lxml")
            info = soup.select_one("article.backdrop-info")
            if not info:
                return None

            title_el = info.select_one("h1 .itemprop, h1 [itemprop=name], h1")
            title = title_el.get_text(strip=True).replace("Ver Película", "").replace("Ver Serie", "").strip()

            overview_el = info.select_one(".description p")
            overview = overview_el.get_text(strip=True) if overview_el else None

            poster_el = info.select_one("figure.poster img")
            poster = self._normalize_url(poster_el.get("src", "")) if poster_el else None

            genres = []
            for ga in info.select(".info-list a[href*='/genero/']"):
                genres.append(ga.get_text(strip=True).rstrip(","))

            is_movie = "/pelicula/" in url
            seasons = []
            if not is_movie:
                for link in soup.select("a[href*='/temporada/']"):
                    href = self._normalize_url(link.get("href", ""))
                    m = re.search(r"-(\d+)/?$", href)
                    if m:
                        num = int(m.group(1))
                        seasons.append(Season(id=href, number=num, title=f"Temporada {num}"))

            return MediaDetails(
                id=item_id, title=title, type="movie" if is_movie else "series",
                poster=poster, overview=overview, genres=genres, seasons=seasons,
            )
        except Exception:
            return None

    async def get_servers(self, movie_id: str) -> list[Server]:
        try:
            url = self._normalize_url(movie_id)
            html = await self._get(url)
            soup = BeautifulSoup(html, "lxml")
            servers = []
            for i, item in enumerate(soup.select("#player li[data-server]")):
                encoded = item.get("data-server", "")
                if not encoded:
                    continue
                try:
                    decoded = base64.b64decode(encoded).decode("utf-8").strip()
                except Exception:
                    continue
                name_el = item.select_one("span")
                name = name_el.get_text(strip=True) if name_el else f"Opción {i+1}"
                servers.append(Server(id=decoded, name=name))
            # Deduplicate
            seen = set()
            unique = []
            for s in servers:
                if s.id not in seen:
                    seen.add(s.id)
                    unique.append(s)
            return unique
        except Exception:
            return []
