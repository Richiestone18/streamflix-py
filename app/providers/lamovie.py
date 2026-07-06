"""
LaMovie provider (Spanish movies/series/anime).
Replaces CineCalidad which moved to lamovie.org.
Uses the site's REST API (wp-api/v1) for listing and player endpoints.
"""
import re
import httpx
from typing import Optional
from ..base import BaseProvider, Movie, TvShow, Category, Server, Episode, Season, MediaDetails


class LaMovieProvider(BaseProvider):
    name = "LaMovie"
    base_url = "https://lamovie.org"
    language = "es"

    API_BASE = "https://lamovie.org/wp-api/v1"
    IMG_BASE = "https://lamovie.org"

    def __init__(self):
        self.http = None  # No cloudscraper needed, uses httpx
        self._client = httpx.AsyncClient(timeout=20.0, headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 8.0.0)",
            "Referer": "https://lamovie.org/",
        })

    async def _get(self, url: str) -> str:
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.text

    async def _get_json(self, url: str) -> dict:
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.json()

    def _build_poster(self, images: dict) -> str:
        if not images:
            return ""
        poster = images.get("poster", "")
        if poster:
            if poster.startswith("/"):
                return self.IMG_BASE + poster
            return poster
        backdrop = images.get("backdrop", "")
        if backdrop:
            if backdrop.startswith("/"):
                return self.IMG_BASE + backdrop
            return backdrop
        return ""

    async def _get_listing(self, content_type: str, page: int = 1) -> list:
        url = f"{self.API_BASE}/listing/{content_type}?page={page}&postsPerPage=24"
        data = await self._get_json(url)
        posts = data.get("data", {}).get("posts", [])
        results = []
        for p in posts:
            poster = self._build_poster(p.get("images", {}))
            title = p.get("title", "Unknown")
            item_id = f"{p.get('type', content_type)}|{p['_id']}"
            if content_type == "movies":
                results.append(Movie(id=item_id, title=title, poster=poster or None))
            else:
                results.append(TvShow(id=item_id, title=title, poster=poster or None))
        return results

    async def get_home(self) -> list[Category]:
        try:
            movies = await self.get_movies()
            tv = await self.get_tv_shows()
            cats = []
            if movies:
                cats.append(Category("Películas", movies))
            if tv:
                cats.append(Category("Series", tv))
            return cats
        except Exception:
            return []

    async def get_movies(self, page: int = 1) -> list[Movie]:
        return await self._get_listing("movies", page)

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        # LaMovie uses "tvshows" for series
        return await self._get_listing("tvshows", page)

    async def search(self, query: str, page: int = 1) -> list:
        if not query:
            # Return categories
            return [
                {"id": "movies", "name": "Películas", "type": "genre"},
                {"id": "tvshows", "name": "Series de TV", "type": "genre"},
                {"id": "novelas", "name": "Novelas", "type": "genre"},
            ]
        url = f"{self.API_BASE}/search?q={query}&page={page}"
        data = await self._get_json(url)
        posts = data.get("data", {}).get("posts", [])
        results = []
        for p in posts:
            poster = self._build_poster(p.get("images", {}))
            title = p.get("title", "Unknown")
            item_type = p.get("type", "movies")
            item_id = f"{item_type}|{p['_id']}"
            if item_type == "movies":
                results.append(Movie(id=item_id, title=title, poster=poster or None))
            else:
                results.append(TvShow(id=item_id, title=title, poster=poster or None))
        return results

    async def get_genre(self, genre_id: str, page: int = 1) -> list:
        # genre_id is the content type (movies, series, anime, novelas)
        return await self._get_listing(genre_id, page)

    async def get_details(self, item_id: str) -> Optional[MediaDetails]:
        # item_id format: "type|numeric_id"
        parts = item_id.split("|")
        if len(parts) < 2:
            return None
        content_type, post_id = parts[0], parts[1]
        url = f"{self.API_BASE}/listing/{content_type}?page=1"
        # Search through pages to find the post
        for pg in range(1, 20):
            data = await self._get_json(f"{self.API_BASE}/listing/{content_type}?page={pg}")
            posts = data.get("data", {}).get("posts", [])
            for p in posts:
                if str(p["_id"]) == str(post_id):
                    poster = self._build_poster(p.get("images", {}))
                    details = MediaDetails(
                        id=item_id,
                        title=p.get("title", ""),
                        type="series" if content_type != "movies" else "movie",
                        poster=poster or None,
                        overview=p.get("overview", ""),
                    )
                    details.rating = float(p.get("rating", 0)) if p.get("rating") else None
                    # Get genres names from tax IDs - skip for now (need separate API call)
                    return details
        return None

    async def get_servers(self, movie_id: str) -> list[Server]:
        # movie_id format: "type|numeric_id"
        parts = movie_id.split("|")
        if len(parts) < 2:
            return []
        post_id = parts[1]
        url = f"{self.API_BASE}/player?postId={post_id}"
        data = await self._get_json(url)
        embeds = data.get("data", {}).get("embeds", [])
        servers = []
        for e in embeds:
            stream_url = e.get("url", "")
            name = e.get("server", "Server")
            lang = e.get("lang", "")
            quality = e.get("quality", "")
            if stream_url and "embed.html" not in stream_url:
                full_name = f"{name} - {lang} {quality}".strip()
                servers.append(Server(id=stream_url, name=full_name))
        return servers
