"""
Pelisplusto provider — now redirects to TioPlus.app.
Spanish movies/series/animes/doramas.
"""
import base64
from bs4 import BeautifulSoup
from ..base import BaseProvider, Movie, TvShow, Category, Server


class PelisplustoProvider(BaseProvider):
    name = "Pelisplusto"
    base_url = "https://pelisplus.to"

    def _parse(self, soup: BeautifulSoup) -> list:
        results = []
        for article in soup.select("article.item"):
            a = article.select_one("a.itemA")
            if not a:
                continue
            href = a.get("href", "")
            if not href.startswith("http"):
                href = self.base_url + href
            img = article.select_one("img")
            title = img.get("alt", "") if img else ""
            poster = img.get("data-src") or img.get("src", "") if img else ""
            if not title:
                continue
            if "/serie/" in href or "/dorama/" in href or "/anime/" in href:
                results.append(TvShow(id=href, title=title, poster=poster))
            else:
                results.append(Movie(id=href, title=title, poster=poster))
        return results

    async def get_home(self) -> list[Category]:
        html = await self._get(self.base_url)
        soup = BeautifulSoup(html, "lxml")
        cats = []
        # Slider / featured
        featured = []
        for article in soup.select("article:not(.item)"):
            a = article.select_one("a[href*='/pelicula/'], a[href*='/serie/']")
            if not a:
                continue
            href = a.get("href", "")
            if not href.startswith("http"):
                href = self.base_url + href
            img = a.select_one("img") or article.select_one("img")
            title = img.get("alt", "") if img else a.get_text(strip=True)
            poster = img.get("data-src") or img.get("src", "") if img else ""
            if title and "/pelicula/" in href:
                featured.append(Movie(id=href, title=title, poster=poster))
        # Latest items
        latest = self._parse(soup)
        if featured:
            cats.append(Category("Destacados", featured))
        if latest:
            cats.append(Category("Últimos", latest))
        return cats

    async def search(self, query: str, page: int = 1) -> list:
        if not query:
            return [
                {"id": "peliculas", "name": "Películas", "type": "genre"},
                {"id": "series", "name": "Series", "type": "genre"},
                {"id": "doramas", "name": "Doramas", "type": "genre"},
                {"id": "animes", "name": "Animes", "type": "genre"},
            ]
        if page > 1:
            return []
        html = await self._get(f"{self.base_url}/search/{query}")
        soup = BeautifulSoup(html, "lxml")
        return self._parse(soup)

    async def get_movies(self, page: int = 1) -> list[Movie]:
        url = f"{self.base_url}/peliculas?page={page}"
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        return [m for m in self._parse(soup) if isinstance(m, Movie)]

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        url = f"{self.base_url}/series?page={page}"
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        return [s for s in self._parse(soup) if isinstance(s, TvShow)]

    async def get_genre(self, genre_id: str, page: int = 1) -> list:
        genre_id = genre_id.rstrip("/")
        url = f"{self.base_url}/{genre_id}?page={page}"
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        return self._parse(soup)

    async def get_servers(self, movie_id: str) -> list[Server]:
        html = await self._get(movie_id)
        soup = BeautifulSoup(html, "lxml")
        servers = []

        # TioPlus: li with data-server attribute (encrypted)
        for li in soup.select("li[data-server]"):
            data_server = li.get("data-server", "")
            if not data_server:
                continue
            name = li.get_text(strip=True)
            # Remove "Reproducir" and extra text
            name = name.replace("Reproducir", "").strip()
            if not name:
                name = "Server"
            # Build player URL: /player/{btoa(data_server)}
            encoded = base64.b64encode(data_server.encode()).decode()
            player_url = f"{self.base_url}/player/{encoded}"
            servers.append(Server(id=player_url, name=name))

        # Fallback: direct iframes
        if not servers:
            for iframe in soup.select("iframe[src]"):
                src = iframe.get("src", "")
                if src.startswith("http"):
                    servers.append(Server(id=src, name=iframe.get("title", "Player") or "Player"))

        return servers
