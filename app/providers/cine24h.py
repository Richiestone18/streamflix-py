"""
Cine24h provider (Spanish movies/series).
"""
import base64
from bs4 import BeautifulSoup
from ..base import BaseProvider, Movie, TvShow, Category, Server


class Cine24hProvider(BaseProvider):
    name = "Cine24h"
    base_url = "https://cine24h.online"

    def _parse_list(self, soup: BeautifulSoup) -> list:
        results = []
        for article in soup.select("article.item, article.TPost, li.TPostMv"):
            a = article.select_one("a")
            if not a:
                continue
            href = a.get("href", "")
            title = a.get("title") or article.select_one(".Title, h3, h2")
            if title:
                title = title.get_text(strip=True)
            if not title:
                continue
            img = article.select_one("img")
            poster = img.get("src") or img.get("data-src", "") if img else ""

            if "/pelicula" in href or "/movie" in href:
                results.append(Movie(id=href, title=title, poster=poster))
            elif "/serie" in href or "/series" in href or "/show" in href:
                results.append(TvShow(id=href, title=title, poster=poster))
            else:
                results.append(Movie(id=href, title=title, poster=poster))
        return results

    async def get_home(self) -> list[Category]:
        html = await self._get(self.base_url)
        soup = BeautifulSoup(html, "lxml")
        cats = []
        for section in soup.select("section, .TPostMv, .sect"):
            title_el = section.select_one("h1, h2, h3, .Title, .section-title")
            if not title_el:
                continue
            items = self._parse_list(section)
            if items:
                cats.append(Category(title_el.get_text(strip=True), items))
        if not cats:
            items = self._parse_list(soup)
            if items:
                cats.append(Category("Últimos estrenos", items))
        return cats

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
        url = movie_id
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        servers = []

        # Try ul.optnslst li[data-src]
        for li in soup.select("ul.optnslst li, .optnslst li"):
            data_src = li.get("data-src", "")
            if data_src:
                try:
                    decoded = base64.b64decode(data_src).decode()
                except Exception:
                    continue
                info = li.get_text(strip=True) or "Server"
                if decoded.startswith("http"):
                    servers.append(Server(id=decoded, name=info))

        # Try table-based layout (div.TPTblCn.LnksTb)
        if not servers:
            for row in soup.select("div.TPTblCn.LnksTb table tbody tr, table.tablesorter tbody tr"):
                cols = row.select("td")
                if len(cols) >= 5:
                    link = cols[1].select_one("a")
                    if link:
                        url2 = link.get("href", "")
                        name = cols[0].get_text(strip=True) or "Server"
                        if url2:
                            servers.append(Server(id=url2, name=name))
        return servers