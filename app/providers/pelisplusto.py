"""
Pelisplusto provider (Spanish movies/series).
"""
import json
from bs4 import BeautifulSoup
from ..base import BaseProvider, Movie, TvShow, Category, Server


class PelisplustoProvider(BaseProvider):
    name = "Pelisplusto"
    base_url = "https://pelisplus.to"

    def _extract_json_data(self, html: str) -> dict | None:
        """Extract Apollo GraphQL state from the page."""
        soup = BeautifulSoup(html, "lxml")
        for script in soup.select("script"):
            if "window.__NUXT__" in script.text or "window.__INITIAL_STATE__" in script.text:
                try:
                    data = script.text.split("=", 1)[1].strip().rstrip(";")
                    return json.loads(data)
                except Exception:
                    pass
        return None

    def _parse_list(self, soup: BeautifulSoup) -> list:
        results = []
        for article in soup.select("article.TPost, li.TPostMv, .TPost .TPostMv"):
            a = article.select_one("a")
            if not a:
                continue
            href = a.get("href", "")
            title = a.get("title") or article.select_one(".Title, h3, h2")
            title = title.get_text(strip=True) if title else ""
            if not title:
                continue
            img = article.select_one("img")
            poster = img.get("src") or img.get("data-src", "") if img else ""

            if any(x in href for x in ["/pelicula", "/movie"]):
                results.append(Movie(id=href, title=title, poster=poster))
            elif any(x in href for x in ["/serie", "/series", "/show"]):
                results.append(TvShow(id=href, title=title, poster=poster))
            else:
                results.append(Movie(id=href, title=title, poster=poster))
        return results

    async def get_home(self) -> list[Category]:
        html = await self._get(self.base_url)
        soup = BeautifulSoup(html, "lxml")
        cats = []
        for section in soup.select("section, .TPostList, div[class*='section']"):
            title_el = section.select_one("h1, h2, h3, .Title, .section-title")
            if not title_el:
                continue
            items = self._parse_list(section)
            if items:
                cats.append(Category(title_el.get_text(strip=True), items))
        if not cats:
            items = self._parse_list(soup)
            if items:
                cats.append(Category("Películas", items))
        return cats

    async def search(self, query: str, page: int = 1) -> list:
        if page > 1:
            return []
        html = await self._get(f"{self.base_url}/search?q={query}")
        soup = BeautifulSoup(html, "lxml")
        return self._parse_list(soup)

    async def get_movies(self, page: int = 1) -> list[Movie]:
        url = f"{self.base_url}/peliculas" if page == 1 else f"{self.base_url}/peliculas/page/{page}"
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        return [i for i in self._parse_list(soup) if isinstance(i, Movie)]

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        url = f"{self.base_url}/series" if page == 1 else f"{self.base_url}/series/page/{page}"
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        return [i for i in self._parse_list(soup) if isinstance(i, TvShow)]

    async def get_servers(self, movie_id: str) -> list[Server]:
        html = await self._get(movie_id)
        soup = BeautifulSoup(html, "lxml")
        servers = []

        # Try to extract from NUXT data
        data = self._extract_json_data(html)
        if data:
            # Navigate the state to find iframes/servers
            try:
                servers_raw = data.get("state", {}).get("servers", [])
                if not servers_raw:
                    servers_raw = data.get("servers", [])
                for srv in servers_raw:
                    if isinstance(srv, dict):
                        url = srv.get("url") or srv.get("src") or srv.get("code", "")
                        name = srv.get("name") or srv.get("title", "Server")
                        if url:
                            servers.append(Server(id=url, name=name))
            except Exception:
                pass

        # Try HTML selectors
        if not servers:
            for iframe in soup.select("iframe[src]"):
                src = iframe.get("src", "")
                if src.startswith("http"):
                    servers.append(Server(id=src))

            for li in soup.select("ul.optnslst li[data-src], .optnslst li[data-src]"):
                import base64
                raw = li.get("data-src", "")
                try:
                    url = base64.b64decode(raw).decode()
                    if url.startswith("http"):
                        servers.append(Server(id=url, name=li.get_text(strip=True) or "Server"))
                except Exception:
                    pass
        return servers