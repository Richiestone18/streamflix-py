"""
AnimeFLV provider (Spanish anime). Only series, no movies.
"""
import json
import re
from bs4 import BeautifulSoup
from ..base import BaseProvider, Movie, TvShow, Category, Server


class AnimeFLVProvider(BaseProvider):
    name = "AnimeFLV"
    base_url = "https://animeflv.net"
    language = "es"

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        url = f"{self.base_url}/browse?page={page}"
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        results = []
        seen = set()
        for a in soup.select("a[href*='/anime/']"):
            href = a.get("href", "")
            if href in seen or href == "/anime/" or not href:
                continue
            seen.add(href)
            if not href.startswith("http"):
                href = self.base_url + href
            img = a.select_one("img")
            title = img.get("alt", "") if img and img.get("alt") else a.get("title", "")
            if not title or title == "VER ANIME":
                continue
            poster = img.get("src") or img.get("data-src", "") if img else ""
            if poster.startswith("//"):
                poster = "https:" + poster
            results.append(TvShow(id=href, title=title, poster=poster))
        return results

    async def get_movies(self, page: int = 1) -> list[Movie]:
        return []

    async def get_servers(self, movie_id: str) -> list[Server]:
        html = await self._get(movie_id)
        soup = BeautifulSoup(html, "lxml")
        servers = []

        # Check for episodes list first
        episodes = soup.select("a[href*='/ver/']")
        if not episodes:
            return []

        # Get the first episode
        ep_url = episodes[0].get("href", "")
        if not ep_url.startswith("http"):
            ep_url = self.base_url + ep_url
        ep_html = await self._get(ep_url)
        ep_soup = BeautifulSoup(ep_html, "lxml")

        # Look for var videos = [...] in scripts (AnimeFLV format)
        for script in ep_soup.select("script"):
            if not script.text:
                continue
            m = re.search(r'var\s+videos\s*=\s*(\[[^\]]+\])', script.text)
            if m:
                try:
                    videos = json.loads(m.group(1))
                    for v in videos:
                        if isinstance(v, dict):
                            url = v.get("url", "")
                            if url:
                                servers.append(Server(id=url, name=v.get("title", v.get("server", "Server"))))
                except:
                    pass

        # Fallback: look for URL patterns
        if not servers:
            for script in ep_soup.select("script"):
                if not script.text:
                    continue
                for m in re.finditer(r'"(?:url|src|file)"\s*:\s*"([^"]+)"', script.text):
                    url = m.group(1)
                    if any(ext in url for ext in [".mp4", ".m3u8"]):
                        servers.append(Server(id=url, name="Video"))

        for iframe in ep_soup.select("iframe[src]"):
            src = iframe.get("src", "")
            if src.startswith("http"):
                servers.append(Server(id=src, name=iframe.get("title", "Player") or "Player"))

        return servers