"""
FlixLatam provider (Spanish movies/series/animes).
Site: https://flixlatam.com
Uses static HTML with iframe-based players.
"""
from bs4 import BeautifulSoup
from ..base import BaseProvider, Movie, TvShow, Category, Server
import re


class FlixLatamProvider(BaseProvider):
    name = "FlixLatam"
    base_url = "https://flixlatam.com"

    def _parse_movies(self, soup: BeautifulSoup) -> list:
        results = []
        seen = set()
        for a in soup.select('a[href*="/pelicula/"]'):
            href = a.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            if not href.startswith("http"):
                href = self.base_url + href
            img = a.select_one("img")
            title = img.get("alt", "") if img else ""
            if not title:
                title = a.get_text(strip=True)
            title = re.sub(r'^Ver\s+', '', title)
            title = re.sub(r'\s+online$', '', title, flags=re.I)
            title = title.strip()
            poster = img.get("src") if img else None
            if poster and not poster.startswith("http"):
                poster = self.base_url + poster
            if title and len(title) > 2:
                results.append(Movie(id=href, title=title, poster=poster))
        return results

    def _parse_series(self, soup: BeautifulSoup) -> list:
        results = []
        seen = set()
        for a in soup.select('a[href*="/serie/"]'):
            href = a.get("href", "")
            # Skip episode links
            if "/temporada/" in href:
                continue
            if not href or href in seen:
                continue
            seen.add(href)
            if not href.startswith("http"):
                href = self.base_url + href
            img = a.select_one("img")
            title = img.get("alt", "") if img else ""
            if not title:
                title = a.get_text(strip=True)
            title = re.sub(r'^Ver\s+', '', title)
            title = re.sub(r'\s+online$', '', title, flags=re.I)
            title = title.strip()
            poster = img.get("src") if img else None
            if poster and not poster.startswith("http"):
                poster = self.base_url + poster
            if title and len(title) > 2:
                results.append(TvShow(id=href, title=title, poster=poster))
        return results

    def _parse_animes(self, soup: BeautifulSoup) -> list:
        results = []
        seen = set()
        for a in soup.select('a[href*="/anime/"]'):
            href = a.get("href", "")
            if "/temporada/" in href:
                continue
            if not href or href in seen:
                continue
            seen.add(href)
            if not href.startswith("http"):
                href = self.base_url + href
            img = a.select_one("img")
            title = img.get("alt", "") if img else ""
            if not title:
                title = a.get_text(strip=True)
            title = re.sub(r'^Ver\s+', '', title)
            title = re.sub(r'\s+online$', '', title, flags=re.I)
            title = title.strip()
            poster = img.get("src") if img else None
            if poster and not poster.startswith("http"):
                poster = self.base_url + poster
            if title and len(title) > 2:
                results.append(TvShow(id=href, title=title, poster=poster))
        return results

    async def get_movies(self, page: int = 1) -> list[Movie]:
        url = f"{self.base_url}/peliculas?page={page}"
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        return self._parse_movies(soup)

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        url = f"{self.base_url}/series?page={page}"
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        return self._parse_series(soup)

    async def search(self, query: str, page: int = 1) -> list:
        if not query:
            return [
                {"id": "peliculas", "name": "Películas", "type": "genre"},
                {"id": "series", "name": "Series", "type": "genre"},
                {"id": "animes", "name": "Animes", "type": "genre"},
            ]
        url = f"{self.base_url}/peliculas?page={page}"
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        return self._parse_movies(soup)

    async def get_genre(self, genre_id: str, page: int = 1) -> list:
        url = f"{self.base_url}/{genre_id}?page={page}"
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        if genre_id == "peliculas":
            return self._parse_movies(soup)
        elif genre_id == "series":
            return self._parse_series(soup)
        elif genre_id == "animes":
            return self._parse_animes(soup)
        return self._parse_movies(soup)

    async def get_servers(self, movie_id: str) -> list[Server]:
        html = await self._get(movie_id)
        soup = BeautifulSoup(html, "lxml")
        servers = []

        # Look for iframe with /vidurl/ path (movie)
        for iframe in soup.select("iframe[src]"):
            src = iframe.get("src", "")
            if not src:
                continue
            if not src.startswith("http"):
                src = self.base_url + src
            servers.append(Server(id=src, name="FlixLatam Player"))

        # If this is a series episode page, also check episode links
        if not servers:
            episodes = soup.select('a[href*="/temporada/"]')
            for ep in episodes[:1]:  # Just first episode
                ep_url = ep.get("href", "")
                if not ep_url.startswith("http"):
                    ep_url = self.base_url + ep_url
                ep_html = await self._get(ep_url)
                ep_soup = BeautifulSoup(ep_html, "lxml")
                for iframe in ep_soup.select("iframe[src]"):
                    src = iframe.get("src", "")
                    if not src.startswith("http"):
                        src = self.base_url + src
                    servers.append(Server(id=src, name=ep.get_text(strip=True)[:30] or "Episodio 1"))

        return servers
