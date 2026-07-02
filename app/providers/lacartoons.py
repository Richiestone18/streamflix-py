"""
LaCartoons provider (Spanish cartoons). Only TV shows/series, no movies.
"""
import re
from bs4 import BeautifulSoup
from ..base import BaseProvider, Movie, TvShow, Category, Server


class LaCartoonsProvider(BaseProvider):
    name = "LaCartoons"
    base_url = "https://www.lacartoons.com"

    def _extract_title(self, text: str) -> str:
        # Text format: "SeriesNameCategoryNetworkYear" 
        # e.g. "2 Perros TontosCartoon Network19937"
        # Remove trailing year+digits
        text = re.sub(r'\d+$', '', text).strip()
        # Remove known network names at the end
        for network in ['Cartoon Network', 'Nickelodeon', 'Disney XD', 'Disney Channel',
                        'Disney Junior', 'Boomerang', 'PBS Kids', 'Netflix', 'Amazon Prime Video',
                        'HBO Max', 'Hulu', 'Disney+', 'Crunchyroll']:
            if text.endswith(network):
                text = text[:-len(network)].strip()
                break
        return text

    async def get_home(self) -> list[Category]:
        html = await self._get(self.base_url)
        soup = BeautifulSoup(html, "lxml")
        cats = []
        for section in soup.select("section.seccion"):
            title_el = section.select_one("h1, h2, h3")
            cat_title = title_el.get_text(strip=True) if title_el else "Series"
            shows = []
            for a in section.select("a[href*='/serie/']"):
                href = a.get("href", "")
                if not href.startswith("http"):
                    href = self.base_url + href
                img = a.select_one("img")
                title = self._extract_title(a.get_text(strip=True))
                poster = img.get("src", "") if img else ""
                if not poster.startswith("http"):
                    poster = self.base_url + poster
                shows.append(TvShow(id=href, title=title, poster=poster))
            if shows:
                cats.append(Category(cat_title, shows))
        return cats

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        url = f"{self.base_url}/?page={page}" if page > 1 else self.base_url
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        results = []
        seen = set()
        for a in soup.select("a[href*='/serie/']"):
            href = a.get("href", "")
            if href in seen:
                continue
            seen.add(href)
            if not href.startswith("http"):
                href = self.base_url + href
            img = a.select_one("img")
            title = self._extract_title(a.get_text(strip=True))
            poster = img.get("src", "") if img else ""
            if not poster.startswith("http"):
                poster = self.base_url + poster
            results.append(TvShow(id=href, title=title, poster=poster))
        return results

    async def get_movies(self, page: int = 1) -> list[Movie]:
        return []

    async def get_servers(self, movie_id: str) -> list[Server]:
        html = await self._get(movie_id)
        soup = BeautifulSoup(html, "lxml")
        servers = []
        # Check for episodes first
        episodes = soup.select("a[href*='/serie/capitulo/']")
        if episodes:
            import urllib.parse
            # Return episodes as server options
            for ep in episodes[:1]:  # Just first episode
                ep_url = ep.get("href", "")
                if not ep_url.startswith("http"):
                    ep_url = "https://www.lacartoons.com" + ep_url
                ep_html = await self._get(ep_url)
                ep_soup = BeautifulSoup(ep_html, "lxml")
                for iframe in ep_soup.select("iframe[src]"):
                    src = iframe.get("src", "")
                    if src.startswith("http"):
                        servers.append(Server(id=src, name=ep.get_text(strip=True)[:30] or "Episode"))
                for video in ep_soup.select("video source[src], video[src]"):
                    src = video.get("src", "")
                    if src:
                        servers.append(Server(id=src, name="Video"))
        for iframe in soup.select("iframe[src]"):
            src = iframe.get("src", "")
            if src.startswith("http"):
                servers.append(Server(id=src, name=iframe.get("title", "Player") or "Player"))
        for video in soup.select("video source[src], video[src]"):
            src = video.get("src", "")
            if src:
                servers.append(Server(id=src, name="Video"))
        return servers