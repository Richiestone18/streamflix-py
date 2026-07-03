"""
JKanime provider (Spanish anime). Only series, no movies.
Uses the /directorio endpoint with embedded JSON for anime listing (4808 animes).
Episodes via AJAX: POST /ajax/episodes/{anime_id}/{page} with CSRF token.
Servers: iframe URLs from inline scripts (jkplayer/um, umv, jk).
"""
import re
import json
from bs4 import BeautifulSoup
from typing import Optional
from ..base import BaseProvider, Movie, TvShow, Server, MediaDetails, Season, Episode


class JKanimeProvider(BaseProvider):
    name = "JKanime"
    base_url = "https://jkanime.net"
    language = "es"

    def __init__(self):
        self.http = None  # Use cloudscraper directly
        import cloudscraper
        self.scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False},
            delay=2,
        )
        self._csrf = None

    def _get_sync(self, url: str) -> str:
        """Synchronous fetch with cloudscraper."""
        return self.scraper.get(url, timeout=15).text

    async def _get(self, url: str) -> str:
        """Async wrapper using cloudscraper in thread."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_sync, url)

    async def _get_csrf(self) -> str:
        """Get CSRF token from the home page."""
        if self._csrf:
            return self._csrf
        html = await self._get(self.base_url + "/")
        m = re.search(r'csrf-token.*?content=["\']([^"\']+)', html)
        if m:
            self._csrf = m.group(1)
        return self._csrf or ""

    async def _post_ajax(self, url: str, data: dict = None) -> str:
        """POST to AJAX endpoint with CSRF token."""
        import asyncio
        csrf = await self._get_csrf()
        headers = {
            "X-CSRF-TOKEN": csrf,
            "X-Requested-With": "XMLHttpRequest",
        }

        def _do_post():
            return self.scraper.post(url, data=data or {}, headers=headers, timeout=15).text

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _do_post)

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        """Get anime list from /directorio?p=N (30 per page, 161 pages, 4808 total)."""
        html = await self._get(f"{self.base_url}/directorio?p={page}")
        m = re.search(r'var\s+animes\s*=\s*(\{.*?\});\s', html, re.S)
        if not m:
            return []
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            return []

        animes = data.get("data", [])
        results = []
        for a in animes:
            title = a.get("title", "")
            slug = a.get("slug", "")
            url = a.get("url", f"{self.base_url}/{slug}/")
            poster = a.get("image", "")
            overview = a.get("synopsis", "")
            results.append(TvShow(
                id=url,
                title=title,
                poster=poster,
                overview=overview[:200] if overview else None,
            ))
        return results

    async def get_movies(self, page: int = 1) -> list[Movie]:
        """JKanime has some movies/Peliculas. Filter from directorio."""
        html = await self._get(f"{self.base_url}/directorio?p={page}")
        m = re.search(r'var\s+animes\s*=\s*(\{.*?\});\s', html, re.S)
        if not m:
            return []
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            return []

        animes = data.get("data", [])
        results = []
        for a in animes:
            anime_type = a.get("type", "")
            if anime_type == "Pelicula":
                title = a.get("title", "")
                url = a.get("url", "")
                poster = a.get("image", "")
                results.append(Movie(id=url, title=title, poster=poster))
        return results

    async def search(self, query: str, page: int = 1) -> list:
        """Search via ajax_search endpoint."""
        if not query:
            return [
                {"id": "type=TV", "name": "Series (TV)", "type": "genre"},
                {"id": "type=Pelicula", "name": "Peliculas", "type": "genre"},
                {"id": "type=OVA", "name": "OVAs", "type": "genre"},
                {"id": "type=Especial", "name": "Especiales", "type": "genre"},
                {"id": "type=ONA", "name": "ONAs", "type": "genre"},
            ]

        result_text = await self._post_ajax(
            f"{self.base_url}/ajax_search",
            data={"q": query},
        )
        try:
            data = json.loads(result_text)
        except json.JSONDecodeError:
            return []

        results = []
        for a in data:
            slug = a.get("slug", "")
            url = a.get("url", f"{self.base_url}/{slug}/")
            title = a.get("title", "")
            poster = a.get("thumbnail", "")
            if poster and not poster.startswith("http"):
                poster = "https://cdn.jkdesa.com/assets/images/animes/thumbnail/" + poster.split("/")[-1]
            results.append(TvShow(id=url, title=title, poster=poster))
        return results

    async def get_servers(self, movie_id: str) -> list[Server]:
        """Get servers from an episode page. movie_id is the episode URL."""
        html = await self._get(movie_id)

        servers = []
        # Find the video[] array in inline scripts - server iframe URLs
        for m in re.finditer(r"""video\[\d+\]\s*=\s*'<iframe[^>]*src=["']([^"']+)["']""", html):
            url = m.group(1).replace("&", "&")
            if "/jkplayer/um" in url:
                name = "Desu"
            elif "/jkplayer/umv" in url:
                name = "Magi"
            elif "/jkplayer/jk" in url:
                name = "Desuka"
            else:
                name = "Server"
            servers.append(Server(id=url, name=name))

        # Fallback: any iframe with jkplayer
        if not servers:
            for m in re.finditer(r"""<iframe[^>]*src=["']([^"']*jkplayer[^"']*)["']""", html):
                url = m.group(1).replace("&", "&")
                servers.append(Server(id=url, name="JK Player"))

        return servers

    async def get_details(self, item_id: str) -> Optional[MediaDetails]:
        """Get anime details including seasons and episodes."""
        html = await self._get(item_id)
        soup = BeautifulSoup(html, "lxml")

        # Title from og:title or h1
        title = ""
        og_title = soup.select_one('meta[property="og:title"]')
        if og_title:
            title = og_title.get("content", "").strip()
        if not title:
            h1 = soup.select_one("h1, h2, .title")
            if h1:
                title = h1.get_text(strip=True)
        if title:
            title = re.sub(r'\s*\|\s*JKanime.*$', '', title, flags=re.I).strip()
            title = re.sub(r'\s*\|\s*JkAnime.*$', '', title, flags=re.I).strip()

        # Poster from og:image
        poster = None
        og_img = soup.select_one('meta[property="og:image"]')
        if og_img:
            poster = og_img.get("content", "").strip()

        # Synopsis
        overview = None
        og_desc = soup.select_one('meta[name="description"], meta[property="og:description"]')
        if og_desc:
            overview = og_desc.get("content", "").strip()

        # Genres
        genres = []
        for a in soup.select('a[href*="/genero/"]'):
            g = a.get_text(strip=True)
            if g:
                genres.append(g)

        # Get anime_id from data-anime attribute
        anime_id = None
        m = re.search(r"""data-anime=["'](\d+)["']""", html)
        if m:
            anime_id = m.group(1)
        if not anime_id:
            m2 = re.search(r'/ajax/episodes/(\d+)/', html)
            if m2:
                anime_id = m2.group(1)

        # Get episodes via AJAX
        seasons = []
        if anime_id:
            try:
                ajax_text = await self._post_ajax(
                    f"{self.base_url}/ajax/episodes/{anime_id}/1"
                )
                ep_data = json.loads(ajax_text)
                episodes_data = ep_data.get("data", [])
                total_pages = ep_data.get("last_page", 1)

                all_episodes = list(episodes_data)
                for p in range(2, min(total_pages + 1, 50)):
                    try:
                        more_text = await self._post_ajax(
                            f"{self.base_url}/ajax/episodes/{anime_id}/{p}"
                        )
                        more_data = json.loads(more_text)
                        all_episodes.extend(more_data.get("data", []))
                    except Exception:
                        break

                episodes = []
                slug = item_id.rstrip("/").split("/")[-1]
                for ep in all_episodes:
                    ep_num = ep.get("number", 0)
                    ep_title = ep.get("title", f"Episodio {ep_num}")
                    ep_url = f"{self.base_url}/{slug}/{ep_num}/"
                    episodes.append(Episode(
                        id=ep_url,
                        number=ep_num,
                        season=1,
                        title=ep_title,
                    ))

                if episodes:
                    episodes.reverse()
                    seasons.append(Season(
                        id=f"{anime_id}_s1",
                        number=1,
                        title="Temporada 1",
                        episodes=episodes,
                    ))
            except Exception:
                pass

        details = MediaDetails(
            id=item_id,
            title=title or "Anime",
            type="series",
            poster=poster,
            overview=overview,
            genres=genres,
            seasons=seasons,
        )
        return details
