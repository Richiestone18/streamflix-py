"""
Provider registry.
"""
from .lamovie import LaMovieProvider
from .sololatino import SoloLatinoProvider
from .latinanime import LatinAnimeProvider
from .lacartoons import LaCartoonsProvider
from .pelisplusto import PelisplustoProvider
from .flixlatam import FlixLatamProvider
from .iptv import IPTVProvider
from .cablevisionhd import CableVisionHDProvider
# New providers from streamflix-reborn
from .doramasflix import DoramasflixProvider
from .pelisflixhd import PelisflixHdProvider
from .magistv import MagistvProvider
from .seriesflix import SeriesFlixProvider
from .tvporinternethd import TvporinternetHDProvider
from .tvlibrefutbol import TvLibrefutbolProvider
from .plutotvmx import PlutoTvMxProvider
from .plutotvar import PlutoTvArProvider
from .animefenix import AnimefenixProvider
from .latanime import LatanimeProvider

PROVIDERS = [
    LaMovieProvider(),
    PelisplustoProvider(),
    FlixLatamProvider(),
    SoloLatinoProvider(),
    LatinAnimeProvider(),
    LaCartoonsProvider(),
    IPTVProvider(),
    CableVisionHDProvider(),
    # New providers
    DoramasflixProvider(),
    PelisflixHdProvider(),
    MagistvProvider(),
    SeriesFlixProvider(),
    TvporinternetHDProvider(),
    TvLibrefutbolProvider(),
    PlutoTvMxProvider(),
    PlutoTvArProvider(),
    AnimefenixProvider(),
    LatanimeProvider(),
]

def get_provider(name: str):
    for p in PROVIDERS:
        if p.name.lower() == name.lower():
            return p
    return None