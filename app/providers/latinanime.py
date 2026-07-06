"""
LatinAnime provider (Spanish anime) — only anime/series, no movies.
"""
import base64, re
from bs4 import BeautifulSoup
from ..base import BaseProvider, Movie, TvShow, Category, Server


class LatinAnimeProvider(BaseProvider):
    name = "LatinAnime"
    base_url = "https://latanime.org"

    def _parse(self, soup: BeautifulSoup) -> list:
        results = []
        for card in soup.select("div.row > div[class*='col-']"):
            a = card.select_one("a[href*='/anime/']")
            if not a:
                continue
            href = a.get("href", "")
            if not href.startswith("http"):
                href = self.base_url + href
            img = card.select_one("img")
            title = img.get("alt", "") if img else a.get("title", a.get_text(strip=True))
            poster = img.get("src") or img.get("data-src", "") if img else ""
            if poster.startswith("//"):
                poster = "https:" + poster
            if not title or "/login" in href or "/register" in href:
                continue
            results.append(TvShow(id=href, title=title, poster=poster))
        return results

    async def get_home(self) -> list[Category]:
        try:
            tv = await self.get_tv_shows()
            if tv:
                return [Category("Animes", tv)]
            return []
        except Exception:
            return []

    async def get_movies(self, page: int = 1) -> list[Movie]:
        # LatinAnime is anime-only, no movies
        return []

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        url = f"{self.base_url}/animes" if page == 1 else f"{self.base_url}/animes/page/{page}"
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        return [s for s in self._parse(soup) if isinstance(s, TvShow)]

    async def get_servers(self, movie_id: str) -> list[Server]:
        html = await self._get(movie_id)
        soup = BeautifulSoup(html, "lxml")
        servers = []
        for iframe in soup.select("iframe[src]"):
            src = iframe.get("src", "")
            if src.startswith("http"):
                servers.append(Server(id=src, name=iframe.get("title", "Server") or "Server"))
        for el in soup.select("[data-player], [data-src]"):
            src = el.get("data-player") or el.get("data-src") or ""
            if src.startswith("http"):
                servers.append(Server(id=src, name="Player"))
        for script in soup.select("script"):
            if not script.text: continue
            for m in re.finditer(r'data-src=["\']([^"\']+)["\']', script.text):
                try:
                    decoded = base64.b64decode(m.group(1)).decode()
                    if decoded.startswith("http"):
                        servers.append(Server(id=decoded, name="Server"))
                except Exception:
                    pass
        return servers