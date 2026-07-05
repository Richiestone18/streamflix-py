"""
SeriesFlix provider (Spanish series only).
Ported from streamflix-reborn/streamflix SeriesFlixProvider.
URL: https://seriesflixhd.lol
"""
import re
import base64
import urllib.parse
from bs4 import BeautifulSoup
from ..base import BaseProvider, Movie, TvShow, Category, Server, Episode, Season, MediaDetails
from typing import Optional


class SeriesFlixProvider(BaseProvider):
    name = "SeriesFlix"
    base_url = "https://seriesflixhd.lol"
    language = "es"

    def _normalize_img(self, url: str) -> str:
        if not url:
            return ""
        url = url.strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.base_url + url
        return url

    def _parse_show_card(self, el) -> TvShow:
        a = el.select_one("a[href*='/serie/']")
        if not a:
            return None
        title_el = el.select_one("h2.Title")
        if not title_el:
            return None
        title = title_el.get_text(strip=True)
        img = el.select_one("img")
        poster = self._normalize_img(img.get("data-src") or img.get("src", "")) if img else ""
        overview_el = el.select_one(".Description")
        overview = overview_el.get_text(strip=True) if overview_el else None
        date_el = el.select_one(".Year, .Date, span.Date")
        released = date_el.get_text(strip=True) if date_el else None
        return TvShow(id=a.get("href", "").strip(), title=title, poster=poster, overview=overview, year=released)

    async def get_home(self) -> list[Category]:
        try:
            html = await self._get(self.base_url)
            soup = BeautifulSoup(html, "lxml")
            cats = []
            for section in soup.select("section"):
                title_el = section.select_one(".Top .Title, .Top h2, .Top h3")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                items = []
                if "top 10" in title.lower():
                    for li in section.select("ul.hometop10 li.mvnew"):
                        a = li.select_one("a[href*='/serie/']")
                        t = li.select_one("h2.Title")
                        if a and t:
                            img = li.select_one("img")
                            poster = self._normalize_img(img.get("data-src") or img.get("src", "")) if img else ""
                            items.append(TvShow(id=a.get("href", ""), title=t.get_text(strip=True), poster=poster))
                else:
                    for art in section.select("article.TPost.B"):
                        show = self._parse_show_card(art)
                        if show:
                            items.append(show)
                if items:
                    cats.append(Category(title, items))
            return cats
        except Exception:
            return []

    async def search(self, query: str, page: int = 1) -> list:
        if not query:
            try:
                html = await self._get(self.base_url)
                soup = BeautifulSoup(html, "lxml")
                genres = []
                for a in soup.select("li.menu-item-has-children a[href*='/genero/']"):
                    href = a.get("href", "").strip()
                    name = a.get_text(strip=True)
                    if href and name:
                        genres.append({"id": href, "name": name, "type": "genre"})
                return genres
            except Exception:
                return []
        try:
            encoded = urllib.parse.quote(query)
            if page <= 1:
                url = f"{self.base_url}/?s={encoded}"
            else:
                url = f"{self.base_url}/page/{page}/?s={encoded}"
            html = await self._get(url)
            soup = BeautifulSoup(html, "lxml")
            results = []
            for art in soup.select("article.TPost.B"):
                show = self._parse_show_card(art)
                if show:
                    results.append(show)
            return results
        except Exception:
            return []

    async def get_movies(self, page: int = 1) -> list[Movie]:
        return []

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        try:
            html = await self._get(f"{self.base_url}/peliculas-online/series-online/page/{page}")
            soup = BeautifulSoup(html, "lxml")
            results = []
            for art in soup.select("article.TPost.B"):
                show = self._parse_show_card(art)
                if show:
                    results.append(show)
            return results
        except Exception:
            return []

    async def get_genre(self, genre_id: str, page: int = 1) -> list:
        try:
            if genre_id.startswith("http"):
                url = genre_id if page <= 1 else f"{genre_id.rstrip('/')}/page/{page}/"
            else:
                if page <= 1:
                    url = f"{self.base_url}/genero/{genre_id.strip('/')}/"
                else:
                    url = f"{self.base_url}/genero/{genre_id.strip('/')}/page/{page}/"
            html = await self._get(url)
            soup = BeautifulSoup(html, "lxml")
            results = []
            for art in soup.select("article.TPost.B"):
                show = self._parse_show_card(art)
                if show:
                    results.append(show)
            return results
        except Exception:
            return []

    async def get_details(self, item_id: str) -> Optional[MediaDetails]:
        try:
            html = await self._get(item_id)
            soup = BeautifulSoup(html, "lxml")
            container = soup.select_one("article.TPost.A") or soup

            title_el = container.select_one("h1.Title")
            title = title_el.get_text(strip=True).replace("Serie ", "").strip() if title_el else item_id

            desc_el = container.select_one(".Description > p:not([class])")
            overview = desc_el.get_text(strip=True) if desc_el else None

            img_el = container.select_one(".Image img")
            poster = self._normalize_img(img_el.get("src", "")) if img_el else None

            genres = []
            for ga in container.select(".Description .Genre a[href]"):
                genres.append(ga.get_text(strip=True).rstrip(","))

            seasons = []
            for a in soup.select("a[href*='/temporada/']"):
                href = a.get("href", "").strip()
                m = re.search(r"Temporada\s+(\d+)", a.get_text(), re.IGNORECASE)
                if not m:
                    m = re.search(r"-(\d+)/?$", href)
                if m:
                    num = int(m.group(1))
                    seasons.append(Season(id=href, number=num, title=f"Temporada {num}"))

            return MediaDetails(
                id=item_id, title=title, type="series", poster=poster,
                overview=overview, genres=genres, seasons=seasons,
            )
        except Exception:
            return None

    async def get_servers(self, movie_id: str) -> list[Server]:
        """For SeriesFlix, the movie_id is an episode URL.
        Get the page and extract the server URLs from .Button.sgty[data-url]."""
        import base64
        html = await self._get(movie_id)
        soup = BeautifulSoup(html, "lxml")
        servers = []

        # The episode page has .Button.sgty[data-url] with base64 encoded URLs
        for btn in soup.select(".Button.sgty[data-url]"):
            data_url = btn.get("data-url", "").strip()
            if not data_url:
                continue
            try:
                decoded = base64.b64decode(data_url.strip()).decode("utf-8").strip()
                if decoded.startswith("http"):
                    servers.append(Server(id=decoded, name="SeriesFlix Stream"))
            except Exception:
                pass

        # Fallback: try iframes
        if not servers:
            for iframe in soup.select("iframe[src]"):
                src = iframe.get("src", "")
                if src.startswith("http"):
                    servers.append(Server(id=src, name="iframe"))

        return servers
