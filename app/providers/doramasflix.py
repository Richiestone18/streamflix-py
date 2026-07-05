"""
Doramasflix provider (Spanish doramas/movies).
Ported from streamflix-reborn/streamflix Kotlin project.
URL: https://doramasflix.in
Uses GraphQL API at sv1.fluxcedene.net
"""
import httpx
import json
from typing import Optional
from ..base import BaseProvider, Movie, TvShow, Category, Server, Episode, Season, MediaDetails


class DoramasflixProvider(BaseProvider):
    name = "Doramasflix"
    base_url = "https://doramasflix.in"
    language = "es"
    _api_url = "https://sv1.fluxcedene.net/api/"
    _access_platform = "RxARncfg1S_MdpSrCvreoLu_SikCGMzE1NzQzODc3NjE2MQ=="

    _LANG_MAP = {
        "36": "[ENG]", "37": "[CAST]", "38": "[LAT]", "192": "[SUB]",
        "1327": "[POR]", "13109": "[COR]", "13110": "[JAP]", "13111": "[MAN]",
        "13112": "[TAI]", "13113": "[FIL]", "13114": "[IND]", "343422": "[VIET]",
    }

    def __init__(self):
        self.http = None  # Use httpx directly
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _get(self, url: str) -> str:
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.text

    async def _gql(self, operation: str, variables: dict, query: str) -> dict:
        """Execute GraphQL query."""
        payload = {
            "operationName": operation,
            "variables": variables,
            "query": query,
        }
        headers = {
            "accept": "application/json, text/plain, */*",
            "platform": "doramasflix",
            "authorization": "***",
            "x-access-jwt-token": "",
            "x-access-platform": self._access_platform,
            "Content-Type": "application/json",
        }
        resp = await self._client.post(f"{self._api_url}gql", json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def _poster_url(self, path: str) -> str:
        if path and path.startswith("http"):
            return path
        return f"https://image.tmdb.org/t/p/w500{path}" if path else ""

    async def get_movies(self, page: int = 1) -> list[Movie]:
        query = """query listMovies($page: Int, $perPage: Int, $sort: SortFindManyMovieInput, $filter: FilterFindManyMovieInput) {
  paginationMovie(page: $page, perPage: $perPage, sort: $sort, filter: $filter) {
    items { _id name name_es slug poster_path poster __typename }
  }
}"""
        try:
            data = await self._gql("listMovies",
                {"perPage": 20, "sort": "POPULARITY_DESC", "filter": {}, "page": page}, query)
            items = data.get("data", {}).get("paginationMovie", {}).get("items", [])
            return [
                Movie(
                    id=f"peliculas-online/{it['slug']}",
                    title=f"{it['name']} ({it.get('name_es', '')})".strip(),
                    poster=self._poster_url(it.get("poster_path") or it.get("poster", "")),
                )
                for it in items
            ]
        except Exception:
            return []

    async def get_tv_shows(self, page: int = 1) -> list[TvShow]:
        query = """query listDoramas($page: Int, $perPage: Int, $sort: SortFindManyDoramaInput, $filter: FilterFindManyDoramaInput) {
  paginationDorama(page: $page, perPage: $perPage, sort: $sort, filter: $filter) {
    items { _id name name_es slug poster_path poster __typename }
  }
}"""
        try:
            data = await self._gql("listDoramas",
                {"page": page, "sort": "POPULARITY_DESC", "perPage": 20, "filter": {"isTVShow": False}}, query)
            items = data.get("data", {}).get("paginationDorama", {}).get("items", [])
            return [
                TvShow(
                    id=f"doramas-online/{it['slug']}",
                    title=f"{it['name']} ({it.get('name_es', '')})".strip(),
                    poster=self._poster_url(it.get("poster_path") or it.get("poster", "")),
                )
                for it in items
            ]
        except Exception:
            return []

    async def search(self, query: str, page: int = 1) -> list:
        if not query:
            return [
                {"id": "doramas", "name": "Doramas", "type": "genre"},
                {"id": "peliculas", "name": "Películas", "type": "genre"},
                {"id": "variedades", "name": "Variedades", "type": "genre"},
            ]
        gql_query = """query searchAll($input: String!) {
  searchDorama(input: $input, limit: 32) { _id slug name name_es poster_path poster __typename }
  searchMovie(input: $input, limit: 32) { _id name name_es slug poster_path poster __typename }
}"""
        try:
            data = await self._gql("searchAll", {"input": query}, gql_query)
            results = []
            for show in data.get("data", {}).get("searchDorama", []):
                results.append(TvShow(
                    id=f"doramas-online/{show['slug']}",
                    title=f"{show['name']} ({show.get('name_es', '')})".strip(),
                    poster=self._poster_url(show.get("poster_path") or show.get("poster", "")),
                ))
            for show in data.get("data", {}).get("searchMovie", []):
                results.append(Movie(
                    id=f"peliculas-online/{show['slug']}",
                    title=f"{show['name']} ({show.get('name_es', '')})".strip(),
                    poster=self._poster_url(show.get("poster_path") or show.get("poster", "")),
                ))
            return results
        except Exception:
            return []

    async def get_genre(self, genre_id: str, page: int = 1) -> list:
        if genre_id == "peliculas":
            return await self.get_movies(page)
        elif genre_id == "variedades":
            query = """query listDoramas($page: Int, $perPage: Int, $sort: SortFindManyDoramaInput, $filter: FilterFindManyDoramaInput) {
  paginationDorama(page: $page, perPage: $perPage, sort: $sort, filter: $filter) {
    items { _id name name_es slug poster_path poster __typename }
  }
}"""
            try:
                data = await self._gql("listDoramas",
                    {"page": page, "sort": "CREATEDAT_DESC", "perPage": 32, "filter": {"isTVShow": True}}, query)
                items = data.get("data", {}).get("paginationDorama", {}).get("items", [])
                return [
                    TvShow(
                        id=it["slug"],
                        title=f"{it['name']} ({it.get('name_es', '')})".strip(),
                        poster=self._poster_url(it.get("poster_path") or it.get("poster", "")),
                    )
                    for it in items
                ]
            except Exception:
                return []
        return await self.get_tv_shows(page)

    async def get_details(self, item_id: str) -> Optional[MediaDetails]:
        try:
            url = item_id if item_id.startswith("http") else f"{self.base_url}/{item_id}"
            html = await self._get(url)
            # Parse __NEXT_DATA__ script
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            script = soup.select_one("script#__NEXT_DATA__")
            if not script:
                return None
            data = json.loads(script.string)
            apollo_state = data.get("props", {}).get("pageProps", {}).get("apolloState", {})

            media_key = None
            for key in apollo_state:
                if key.startswith("Dorama:") or key.startswith("Movie:"):
                    media_key = key
                    break
            if not media_key:
                return None
            md = apollo_state[media_key]

            is_movie = media_key.startswith("Movie:")
            title = f"{md.get('name', '')} ({md.get('name_es', '')})".strip()
            poster = self._poster_url(md.get("poster_path") or md.get("poster", ""))
            overview = md.get("overview")

            seasons = []
            if not is_movie:
                # Fetch seasons
                dorama_id = md.get("_id", "")
                season_query = """query listSeasons($serie_id: MongoID!) {
  listSeasons(sort: NUMBER_ASC, filter: {serie_id: $serie_id}) { slug season_number poster_path __typename }
}"""
                try:
                    sdata = await self._gql("listSeasons", {"serie_id": dorama_id}, season_query)
                    for s in sdata.get("data", {}).get("listSeasons", []):
                        seasons.append(Season(
                            id=f"{dorama_id}/{s['season_number']}",
                            number=s["season_number"],
                            title=f"Temporada {s['season_number']}",
                        ))
                except Exception:
                    pass

            return MediaDetails(
                id=item_id, title=title, type="movie" if is_movie else "series",
                poster=poster, overview=overview, seasons=seasons,
            )
        except Exception:
            return None

    async def get_servers(self, movie_id: str) -> list[Server]:
        try:
            url = movie_id if movie_id.startswith("http") else f"{self.base_url}/{movie_id}"
            html = await self._get(url)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            script = soup.select_one("script#__NEXT_DATA__")
            if not script:
                return []
            data = json.loads(script.string)
            apollo_state = data.get("props", {}).get("pageProps", {}).get("apolloState", {})

            servers = []
            # Try getMovieLinks first (new API structure) - keys have $ prefix in Apollo state
            for key, val in apollo_state.items():
                if "getMovieLinks" in key or "getDoramaLinks" in key:
                    links_online = val.get("links_online", {})
                    links_json = links_online.get("json", [])
                    for link in links_json:
                        server_url = link.get("link", "")
                        if server_url:
                            name = server_url.split("//")[-1].split("/")[0].split(".")[0].capitalize()
                            lang_code = link.get("lang", "")
                            lang = self._LANG_MAP.get(lang_code, "")
                            servers.append(Server(id=server_url, name=f"{name} {lang}".strip()))
                    if servers:
                        return servers

            # Fallback: old Episode/Movie structure
            for key, val in apollo_state.items():
                if key.startswith("Episode:") or key.startswith("Movie:"):
                    links = val.get("links_online", {}).get("json", [])
                    for link in links:
                        server_url = link.get("link", "")
                        lang = self._LANG_MAP.get(link.get("lang", ""), "")
                        if server_url:
                            name = server_url.split("//")[-1].split("/")[0].split(".")[0].capitalize()
                            servers.append(Server(id=server_url, name=f"{name} {lang}".strip()))
                    if servers:
                        break
            return servers
        except Exception:
            return []
