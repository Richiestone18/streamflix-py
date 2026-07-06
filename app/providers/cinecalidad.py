"""
CineCalidad provider (Spanish movies/series).
"""
import re
from bs4 import BeautifulSoup
from ..base import BaseProvider, Movie, TvShow, Category, Server, Episode, Season, MediaDetails
from typing import Optional


class CineCalidadProvider(BaseProvider):
    name = "CineCalidad"
    base_url = "https://www.cinecalidad.ec"

    async def _get(self, url: str) -> str:
        """Override to send password cookie for site protection."""
        import httpx
        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"},
            cookies={"password": "cc"},
            follow_redirects=True,
            timeout=30.0,
        ) as c:
            resp = await c.get(url)
            resp.raise_for_status()
            return resp.text

    def _parse_shows(self, elements: list) -> list:
        results = []
        for article in elements:
            a = article.select_one("a")
            if not a:
                continue
            href = a.get("href", "")
            img = article.select_one("div.poster img")
            if not img:
                continue
            title = img.get("alt", "")
            poster = img.get("data-src") or img.get("src", "")
            # Fix double slash in TMDB URLs
            if poster and "image.tmdb.org" in poster:
                poster = poster.replace("//", "/", 1).replace("https:/", "https://", 1)
                # Remove leftover double slash after w342/
                poster = poster.replace("w342//", "w342/")
            # Skip empty TMDB posters (no path after w342/)
            if poster and poster.rstrip("/").endswith("w342"):
                poster = ""

            if "/ver-pelicula/" in href:
                results.append(Movie(id=href, title=title, poster=poster))
            elif "/ver-serie/" in href:
                results.append(TvShow(id=href, title=title, poster=poster))
        return results

    async def get_home(self) -> list[Category]:
        html = await self._get(self.base_url)
        soup = BeautifulSoup(html, "lxml")
        cats = []

        featured = []
        for li in soup.select("aside#dtw_content_featured-3 li"):
            a = li.select_one("a")
            if not a:
                continue
            href = a.get("href", "")
            title = a.get("title", "")
            img = a.select_one("img")
            poster = (img.get("data-src") or img.get("src", "")) if img else None
            if poster and isinstance(poster, str):
                if "image.tmdb.org" in poster:
                    poster = poster.replace("w342//", "w342/")
                if poster.rstrip("/").endswith("w342"):
                    poster = ""
            else:
                poster = str(poster) if poster else None
            if "/ver-pelicula/" in href:
                featured.append(Movie(id=href, title=title, banner=poster))
            elif "/ver-serie/" in href:
                featured.append(TvShow(id=href, title=title, banner=poster))
        if featured:
            cats.append(Category("Destacados", featured))

        latest = self._parse_shows(soup.select("article.item[id^=post-]"))
        if latest:
            cats.append(Category("Últimos Estrenos", latest))
        return cats

    async def search(self, query: str, page: int = 1) -> list:
        if not query:
            return [
                {"id": "genero-de-la-pelicula/accion", "name": "Acción", "type": "genre"},
                {"id": "genero-de-la-pelicula/animacion", "name": "Animación", "type": "genre"},
                {"id": "genero-de-la-pelicula/anime", "name": "Anime", "type": "genre"},
                {"id": "genero-de-la-pelicula/aventura", "name": "Aventura", "type": "genre"},
                {"id": "genero-de-la-pelicula/belica", "name": "Bélico", "type": "genre"},
                {"id": "genero-de-la-pelicula/ciencia-ficcion", "name": "Ciencia ficción", "type": "genre"},
                {"id": "genero-de-la-pelicula/crimen", "name": "Crimen", "type": "genre"},
                {"id": "genero-de-la-pelicula/comedia", "name": "Comedia", "type": "genre"},
                {"id": "genero-de-la-pelicula/documental", "name": "Documental", "type": "genre"},
                {"id": "genero-de-la-pelicula/drama", "name": "Drama", "type": "genre"},
                {"id": "genero-de-la-pelicula/familia", "name": "Familiar", "type": "genre"},
                {"id": "genero-de-la-pelicula/fantasia", "name": "Fantasía", "type": "genre"},
                {"id": "genero-de-la-pelicula/historia", "name": "Historia", "type": "genre"},
                {"id": "genero-de-la-pelicula/musica", "name": "Música", "type": "genre"},
                {"id": "genero-de-la-pelicula/misterio", "name": "Misterio", "type": "genre"},
                {"id": "genero-de-la-pelicula/terror", "name": "Terror", "type": "genre"},
                {"id": "genero-de-la-pelicula/suspense", "name": "Suspenso", "type": "genre"},
                {"id": "genero-de-la-pelicula/romance", "name": "Romance", "type": "genre"},
                {"id": "genero-de-la-pelicula/peliculas-de-dc-comics-online-cinecalidad", "name": "DC Comics", "type": "genre"},
                {"id": "genero-de-la-pelicula/universo-marvel", "name": "Marvel", "type": "genre"},
            ]
        html = await self._get(f"{self.base_url}/page/{page}?s={query}")
        soup = BeautifulSoup(html, "lxml")
        return self._parse_shows(soup.select("article.item[id^=post-]"))

    async def get_movies(self, page: int = 1) -> list[Movie]:
        html = await self._get(f"{self.base_url}/page/{page}")
        soup = BeautifulSoup(html, "lxml")
        return [m for m in self._parse_shows(soup.select("article.item[id^=post-]"))
                if isinstance(m, Movie)]

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        html = await self._get(f"{self.base_url}/ver-serie/page/{page}")
        soup = BeautifulSoup(html, "lxml")
        return [s for s in self._parse_shows(soup.select("article.item[id^=post-]"))
                if isinstance(s, TvShow)]

    # Domains known to block iframe embedding (403/X-Frame-Options)
    _BLOCKED_DOMAINS = {"vimeos.net", "goodstream.one", "hlswish.com"}

    def _domain_name(self, url: str) -> str:
        try:
            from urllib.parse import urlparse
            host = urlparse(url).hostname or ""
            return host.replace("www.", "")
        except Exception:
            return ""

    async def get_servers(self, movie_id: str) -> list[Server]:
        url = movie_id
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        raw_servers = []

        # Try #playeroptionsul li[data-option]
        for li in soup.select("#playeroptionsul li[data-option]"):
            classes = li.get("class") or []
            if "dooplay_player_option_trailer" in classes:
                continue
            if "trailer" in li.get_text(strip=True).lower():
                continue
            raw_url = li.get("data-option", "")
            name = li.get_text(strip=True) or "Server"
            if raw_url:
                raw_servers.append((raw_url, name))

        if not raw_servers:
            import base64
            for li in soup.select("ul.optnslst li[data-src]"):
                data_src = li.get("data-src", "")
                try:
                    decoded = base64.b64decode(data_src).decode()
                except Exception:
                    continue
                if decoded:
                    raw_servers.append((decoded, li.get_text(strip=True) or "Server"))

        # Split into working and blocked
        working = []
        blocked = []
        for srv_url, srv_name in raw_servers:
            domain = self._domain_name(srv_url)
            if domain in self._BLOCKED_DOMAINS:
                blocked.append(Server(id=srv_url, name=f"⚠️ {srv_name}"))
            else:
                working.append(Server(id=srv_url, name=srv_name))
        return working + blocked

    async def get_genre(self, genre_id: str, page: int = 1) -> list:
        url = f"{self.base_url}/{genre_id}/page/{page}"
        html = await self._get(url)
        soup = BeautifulSoup(html, "lxml")
        return self._parse_shows(soup.select("article.item[id^=post-]"))

    async def get_details(self, item_id: str) -> Optional[MediaDetails]:
        html = await self._get(item_id)
        soup = BeautifulSoup(html, "lxml")

        is_series = "/ver-serie/" in item_id
        details = MediaDetails(
            id=item_id,
            title="",
            type="series" if is_series else "movie",
        )

        # Title
        h1 = soup.select_one("#single h1, .dtsingle h1")
        if h1:
            details.title = h1.get_text(strip=True)

        # Poster
        img = soup.select_one("#single img[data-src], .dtsingle img[data-src]")
        if img:
            poster = img.get("data-src") or img.get("src", "")
            if poster and isinstance(poster, str) and "image.tmdb.org" in poster:
                poster = poster.replace("w342//", "w342/")
            details.poster = poster

        # Overview (first <p> in the info column)
        for p in soup.select("#single p, .dtsingle p"):
            txt = p.get_text(strip=True)
            if txt and len(txt) > 20 and "Títulos:" not in txt:
                details.overview = txt
                break

        # Rating
        rating_el = soup.select_one("#single b, .dtsingle b")
        if rating_el:
            try:
                details.rating = float(rating_el.get_text(strip=True))
            except ValueError:
                pass

        # Genres - only from the single content area
        genres = []
        for a in soup.select('#single a[href*="genero-de-la-pelicula/"], .dtsingle a[href*="genero-de-la-pelicula/"]'):
            g = a.get_text(strip=True)
            if g:
                genres.append(g)
        details.genres = genres

        # Year
        for span in soup.select("#single span, .dtsingle span"):
            txt = span.get_text(strip=True)
            if "Fecha:" in txt:
                m = re.search(r"(\d{4})", txt)
                if m:
                    details.year = m.group(1)
                break

        # Audio
        for span in soup.select("#single span, .dtsingle span"):
            txt = span.get_text(strip=True)
            if "Audio:" in txt:
                details.audio = txt.replace("Audio:", "").strip()
                break

        # Quality
        for span in soup.select("#single span, .dtsingle span"):
            txt = span.get_text(strip=True)
            if "Calidad:" in txt:
                details.quality = txt.replace("Calidad:", "").strip()
                break

        # Cast
        for a in soup.select('#single a[href*="reparto-de-"], .dtsingle a[href*="reparto-de-"]'):
            name = a.get_text(strip=True)
            if name:
                details.cast.append(name)

        # Directors
        for a in soup.select('#single a[href*="director-de-"], .dtsingle a[href*="director-de-"]'):
            name = a.get_text(strip=True)
            if name:
                details.directors.append(name)

        # Seasons and episodes (series only)
        if is_series:
            seasons = []
            for ul in soup.select("#single ul.episodios, .dtsingle ul.episodios, ul.episodios"):
                episodes = []
                season_num = 1
                for li in ul.select("li"):
                    li_text = li.get_text(strip=True)
                    a = li.select_one("a[href]")
                    if not a:
                        continue
                    href = a.get("href", "")
                    ep_title = a.get_text(strip=True)

                    # Parse "S1-E2" from li text
                    m_e = re.search(r"S(\d+)\s*-?\s*E(\d+)", li_text)
                    m_h = re.search(r"temporada/(\d+)", href)
                    m_h2 = re.search(r"-(\d+)x(\d+)", href)
                    if m_e:
                        s_num = int(m_e.group(1))
                        e_num = int(m_e.group(2))
                    elif m_h:
                        s_num = int(m_h.group(1))
                        e_num_match = re.search(r"capitulo/(\d+)", href)
                        e_num = int(e_num_match.group(1)) if e_num_match else len(episodes) + 1
                    elif m_h2:
                        s_num = int(m_h2.group(1))
                        e_num = int(m_h2.group(2))
                    else:
                        continue

                    season_num = s_num
                    episodes.append(Episode(
                        id=href,
                        number=e_num,
                        season=s_num,
                        title=ep_title or f"Episodio {e_num}",
                    ))

                if episodes:
                    # Check if season already exists
                    found = False
                    for s in seasons:
                        if s.number == season_num:
                            s.episodes.extend(episodes)
                            found = True
                            break
                    if not found:
                        seasons.append(Season(
                            id=f"{item_id}#season{season_num}",
                            number=season_num,
                            title=f"Temporada {season_num}",
                            episodes=episodes,
                        ))

            details.seasons = seasons

        return details