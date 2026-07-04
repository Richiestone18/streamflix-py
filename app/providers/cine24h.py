"""
Cine24h provider (Spanish movies/series).
Ported from streamflix-reborn/streamflix Kotlin project.
URL: https://cine24h.online
"""
import re
import base64
from bs4 import BeautifulSoup
from ..base import BaseProvider, Movie, TvShow, Category, Server, Episode, Season, MediaDetails
from typing import Optional


class Cine24hProvider(BaseProvider):
    name = "Cine24h"
    base_url = "https://cine24h.online"

    def _parse_shows(self, elements: list) -> list:
        results = []
        for el in elements:
            a = el.select_one("a")
            if not a:
                continue
            url = a.get("href", "")
            title = None
            for sel in ["h2", "h3", ".Title", ".text-md", ".name", ".poster__title"]:
                t = a.select_one(sel)
                if t and t.get_text(strip=True):
                    title = t.get_text(strip=True)
                    break
            if not title:
                for sel in ["h2", "h3", ".Title", ".name"]:
                    t = el.select_one(sel)
                    if t and t.get_text(strip=True):
                        title = t.get_text(strip=True)
                        break
            if not title:
                continue

            img = a.select_one("img") or el.select_one("img")
            poster = ""
            if img:
                poster = img.get("abs:src") or img.get("data-src") or img.get("src", "")
                poster = poster.replace("/w185/", "/w300/").replace("/w92/", "/w300/")

            if "/peliculas/" in url or "/movies/" in url:
                mid = url.split("/peliculas/")[-1].split("/movies/")[-1].rstrip("/")
                results.append(Movie(id=mid, title=title, poster=poster))
            elif "/series/" in url:
                sid = url.split("/series/")[-1].rstrip("/")
                results.append(TvShow(id=sid, title=title, poster=poster))
        # Deduplicate by id
        seen = set()
        unique = []
        for r in results:
            if r.id not in seen:
                seen.add(r.id)
                unique.append(r)
        return unique

    async def get_home(self) -> list[Category]:
        cats = []
        try:
            html = await self._get(f"{self.base_url}/release/2025/")
            banner = self._parse_shows(BeautifulSoup(html, "lxml").select(
                "article.TPost, li.TPostMv article, .TPost, .poster, .grid-item, .item, article[class*='post-']"
            ))
            if banner:
                cats.append(Category("Estrenos 2025", banner[:20]))
        except Exception:
            pass
        try:
            html = await self._get(f"{self.base_url}/estrenos/?type=movies")
            movies = [m for m in self._parse_shows(BeautifulSoup(html, "lxml").select(
                "article.TPost, li.TPostMv article, .TPost, .poster, .grid-item, .item, article[class*='post-']"
            )) if isinstance(m, Movie)]
            if movies:
                cats.append(Category("Películas", movies))
        except Exception:
            pass
        try:
            html = await self._get(f"{self.base_url}/estrenos/?type=series")
            series = [s for s in self._parse_shows(BeautifulSoup(html, "lxml").select(
                "article.TPost, li.TPostMv article, .TPost, .poster, .grid-item, .item, article[class*='post-']"
            )) if isinstance(s, TvShow)]
            if series:
                cats.append(Category("Series", series))
        except Exception:
            pass
        return cats

    async def search(self, query: str, page: int = 1) -> list:
        if not query:
            genres = ["accion", "animacion", "anime", "aventura", "belica",
                       "ciencia-ficcion", "comedia", "crimen", "documental", "drama",
                       "familia", "fantasia", "historia", "misterio", "musica",
                       "romance", "suspense", "terror", "western"]
            return [{"id": f"category/{g}/", "name": g.replace("-", " ").capitalize(), "type": "genre"}
                    for g in genres]
        try:
            import urllib.parse
            html = await self._get(f"{self.base_url}/?s={urllib.parse.quote(query)}&paged={page}")
            return self._parse_shows(BeautifulSoup(html, "lxml").select(
                "article.TPost, li.TPostMv article, .TPost, .poster, .grid-item, .item, article[class*='post-']"
            ))
        except Exception:
            return []

    async def get_movies(self, page: int = 1) -> list[Movie]:
        try:
            html = await self._get(f"{self.base_url}/peliculas/page/{page}")
            shows = self._parse_shows(BeautifulSoup(html, "lxml").select(
                "article.TPost, li.TPostMv article, .TPost, .poster, .grid-item, .item, article[class*='post-']"
            ))
            return [s for s in shows if isinstance(s, Movie)]
        except Exception:
            return []

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        try:
            html = await self._get(f"{self.base_url}/series/page/{page}")
            shows = self._parse_shows(BeautifulSoup(html, "lxml").select(
                "article.TPost, li.TPostMv article, .TPost, .poster, .grid-item, .item, article[class*='post-']"
            ))
            return [s for s in shows if isinstance(s, TvShow)]
        except Exception:
            return []

    async def get_genre(self, genre_id: str, page: int = 1) -> list:
        try:
            html = await self._get(f"{self.base_url}/{genre_id}page/{page}")
            return self._parse_shows(BeautifulSoup(html, "lxml").select(
                "article.TPost, li.TPostMv article, .TPost, .poster, .grid-item, .item, article[class*='post-']"
            ))
        except Exception:
            return []

    async def get_details(self, item_id: str) -> Optional[MediaDetails]:
        try:
            is_movie = True
            if item_id.startswith("http"):
                url = item_id
            else:
                url = f"{self.base_url}/peliculas/{item_id}"
            html = await self._get(url)
            soup = BeautifulSoup(html, "lxml")

            title_el = soup.select_one(".TPost header .Title, h1")
            title = title_el.get_text(strip=True) if title_el else item_id

            desc_el = soup.select_one(".TPost .Description, .Description, .page__text")
            overview = desc_el.get_text(strip=True) if desc_el else None

            poster_el = soup.select_one(".TPost .Image img, .pmovie__poster img")
            poster = None
            if poster_el:
                poster = poster_el.get("abs:src") or poster_el.get("src", "")
                poster = poster.replace("/w185/", "/w500/")

            genres = []
            for ga in soup.select(".TPost .Description .Genre a, a[href*='/category/']"):
                genres.append(ga.get_text(strip=True))

            return MediaDetails(
                id=item_id, title=title, type="movie" if is_movie else "series",
                poster=poster, overview=overview, genres=genres,
            )
        except Exception:
            return None

    async def get_servers(self, movie_id: str) -> list[Server]:
        try:
            if movie_id.startswith("http"):
                url = movie_id
            else:
                url = f"{self.base_url}/peliculas/{movie_id}"
            html = await self._get(url)
            soup = BeautifulSoup(html, "lxml")
            servers = []
            for li in soup.select("ul.optnslst li[data-src], .optnslst li"):
                data_src = li.get("data-src", "")
                if not data_src:
                    continue
                try:
                    decoded = base64.b64decode(data_src).decode("utf-8")
                except Exception:
                    continue
                if decoded:
                    # Try to get iframe URL
                    try:
                        iframe_html = await self._get(decoded)
                        iframe_soup = BeautifulSoup(iframe_html, "lxml")
                        iframe = iframe_soup.select_one("iframe")
                        if iframe and iframe.get("src"):
                            servers.append(Server(id=iframe["src"], name=decoded.split("//")[-1].split("/")[0]))
                        else:
                            servers.append(Server(id=decoded, name=decoded.split("//")[-1].split("/")[0]))
                    except Exception:
                        servers.append(Server(id=decoded, name=decoded.split("//")[-1].split("/")[0]))
            return servers
        except Exception:
            return []
