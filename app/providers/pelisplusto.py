"""
Pelisplusto provider — now redirects to TioPlus.app.
Spanish movies/series/animes/doramas.
"""
import base64
import re
from bs4 import BeautifulSoup
from ..base import BaseProvider, Movie, TvShow, Category, Server, Episode, Season, MediaDetails
from typing import Optional


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

    async def get_details(self, item_id: str) -> Optional[MediaDetails]:
        html = await self._get(item_id)
        soup = BeautifulSoup(html, "lxml")

        is_series = "/serie/" in item_id or "/anime/" in item_id
        details = MediaDetails(
            id=item_id,
            title="",
            type="series" if is_series else "movie",
        )

        # Title from h1.slugh1
        h1 = soup.select_one("h1.slugh1, h1")
        if h1:
            details.title = h1.get_text(strip=True)

        # Poster / backdrop from div.bg background-image
        bg = soup.select_one("div.bg[style]")
        if bg:
            style = bg.get("style", "")
            m = re.search(r"url\(['\"]?([^'\")]+)['\"]?\)", style)
            if m:
                details.banner = m.group(1)
                details.poster = m.group(1).replace("w1280", "w500")

        # Overview from div.description p
        desc = soup.select_one("div.description p")
        if desc:
            details.overview = desc.get_text(strip=True)

        # Genres - only from the article content, not sidebar/footer
        for a in soup.select("article a[href*='/genero/']"):
            g = a.get_text(strip=True)
            if g and g not in details.genres:
                details.genres.append(g)

        # Year
        year_a = soup.select_one('a[href*="/year/"]')
        if year_a:
            details.year = year_a.get_text(strip=True)

        # Rating
        for span in soup.select("span"):
            txt = span.get_text(strip=True)
            if "Rating:" in txt:
                m = re.search(r"([\d.]+)", txt.replace("Rating:", "").strip())
                if m:
                    try:
                        details.rating = float(m.group(1))
                    except ValueError:
                        pass
                break

        # Director
        for div in soup.select("div.genres"):
            b = div.select_one("b")
            if b and "Director" in b.get_text(strip=True):
                p = div.select_one("p")
                if p:
                    name = p.get_text(strip=True)
                    if name:
                        details.directors.append(name)
                break

        # Cast
        for a in soup.select("article a[href*='/actor/']"):
            name = a.get_text(strip=True)
            if name and name not in details.cast:
                details.cast.append(name)

        # Audio / Quality (not always present)
        for span in soup.select("span"):
            txt = span.get_text(strip=True)
            if "Audio:" in txt:
                details.audio = txt.replace("Audio:", "").strip()
            if "Calidad:" in txt:
                details.quality = txt.replace("Calidad:", "").strip()

        # For series: parse episodes
        if is_series:
            season_map = {}
            for article in soup.select("article.item"):
                a = article.select_one("a.itemA")
                if not a:
                    continue
                href = a.get("href", "")
                if not href.startswith("http"):
                    href = self.base_url + href
                # URL pattern: /serie/name/season/X/episode/Y
                m_s = re.search(r"/season/(\d+)", href)
                m_e = re.search(r"/episode/(\d+)", href)
                if not m_s:
                    continue
                s_num = int(m_s.group(1))
                e_num = int(m_e.group(1)) if m_e else 1

                # Episode title from img alt or link text
                img = article.select_one("img")
                ep_title = ""
                if img:
                    ep_title = img.get("alt", "").strip()
                if not ep_title:
                    ep_title = a.get("title", "").strip()
                # Clean "SXXEYY: Title" format
                ep_title = re.sub(r"S\d+E\d+:\s*", "", ep_title).strip()
                if not ep_title:
                    ep_title = f"Episodio {e_num}"

                ep = Episode(
                    id=href,
                    number=e_num,
                    season=s_num,
                    title=ep_title,
                )

                if s_num not in season_map:
                    season_map[s_num] = []
                season_map[s_num].append(ep)

            seasons = []
            for s_num in sorted(season_map.keys()):
                # Sort episodes by number
                eps = sorted(season_map[s_num], key=lambda e: e.number)
                seasons.append(Season(
                    id=f"{item_id}#season{s_num}",
                    number=s_num,
                    title=f"Temporada {s_num}",
                    episodes=eps,
                ))
            details.seasons = seasons

        return details
