"""
AnimeFlv provider (Spanish anime).
Ported from streamflix-reborn/streamflix AnimeFlvProvider.
URL: https://www3.animeflv.net
"""
import re
import base64
import urllib.parse
from bs4 import BeautifulSoup
from ..base import BaseProvider, Movie, TvShow, Category, Server, Episode, Season, MediaDetails
from typing import Optional


class AnimeFlvProvider(BaseProvider):
    name = "AnimeFLV"
    base_url = "https://www3.animeflv.net"
    language = "es"

    def _parse_animes(self, elements: list) -> list:
        results = []
        for el in elements:
            a = el.select_one("a")
            if not a:
                continue
            href = a.get("href", "")
            title = a.get("title") or a.select_one(".Title") and a.select_one(".Title").get_text(strip=True) or ""
            if not title:
                img = el.select_one("img")
                if img:
                    title = img.get("alt", "")
            poster = ""
            img = el.select_one("img")
            if img:
                poster = img.get("src") or img.get("data-src", "")
                if poster and not poster.startswith("http"):
                    poster = self.base_url + poster

            # href like /anime/12345/name
            if "/anime/" in href:
                aid = href.split("/anime/")[-1]
                results.append(TvShow(id=aid, title=title.strip(), poster=poster))
        return results

    async def get_home(self) -> list[Category]:
        try:
            html = await self._get(self.base_url)
            soup = BeautifulSoup(html, "lxml")
            cats = []
            # Latest episodes
            eps = []
            for el in soup.select(".ListEpisodios li, .lastEpisodes li"):
                a = el.select_one("a")
                if not a:
                    continue
                href = a.get("href", "")
                title = a.select_one(".Title") or a.select_one("h3")
                title = title.get_text(strip=True) if title else ""
                img = el.select_one("img")
                poster = img.get("src") or img.get("data-src", "") if img else ""
                if poster and not poster.startswith("http"):
                    poster = self.base_url + poster
                eps.append(TvShow(id=href, title=title, poster=poster))
            if eps:
                cats.append(Category("Últimos Episodios", eps[:20]))
            # Popular anime
            popular = self._parse_animes(soup.select(".main-carousel .carousel-item, .blVlaSuP li"))
            if popular:
                cats.append(Category("Populares", popular))
            return cats
        except Exception:
            return []

    async def search(self, query: str, page: int = 1) -> list:
        if not query:
            return [
                {"id": "accion", "name": "Acción", "type": "genre"},
                {"id": "aventura", "name": "Aventura", "type": "genre"},
                {"id": "comedia", "name": "Comedia", "type": "genre"},
                {"id": "drama", "name": "Drama", "type": "genre"},
                {"id": "fantasia", "name": "Fantasía", "type": "genre"},
                {"id": "ciencia-ficcion", "name": "Ciencia Ficción", "type": "genre"},
                {"id": "romance", "name": "Romance", "type": "genre"},
                {"id": "shounen", "name": "Shounen", "type": "genre"},
                {"id": "seinen", "name": "Seinen", "type": "genre"},
                {"id": " Ecchi", "type": "genre"},
                {"id": "misterio", "name": "Misterio", "type": "genre"},
                {"id": "horror", "name": "Horror", "type": "genre"},
            ]
        try:
            encoded = urllib.parse.quote(query)
            html = await self._get(f"{self.base_url}/browse?q={encoded}&page={page}")
            soup = BeautifulSoup(html, "lxml")
            return self._parse_animes(soup.select(".main-carousel .carousel-item, .blVlaSuP li, ul.ListAnimes li"))
        except Exception:
            return []

    async def get_movies(self, page: int = 1) -> list[Movie]:
        return []

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        try:
            html = await self._get(f"{self.base_url}/browse?page={page}")
            soup = BeautifulSoup(html, "lxml")
            return self._parse_animes(soup.select(".main-carousel .carousel-item, .blVlaSuP li, ul.ListAnimes li"))
        except Exception:
            return []

    async def get_genre(self, genre_id: str, page: int = 1) -> list:
        try:
            html = await self._get(f"{self.base_url}/browse?genre={genre_id}&page={page}")
            soup = BeautifulSoup(html, "lxml")
            return self._parse_animes(soup.select(".main-carousel .carousel-item, .blVlaSuP li, ul.ListAnimes li"))
        except Exception:
            return []

    async def get_details(self, item_id: str) -> Optional[MediaDetails]:
        try:
            url = item_id if item_id.startswith("http") else f"{self.base_url}/anime/{item_id}"
            html = await self._get(url)
            soup = BeautifulSoup(html, "lxml")

            title = soup.select_one(".TitleoF点左右seriename, h1.Title") or soup.select_one("h2.Title")
            title = title.get_text(strip=True) if title else item_id

            poster = soup.select_one(".AnimeCover img") or soup.select_one(".anime-image")
            poster = poster.get("src") if poster else None

            overview_el = soup.select_one(".Descriptionp, .description")
            overview = overview_el.get_text(strip=True) if overview_el else None

            genres = []
            for ga in soup.select(".Nvgnrs a, .gnres a"):
                genres.append(ga.get_text(strip=True))

            # Parse episodes
            episodes = []
            for ep in soup.select(".ListCaps li a, .EpsNvCAPS a"):
                href = ep.get("href", "")
                text = ep.get_text(strip=True)
                m = re.search(r"(\d+)", text)
                num = int(m.group(1)) if m else 0
                if href:
                    episodes.append(Episode(id=href, number=num, title=text))

            return MediaDetails(
                id=item_id, title=title, type="series",
                poster=poster, overview=overview, genres=genres,
                seasons=[Season(id=item_id, number=1, title="Episodios", episodes=episodes)],
            )
        except Exception:
            return None

    async def get_servers(self, movie_id: str) -> list[Server]:
        try:
            url = movie_id if movie_id.startswith("http") else f"{self.base_url}/{movie_id}"
            html = await self._get(url)
            soup = BeautifulSoup(html, "lxml")
            servers = []
            for a in soup.select("#play-video a, .RTbulPlay li a"):
                href = a.get("data-url", a.get("href", ""))
                name = a.select_one("span") or a
                name = name.get_text(strip=True) if hasattr(name, 'get_text') else str(name).strip()

                if href:
                    try:
                        decoded = base64.b64decode(href).decode("utf-8")
                        servers.append(Server(id=decoded, name=name))
                    except Exception:
                        servers.append(Server(id=href, name=name))
            return servers
        except Exception:
            return []
