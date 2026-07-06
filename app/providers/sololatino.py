"""
SoloLatino provider (Spanish movies/series).
"""
import json
import base64
import re
from bs4 import BeautifulSoup
from ..base import BaseProvider, Movie, TvShow, Category, Server


class SoloLatinoProvider(BaseProvider):
    name = "SoloLatino"
    base_url = "https://sololatino.net"

    def _parse(self, soup: BeautifulSoup) -> list:
        results = []
        for card in soup.select("div.movies-grid div.card"):
            a = card.select_one("a[href*='/pelicula/'], a[href*='/serie/']")
            if not a:
                continue
            href = a.get("href", "")
            if not href.startswith("http"):
                href = self.base_url + href
            img = card.select_one("img.card__poster")
            title = img.get("alt", "") if img else a.get("title", "")
            poster = img.get("src") or img.get("data-src", "") if img else ""
            if poster.startswith("//"):
                poster = "https:" + poster
            if "/serie/" in href:
                results.append(TvShow(id=href, title=title, poster=poster))
            else:
                results.append(Movie(id=href, title=title, poster=poster))
        return results

    async def get_home(self) -> list[Category]:
        try:
            movies = await self.get_movies()
            if movies:
                return [Category("Películas", movies)]
            return []
        except Exception:
            return []

    async def get_movies(self, page: int = 1) -> list[Movie]:
        url = f"{self.base_url}/peliculas" if page == 1 else f"{self.base_url}/peliculas/page/{page}"
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        return [m for m in self._parse(soup) if isinstance(m, Movie)]

    async def get_servers(self, movie_id: str) -> list[Server]:
        # 1. Get the page HTML
        html = await self._get(movie_id)
        soup = BeautifulSoup(html, "lxml")

        # 2. Find server buttons with player tokens
        btns = soup.select("button[data-player-token]")
        if not btns:
            return []

        # 3. Get CSRF cookie first (synchronous but fine for a few calls)
        import httpx
        with httpx.Client() as client:
            client.get(f"{self.base_url}/sanctum/csrf-cookie", headers={"Referer": movie_id})
            xsrf = None
            for c in client.cookies.jar:
                if c.name == "XSRF-TOKEN":
                    from urllib.parse import unquote
                    xsrf = unquote(c.value)
                    break

            servers = []
            headers = {
                "Referer": movie_id,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            if xsrf:
                headers["X-XSRF-TOKEN"] = xsrf

            for btn in btns:
                token = btn.get("data-player-token", "")
                if not token:
                    continue
                try:
                    resp = client.post(
                        f"{self.base_url}/api/player-url",
                        json={"t": token},
                        headers=headers,
                        timeout=10
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        url = data.get("url", "")
                        if url:
                            name = btn.get_text(strip=True) or "Server"
                            servers.append(Server(id=url, name=name))
                except Exception:
                    pass
            return servers