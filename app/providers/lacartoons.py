"""
LaCartoons provider (Spanish classic cartoons).
Only TV shows/series, no movies.
Categories are by animation company (Nickelodeon, Cartoon Network, etc.).
Single server (ok.ru) per episode.
"""
import re
from bs4 import BeautifulSoup
from ..base import BaseProvider, Movie, TvShow, Category, Server, Episode, Season, MediaDetails
from typing import Optional


class LaCartoonsProvider(BaseProvider):
    name = "LaCartoons"
    base_url = "https://www.lacartoons.com"
    language = "es"

    # Category mapping: company -> Categoria_id
    CATEGORIES = {
        "Nickelodeon": 1,
        "Cartoon Network": 2,
        "Fox Kids": 3,
        "Hanna Barbera": 4,
        "Disney": 5,
        "Warner Channel": 6,
        "Marvel": 7,
        "Otros": 8,
    }

    def _extract_title(self, text: str) -> str:
        """Extract series title from card text like '2 Perros TontosCartoon Network19937'"""
        # Remove year at end (4 digits)
        text = re.sub(r'\d{4}$', '', text).strip()
        # Remove known network names
        for network in sorted(self.CATEGORIES.keys(), key=len, reverse=True):
            if text.endswith(network):
                text = text[:-len(network)].strip()
                break
        # Remove trailing rating number
        text = re.sub(r'\d+$', '', text).strip()
        return text

    def _parse_series_cards(self, soup: BeautifulSoup) -> list:
        """Parse series cards from a listing page."""
        results = []
        seen = set()
        for a in soup.select('a[href*="/serie/"]'):
            href = a.get("href", "")
            # Skip episode links
            if "/capitulo/" in href:
                continue
            if href in seen:
                continue
            seen.add(href)

            if not href.startswith("http"):
                href = self.base_url + href

            img = a.select_one("img")
            poster = img.get("src", "") if img else ""
            if poster and not poster.startswith("http"):
                poster = self.base_url + poster

            # Text parts: title, network, year, rating
            text_parts = [t.strip() for t in a.get_text("|", strip=True).split("|") if t.strip()]
            if not text_parts:
                continue

            title = text_parts[0]
            year = None
            for part in text_parts:
                if re.match(r'^\d{4}$', part):
                    year = part
                    break

            # Clean title
            title = self._extract_title(title)
            if not title:
                continue

            results.append(TvShow(id=href, title=title, poster=poster, year=year))
        return results

    async def get_home(self) -> list[Category]:
        try:
            tv = await self.get_tv_shows()
            if tv:
                return [Category("Series Animadas", tv)]
            return []
        except Exception:
            return []

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        url = f"{self.base_url}/?page={page}" if page > 1 else self.base_url
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        return self._parse_series_cards(soup)

    async def get_movies(self, page: int = 1) -> list[Movie]:
        return []

    async def search(self, query: str, page: int = 1) -> list:
        if not query:
            # Return categories as genres
            return [
                {"id": f"cat={cat_id}", "name": name, "type": "genre"}
                for name, cat_id in self.CATEGORIES.items()
            ]
        # Search by title
        url = f"{self.base_url}/?Titulo={query}&page={page}"
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        return self._parse_series_cards(soup)

    async def get_genre(self, genre_id: str, page: int = 1) -> list:
        """Genre = company category. genre_id format: 'cat=1' or just '1'."""
        # Extract category ID
        cat_id = genre_id.replace("cat=", "")
        url = f"{self.base_url}/?Categoria_id={cat_id}&page={page}"
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        return self._parse_series_cards(soup)

    async def get_servers(self, item_id: str) -> list[Server]:
        """For LaCartoons, the item_id is an episode URL.
        Get the page and extract the ok.ru iframe."""
        html = await self._get(item_id)
        soup = BeautifulSoup(html, "lxml")
        servers = []

        # The episode page has an iframe (ok.ru)
        for iframe in soup.select("iframe[src]"):
            src = iframe.get("src", "")
            if src.startswith("http"):
                servers.append(Server(id=src, name="ok.ru"))

        # Fallback: try video tags
        if not servers:
            for video in soup.select("video source[src], video[src]"):
                src = video.get("src", "")
                if src:
                    servers.append(Server(id=src, name="Video"))

        return servers

    async def get_details(self, item_id: str) -> Optional[MediaDetails]:
        """Get series details: title, poster, network, year, seasons with episodes."""
        html = await self._get(item_id)
        soup = BeautifulSoup(html, "lxml")

        details = MediaDetails(
            id=item_id,
            title="",
            type="series",
        )

        # Title from h2
        h2 = soup.select_one("h2")
        if h2:
            full_text = h2.get_text(strip=True)
            # h2 text is like "2 Perros Tontos Cartoon Network"
            # Extract title and network
            for network in sorted(self.CATEGORIES.keys(), key=len, reverse=True):
                if network in full_text:
                    details.title = full_text.replace(network, "").strip()
                    details.genres = [network]
                    break
            if not details.title:
                details.title = full_text

        # Poster: first meaningful image on the page
        for img in soup.select("img"):
            src = img.get("src", "")
            if src and ("lacartoons" in src or "active_storage" in src):
                full_src = src if src.startswith("http") else self.base_url + src
                details.poster = full_src
                details.banner = full_src
                break

        # Overview: not available on series page, but try
        for p in soup.select("p"):
            txt = p.get_text(strip=True)
            if len(txt) > 50 and "cartoon" not in txt.lower()[:20]:
                details.overview = txt
                break

        # Parse seasons and episodes
        # Structure: h4.accordion (season header) -> sibling div (panel with episode links)
        seasons = []
        for h4 in soup.select("h4"):
            season_text = h4.get_text(strip=True)
            # "Temporada 1"
            m = re.search(r"Temporada\s+(\d+)", season_text)
            if not m:
                continue
            season_num = int(m.group(1))

            # Find the episode panel (next sibling div)
            panel = h4.find_next_sibling("div") or h4.find_next("div")
            if not panel:
                continue

            episodes = []
            for a in panel.select('a[href*="/serie/capitulo/"]'):
                href = a.get("href", "")
                text = a.get_text(strip=True)
                if not href:
                    continue
                if not href.startswith("http"):
                    href = self.base_url + href

                # Parse episode number from text "Capitulo 1- Title"
                m_ep = re.search(r"Capitulo\s+(\d+)", text)
                ep_num = int(m_ep.group(1)) if m_ep else len(episodes) + 1

                # Extract episode title (after "Capitulo N-")
                ep_title = re.sub(r"Capitulo\s*\d+\s*-?\s*", "", text).strip()
                if not ep_title:
                    ep_title = f"Capítulo {ep_num}"

                episodes.append(Episode(
                    id=href,
                    number=ep_num,
                    season=season_num,
                    title=ep_title,
                ))

            if episodes:
                seasons.append(Season(
                    id=f"{item_id}#season{season_num}",
                    number=season_num,
                    title=f"Temporada {season_num}",
                    episodes=episodes,
                ))

        details.seasons = seasons

        # Year: try to extract from the series info area
        for span in soup.select("span, div, p"):
            txt = span.get_text(strip=True)
            m = re.search(r"(\d{4})", txt)
            if m and 1940 <= int(m.group(1)) <= 2026:
                details.year = m.group(1)
                break

        # Rating
        for span in soup.select("span, div"):
            txt = span.get_text(strip=True)
            if re.match(r"^\d+(\.\d+)?$", txt):
                try:
                    r = float(txt)
                    if 0 <= r <= 10:
                        details.rating = r
                        break
                except ValueError:
                    pass

        return details
