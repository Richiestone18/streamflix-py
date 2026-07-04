"""
Latanime provider (Spanish anime).
Ported from streamflix-reborn/streamflix LatanimeProvider.
URL: https://latanime.org
"""
import re
import base64
import urllib.parse
from bs4 import BeautifulSoup
from ..base import BaseProvider, Movie, TvShow, Category, Server, Episode, Season, MediaDetails
from typing import Optional


class LatanimeProvider(BaseProvider):
    name = "Latanime"
    base_url = "https://latanime.org"
    language = "es"

    _GENRES = [
        "accion", "aventura", "carreras", "ciencia-ficcion", "comedia",
        "deportes", "drama", "escolares", "fantasia", "harem", "horror",
        "josei", "lucha", "magia", "mecha", "militar", "misterio", "musica",
        "psicologico", "romance", "seinen", "shojo", "shonen", "sobrenatural",
        "vampiros", "yaoi", "yuri",
    ]

    def _fix_url(self, url: str) -> str:
        if not url:
            return ""
        if url.startswith("http"):
            return url
        return self.base_url + url

    def _parse_animes(self, elements: list) -> list:
        results = []
        for el in elements:
            a = el.select_one("a")
            if not a:
                continue
            href = a.get("href", "")
            title_el = el.select_one("div.seriedetails > h3")
            title = title_el.get_text(strip=True) if title_el else ""
            img = el.select_one("img")
            poster = img.get("data-src") or img.get("src", "") if img else ""
            poster = self._fix_url(poster)
            results.append(TvShow(id=href, title=title, poster=poster))
        return results

    async def get_home(self) -> list[Category]:
        cats = []
        try:
            html = await self._get(self.base_url)
            soup = BeautifulSoup(html, "lxml")

            # Banner carousel
            banner = []
            for el in soup.select("div.carousel-item"):
                a = el.select_one("a")
                title = el.select_one("span.span-slider")
                img = el.select_one("img")
                if a and title:
                    banner_url = img.get("data-src") if img else None
                    banner.append(TvShow(
                        id=a.get("href", ""),
                        title=title.get_text(strip=True),
                        banner=self._fix_url(banner_url) if banner_url else None,
                    ))
            if banner:
                cats.append(Category("Destacados", banner))

            # Recently added
            recent = []
            for el in soup.select("h2:contains(Añadidos recientemente) + div.row div.col-6"):
                a = el.select_one("a")
                poster = el.select_one("img")
                poster_url = poster.get("data-src") if poster else ""
                title = el.select_one("h2.mt-3")
                if a and title:
                    recent.append(TvShow(
                        id=a.get("href", ""),
                        title=title.get_text(strip=True).split(" - ", 1)[-1],
                        poster=self._fix_url(poster_url) if poster_url else None,
                    ))
            if recent:
                cats.append(Category("Añadidos Recientemente", recent))
        except Exception:
            pass

        # By year
        for year in ["2026", "2025", "2024", "2023"]:
            try:
                html = await self._get(f"{self.base_url}/animes?fecha={year}")
                soup = BeautifulSoup(html, "lxml")
                shows = self._parse_animes(soup.select("div.row > div:has(a)"))
                if shows:
                    cats.append(Category(f"Animes del {year}", shows[:12]))
            except Exception:
                pass
        return cats

    async def search(self, query: str, page: int = 1) -> list:
        if not query:
            return [{"id": g, "name": g.capitalize(), "type": "genre"} for g in self._GENRES]
        try:
            html = await self._get(f"{self.base_url}/buscar?q={urllib.parse.quote(query)}")
            soup = BeautifulSoup(html, "lxml")
            return self._parse_animes(soup.select("div.row > div:has(a)"))
        except Exception:
            return []

    async def get_movies(self, page: int = 1) -> list[Movie]:
        try:
            html = await self._get(f"{self.base_url}/animes?fecha=false&genero=false&letra=false&categoria=Película&p={page}")
            soup = BeautifulSoup(html, "lxml")
            results = []
            for el in soup.select("div.row > div:has(a)"):
                a = el.select_one("a")
                title_el = el.select_one("div.seriedetails > h3")
                img = el.select_one("img")
                if a and title_el:
                    poster = img.get("data-src") or img.get("src", "") if img else ""
                    results.append(Movie(id=a.get("href", ""), title=title_el.get_text(strip=True), poster=self._fix_url(poster)))
            return results
        except Exception:
            return []

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        try:
            html = await self._get(f"{self.base_url}/animes?p={page}")
            soup = BeautifulSoup(html, "lxml")
            return self._parse_animes(soup.select("div.row > div:has(a)"))
        except Exception:
            return []

    async def get_genre(self, genre_id: str, page: int = 1) -> list:
        try:
            html = await self._get(f"{self.base_url}/genero/{genre_id}?p={page}")
            soup = BeautifulSoup(html, "lxml")
            return self._parse_animes(soup.select("div.row > div:has(a)"))
        except Exception:
            return []

    async def get_details(self, item_id: str) -> Optional[MediaDetails]:
        try:
            url = item_id if item_id.startswith("http") else f"{self.base_url}/{item_id}"
            html = await self._get(url)
            soup = BeautifulSoup(html, "lxml")

            title = soup.select_one("div.row > div > h2")
            title = title.get_text(strip=True) if title else item_id

            poster = soup.select_one("div.serieimgficha > img")
            poster = poster.get("src") if poster else None

            overview = soup.select_one("div.row > div > p.my-2")
            overview = overview.get_text(strip=True) if overview else None

            genres = []
            for ga in soup.select("div.row > div > a:has(div.btn)"):
                genres.append(ga.get_text(strip=True))

            return MediaDetails(
                id=item_id, title=title, type="series",
                poster=self._fix_url(poster) if poster else None,
                overview=overview, genres=genres,
                seasons=[Season(id=item_id, number=1, title="Episodios")],
            )
        except Exception:
            return None

    async def get_servers(self, movie_id: str) -> list[Server]:
        try:
            html = await self._get(movie_id)
            soup = BeautifulSoup(html, "lxml")
            servers = []
            for a in soup.select("li#play-video > a.play-video"):
                name = a.get_text(strip=True)
                encoded = a.get("data-player", "")
                if encoded:
                    try:
                        decoded = base64.b64decode(encoded).decode("utf-8")
                        servers.append(Server(id=decoded, name=name))
                    except Exception:
                        pass
            return servers
        except Exception:
            return []
