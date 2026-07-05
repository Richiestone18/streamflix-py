"""
Animefenix provider (Spanish anime).
Ported from streamflix-reborn/streamflix AnimefenixProvider.
URL: https://animefenix2.tv
"""
import re
import base64
import urllib.parse
from bs4 import BeautifulSoup
from ..base import BaseProvider, Movie, TvShow, Category, Server, Episode, Season, MediaDetails
from typing import Optional


class AnimefenixProvider(BaseProvider):
    name = "Animefenix"
    base_url = "https://animefenix2.tv"
    language = "es"

    _GENRES = [
        ("1", "Acción"), ("23", "Aventuras"), ("20", "Ciencia Ficción"),
        ("5", "Comedia"), ("8", "Deportes"), ("38", "Demonios"),
        ("6", "Drama"), ("11", "Ecchi"), ("2", "Escolares"),
        ("13", "Fantasía"), ("28", "Harem"), ("24", "Historico"),
        ("47", "Horror"), ("25", "Infantil"), ("51", "Isekai"),
        ("29", "Josei"), ("14", "Magia"), ("26", "Artes Marciales"),
        ("21", "Mecha"), ("22", "Militar"), ("17", "Misterio"),
        ("36", "Música"), ("30", "Parodia"), ("31", "Policía"),
        ("18", "Psicológico"), ("10", "Recuentos de la vida"), ("3", "Romance"),
        ("34", "Samurai"), ("7", "Seinen"), ("4", "Shoujo"),
        ("9", "Shounen"), ("12", "Sobrenatural"), ("15", "Superpoderes"),
        ("19", "Suspenso"), ("27", "Terror"), ("39", "Vampiros"),
        ("40", "Yaoi"), ("37", "Yuri"),
    ]

    def _parse_shows(self, elements: list) -> list:
        results = []
        for el in elements:
            a = el.select_one("a")
            if not a:
                continue
            href = a.get("href", "")
            title_el = el.select_one("h3, p:not(.gray)")
            title = title_el.get_text(strip=True) if title_el else ""
            img = el.select_one("img")
            poster = img.get("data-src") or img.get("src", "") if img else ""
            if poster and not poster.startswith("http"):
                poster = self.base_url + poster
            if href:
                results.append(TvShow(id=href, title=title, poster=poster))
        return results

    def _parse_movies(self, elements: list) -> list:
        results = []
        for el in elements:
            a = el.select_one("a")
            if not a:
                continue
            href = a.get("href", "")
            poster_el = el.select_one(".main-img img")
            poster = poster_el.get("data-src") or poster_el.get("src", "") if poster_el else ""
            title_el = el.select_one("p:not(.gray)")
            title = title_el.get_text(strip=True) if title_el else ""
            results.append(Movie(id=href, title=title, poster=poster))
        return results

    async def get_home(self) -> list[Category]:
        cats = []
        for year in ["2025", "2024", "2023"]:
            try:
                html = await self._get(f"{self.base_url}/directorio/anime?estreno={year}")
                soup = BeautifulSoup(html, "lxml")
                shows = self._parse_shows(soup.select(".grid-animes li article"))
                if shows:
                    cats.append(Category(f"Estrenos {year}", shows))
            except Exception:
                pass
        return cats

    async def search(self, query: str, page: int = 1) -> list:
        if not query:
            return [{"id": gid, "name": gname, "type": "genre"} for gid, gname in self._GENRES]
        try:
            html = await self._get(f"{self.base_url}/directorio/anime?q={urllib.parse.quote(query)}&p={page}")
            soup = BeautifulSoup(html, "lxml")
            shows = self._parse_shows(soup.select(".grid-animes li article"))
            seen = set()
            unique = []
            for s in shows:
                if s.id not in seen:
                    seen.add(s.id)
                    unique.append(s)
            return unique
        except Exception:
            return []

    async def get_movies(self, page: int = 1) -> list[Movie]:
        try:
            html = await self._get(f"{self.base_url}/directorio/anime?tipo=2&p={page}")
            soup = BeautifulSoup(html, "lxml")
            return self._parse_movies(soup.select(".grid-animes li article"))
        except Exception:
            return []

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        try:
            html = await self._get(f"{self.base_url}/directorio/anime?p={page}")
            soup = BeautifulSoup(html, "lxml")
            return self._parse_shows(soup.select(".grid-animes li article"))
        except Exception:
            return []

    async def get_genre(self, genre_id: str, page: int = 1) -> list:
        try:
            html = await self._get(f"{self.base_url}/directorio/anime?genero={genre_id}&p={page}")
            soup = BeautifulSoup(html, "lxml")
            return self._parse_shows(soup.select(".grid-animes li article"))
        except Exception:
            return []

    async def get_details(self, item_id: str) -> Optional[MediaDetails]:
        try:
            url = item_id if item_id.startswith("http") else f"{self.base_url}/{item_id}"
            html = await self._get(url)
            soup = BeautifulSoup(html, "lxml")

            title_el = soup.select_one("h1.text-4xl")
            title = title_el.get_text(strip=True) if title_el else item_id

            poster_el = soup.select_one("#anime_image")
            poster = poster_el.get("data-src") or poster_el.get("src", "") if poster_el else None

            overview_el = soup.select_one("h2:-soup-contains(Sinopsis) + p") or soup.select_one(".mb-6 p.text-gray-300")
            overview = overview_el.get_text(strip=True) if overview_el else None

            genres = []
            for ga in soup.select("a.bg-gray-800, a[href*='/directorio/anime?genero=']"):
                genres.append(ga.get_text(strip=True))

            # Parse episodes with AJAX
            slug = url.rstrip("/").split("/")[-1]
            episodes = []
            try:
                ajax_url = f"{url}?id={slug}&load=episodes&start=0"
                ajax_html = await self._get(ajax_url)
                ajax_soup = BeautifulSoup(ajax_html, "lxml")
                for ep_el in ajax_soup.select(".episode-card"):
                    href = ep_el.get("href", "")
                    if not href:
                        continue
                    if not href.startswith("http"):
                        href = self.base_url + href
                    ep_title = ep_el.select_one(".ep-title")
                    ep_title = ep_title.get_text(strip=True) if ep_title else "Episodio"
                    m = re.search(r"\d+", ep_title)
                    ep_num = int(m.group()) if m else 0
                    img = ep_el.select_one("img")
                    ep_img = img.get("data-src") or img.get("src", "") if img else ""
                    episodes.append(Episode(id=href, number=ep_num, title=ep_title, poster=ep_img))
            except Exception:
                pass

            episodes.sort(key=lambda e: e.number)

            return MediaDetails(
                id=item_id, title=title, type="series",
                poster=poster, overview=overview, genres=genres,
                seasons=[Season(id=item_id, number=1, title="Episodios", episodes=episodes)],
            )
        except Exception:
            return None

    async def get_servers(self, movie_id: str) -> list[Server]:
        try:
            html = await self._get(movie_id)
            soup = BeautifulSoup(html, "lxml")
            servers = []

            # The servers are in a JavaScript tabsArray variable with iframe HTML
            for script in soup.find_all("script"):
                if script.string and "tabsArray" in script.string:
                    # Extract iframe URLs from the JavaScript
                    for m in re.finditer(r"""src=['"]([^'"]+)['"]""", script.string):
                        url = m.group(1)
                        if url.startswith("http"):
                            # Try to get a readable name from the URL
                            name = url.split("//")[-1].split("/")[0].replace("re.", "").split(".")[0].capitalize()
                            servers.append(Server(id=url, name=name))
                    if servers:
                        return servers

            # Fallback: try the original selectors
            for a in soup.select(".episode-page__servers-list li a"):
                name = a.select("span")[-1].get_text(strip=True) if a.select("span") else "Server"
                servers.append(Server(id=a.get("href", ""), name=name))
            return servers
        except Exception:
            return []