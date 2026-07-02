"""
FlixLatam provider (Spanish movies/series/animes).
Site: https://flixlatam.com
Uses static HTML with iframe-based players.
"""
import re
from bs4 import BeautifulSoup
from ..base import BaseProvider, Movie, TvShow, Category, Server, Episode, Season, MediaDetails
from typing import Optional


class FlixLatamProvider(BaseProvider):
    name = "FlixLatam"
    base_url = "https://flixlatam.com"

    def _parse_movies(self, soup: BeautifulSoup) -> list:
        results = []
        seen = set()
        for a in soup.select('a[href*="/pelicula/"]'):
            href = a.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            if not href.startswith("http"):
                href = self.base_url + href
            img = a.select_one("img")
            title = img.get("alt", "") if img else ""
            if not title:
                title = a.get_text(strip=True)
            title = re.sub(r'^Ver\s+', '', title)
            title = re.sub(r'\s+online$', '', title, flags=re.I)
            title = title.strip()
            poster = img.get("src") if img else None
            if poster and not poster.startswith("http"):
                poster = self.base_url + poster
            if title and len(title) > 2:
                results.append(Movie(id=href, title=title, poster=poster))
        return results

    def _parse_series(self, soup: BeautifulSoup) -> list:
        results = []
        seen = set()
        for a in soup.select('a[href*="/serie/"]'):
            href = a.get("href", "")
            # Skip episode links
            if "/temporada/" in href:
                continue
            if not href or href in seen:
                continue
            seen.add(href)
            if not href.startswith("http"):
                href = self.base_url + href
            img = a.select_one("img")
            title = img.get("alt", "") if img else ""
            if not title:
                title = a.get_text(strip=True)
            title = re.sub(r'^Ver\s+', '', title)
            title = re.sub(r'\s+online$', '', title, flags=re.I)
            title = title.strip()
            poster = img.get("src") if img else None
            if poster and not poster.startswith("http"):
                poster = self.base_url + poster
            if title and len(title) > 2:
                results.append(TvShow(id=href, title=title, poster=poster))
        return results

    def _parse_animes(self, soup: BeautifulSoup) -> list:
        results = []
        seen = set()
        for a in soup.select('a[href*="/anime/"]'):
            href = a.get("href", "")
            if "/temporada/" in href:
                continue
            if not href or href in seen:
                continue
            seen.add(href)
            if not href.startswith("http"):
                href = self.base_url + href
            img = a.select_one("img")
            title = img.get("alt", "") if img else ""
            if not title:
                title = a.get_text(strip=True)
            title = re.sub(r'^Ver\s+', '', title)
            title = re.sub(r'\s+online$', '', title, flags=re.I)
            title = title.strip()
            poster = img.get("src") if img else None
            if poster and not poster.startswith("http"):
                poster = self.base_url + poster
            if title and len(title) > 2:
                results.append(TvShow(id=href, title=title, poster=poster))
        return results

    async def get_movies(self, page: int = 1) -> list[Movie]:
        url = f"{self.base_url}/peliculas?page={page}"
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        return self._parse_movies(soup)

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        url = f"{self.base_url}/series?page={page}"
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        return self._parse_series(soup)

    async def search(self, query: str, page: int = 1) -> list:
        if not query:
            return [
                {"id": "peliculas", "name": "Películas", "type": "genre"},
                {"id": "series", "name": "Series", "type": "genre"},
                {"id": "animes", "name": "Animes", "type": "genre"},
            ]
        url = f"{self.base_url}/peliculas?page={page}"
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        return self._parse_movies(soup)

    async def get_genre(self, genre_id: str, page: int = 1) -> list:
        url = f"{self.base_url}/{genre_id}?page={page}"
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        if genre_id == "peliculas":
            return self._parse_movies(soup)
        elif genre_id == "series":
            return self._parse_series(soup)
        elif genre_id == "animes":
            return self._parse_animes(soup)
        return self._parse_movies(soup)

    async def get_servers(self, movie_id: str) -> list[Server]:
        html = await self._get(movie_id)
        soup = BeautifulSoup(html, "lxml")
        servers = []

        # Look for iframe with /vidurl/ path (movie)
        for iframe in soup.select("iframe[src]"):
            src = iframe.get("src", "")
            if not src:
                continue
            if not src.startswith("http"):
                src = self.base_url + src
            servers.append(Server(id=src, name="FlixLatam Player"))

        # If this is a series episode page, also check episode links
        if not servers:
            episodes = soup.select('a[href*="/temporada/"]')
            for ep in episodes[:1]:  # Just first episode
                ep_url = ep.get("href", "")
                if not ep_url.startswith("http"):
                    ep_url = self.base_url + ep_url
                ep_html = await self._get(ep_url)
                ep_soup = BeautifulSoup(ep_html, "lxml")
                for iframe in ep_soup.select("iframe[src]"):
                    src = iframe.get("src", "")
                    if not src.startswith("http"):
                        src = self.base_url + src
                    servers.append(Server(id=src, name=ep.get_text(strip=True)[:30] or "Episodio 1"))

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

        # Title from h1 first (og:title has "Ver X Online - FLIXLATAM" prefix)
        h1 = soup.select_one("h1, h2, .title")
        if h1:
            details.title = h1.get_text(strip=True)
        if not details.title:
            og_title = soup.select_one('meta[property="og:title"]')
            if og_title:
                details.title = og_title.get("content", "").strip()
        # Clean "Ver X Online" prefix
        details.title = re.sub(r'^Ver\s+', '', details.title)
        details.title = re.sub(r'\s+Online\s*-\s*FLIXLATAM$', '', details.title, flags=re.I)
        details.title = details.title.strip()

        # Overview from meta description
        og_desc = soup.select_one('meta[name="description"], meta[property="og:description"]')
        if og_desc:
            details.overview = og_desc.get("content", "").strip()

        # Poster from og:image
        og_img = soup.select_one('meta[property="og:image"]')
        if og_img:
            details.poster = og_img.get("content", "").strip()

        # Epoch_btn_year from URL or page text
        m = re.search(r"\((\d{4})\)", details.title)
        if m:
            details.year = m.group(1)

        # For series: parse seasons and episodes
        if is_series:
            # Group episodes by season number
            season_map = {}
            for a in soup.select('a[href*="/temporada/"]'):
                href = a.get("href", "")
                text = a.get_text(strip=True)
                if not href or not text:
                    continue
                if not href.startswith("http"):
                    href = self.base_url + href

                # Extract season and episode from URL: /temporada/X/capitulo/Y
                m_s = re.search(r"temporada/(\d+)", href)
                m_e = re.search(r"capitulo/(\d+)", href)
                s_num = int(m_s.group(1)) if m_s else 1
                e_num = int(m_e.group(1)) if m_e else len(season_map.get(s_num, [])) + 1

                ep = Episode(
                    id=href,
                    number=e_num,
                    season=s_num,
                    title=text,
                )

                if s_num not in season_map:
                    season_map[s_num] = []
                season_map[s_num].append(ep)

            seasons = []
            for s_num in sorted(season_map.keys()):
                seasons.append(Season(
                    id=f"{item_id}#season{s_num}",
                    number=s_num,
                    title=f"Temporada {s_num}",
                    episodes=season_map[s_num],
                ))
            details.seasons = seasons

        return details
