"""
IPTV provider using iptv-org public M3U playlists.
Loads live TV channels, movies, and series from iptv-org GitHub.
Streams are direct .m3u8 URLs playable in HTML5 video or HLS.js.
"""
import httpx
import re
from typing import Optional
from ..base import BaseProvider, Movie, TvShow, Category, Server, Episode, Season, MediaDetails


class IPTVProvider(BaseProvider):
    name = "IPTV"
    base_url = "https://iptv-org.github.io"
    language = "es"

    # M3U playlist sources
    PLAYLISTS = {
        "spa": "https://iptv-org.github.io/iptv/languages/spa.m3u",  # Spanish (2240+ channels)
        "movies": "https://iptv-org.github.io/iptv/categories/movies.m3u",
        "series": "https://iptv-org.github.io/iptv/categories/series.m3u",
    }

    def __init__(self):
        # Skip BaseProvider.__init__ (no cloudscraper needed, we use httpx directly)
        self.http = None  # No HttpClient needed
        self._cache = {}  # Cache parsed playlists

    async def _get(self, url: str) -> str:
        """Fetch URL with httpx directly."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text

    def _parse_m3u(self, m3u_text: str) -> list:
        """Parse M3U playlist into channel list."""
        channels = []
        lines = m3u_text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('#EXTINF'):
                # Parse metadata
                m_name = re.search(r',(.+)$', line)
                m_logo = re.search(r'tvg-logo="([^"]+)"', line)
                m_group = re.search(r'group-title="([^"]+)"', line)
                m_id = re.search(r'tvg-id="([^"]+)"', line)

                name = m_name.group(1).strip() if m_name else "Unknown"
                logo = m_logo.group(1) if m_logo else None
                group = m_group.group(1) if m_group else "General"
                tvg_id = m_id.group(1) if m_id else ""

                # Next line should be the URL
                i += 1
                while i < len(lines) and not lines[i].strip():
                    i += 1
                if i < len(lines):
                    url = lines[i].strip()
                    if url and not url.startswith('#'):
                        channels.append({
                            "name": name,
                            "logo": logo,
                            "group": group,
                            "url": url,
                            "tvg_id": tvg_id,
                        })
            i += 1
        return channels

    async def _get_playlist(self, key: str) -> list:
        """Get and cache a playlist by key."""
        if key in self._cache:
            return self._cache[key]
        url = self.PLAYLISTS.get(key)
        if not url:
            return []
        try:
            m3u_text = await self._get(url)
            channels = self._parse_m3u(m3u_text)
            self._cache[key] = channels
            return channels
        except Exception:
            return []

    async def _get_all_channels(self) -> list:
        """Get all channels from all playlists."""
        all_channels = []
        seen = set()
        for key in self.PLAYLISTS:
            channels = await self._get_playlist(key)
            for ch in channels:
                # Deduplicate by URL
                if ch["url"] not in seen:
                    seen.add(ch["url"])
                    all_channels.append(ch)
        return all_channels

    async def get_home(self) -> list[Category]:
        try:
            movies = await self.get_movies()
            tv = await self.get_tv_shows()
            cats = []
            if movies:
                cats.append(Category("Canales de Películas", movies))
            if tv:
                cats.append(Category("Canales de TV", tv))
            return cats
        except Exception:
            return []

    async def get_movies(self, page: int = 1) -> list[Movie]:
        """Movies from IPTV (movie channels)."""
        channels = await self._get_playlist("movies")
        # Paginate: 24 per page
        start = (page - 1) * 24
        end = start + 24
        page_channels = channels[start:end]
        return [
            Movie(
                id=ch["url"],
                title=ch["name"],
                poster=ch["logo"],
            )
            for ch in page_channels
        ]

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        """Series/live TV from IPTV (Spanish channels + series)."""
        series = await self._get_playlist("series")
        spa = await self._get_playlist("spa")

        # Combine and deduplicate
        seen = set()
        all_tv = []
        for ch in spa + series:
            if ch["url"] not in seen:
                seen.add(ch["url"])
                all_tv.append(ch)

        start = (page - 1) * 24
        end = start + 24
        page_channels = all_tv[start:end]
        return [
            TvShow(
                id=ch["url"],
                title=ch["name"],
                poster=ch["logo"],
            )
            for ch in page_channels
        ]

    async def search(self, query: str, page: int = 1) -> list:
        """Search channels or return categories."""
        if not query:
            # Return categories (groups)
            all_channels = await self._get_all_channels()
            groups = set()
            for ch in all_channels:
                for g in ch["group"].split(';'):
                    g = g.strip()
                    if g:
                        groups.add(g)
            return [
                {"id": f"group={g}", "name": g, "type": "genre"}
                for g in sorted(groups)
            ]

        # Search by name
        all_channels = await self._get_all_channels()
        query_lower = query.lower()
        results = [
            ch for ch in all_channels
            if query_lower in ch["name"].lower()
        ]
        start = (page - 1) * 24
        end = start + 24
        page_results = results[start:end]
        return [
            Movie(id=ch["url"], title=ch["name"], poster=ch["logo"])
            for ch in page_results
        ]

    async def get_genre(self, genre_id: str, page: int = 1) -> list:
        """Filter by group."""
        genre_id = genre_id.replace("group=", "")
        all_channels = await self._get_all_channels()
        filtered = [
            ch for ch in all_channels
            if genre_id in ch["group"].split(';')
        ]
        start = (page - 1) * 24
        end = start + 24
        page_channels = filtered[start:end]
        return [
            Movie(id=ch["url"], title=ch["name"], poster=ch["logo"])
            for ch in page_channels
        ]

    async def get_servers(self, movie_id: str) -> list[Server]:
        """For IPTV, the movie_id IS the stream URL. Return it directly."""
        return [Server(id=movie_id, name="IPTV Stream")]

    async def get_details(self, item_id: str) -> Optional[MediaDetails]:
        """For IPTV, create a simple detail from the stream URL."""
        # Find the channel in all playlists
        all_channels = await self._get_all_channels()
        for ch in all_channels:
            if ch["url"] == item_id:
                details = MediaDetails(
                    id=item_id,
                    title=ch["name"],
                    type="movie",  # IPTV streams are treated as movies
                    poster=ch["logo"],
                    overview=f"Canal: {ch['name']}\nGrupo: {ch['group']}",
                )
                details.genres = [g.strip() for g in ch["group"].split(";") if g.strip()]
                return details
        # Fallback: create basic details
        return MediaDetails(
            id=item_id,
            title="IPTV Stream",
            type="movie",
            poster=None,
            overview="Live IPTV stream",
        )
