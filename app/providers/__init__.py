"""Provider registry."""
from .cinecalidad import CineCalidadProvider
from .sololatino import SoloLatinoProvider
from .latinanime import LatinAnimeProvider
from .lacartoons import LaCartoonsProvider
from .animeflv import AnimeFLVProvider
from .pelisplusto import PelisplustoProvider
from .flixlatam import FlixLatamProvider
from .iptv import IPTVProvider

PROVIDERS = [
    CineCalidadProvider(),
    PelisplustoProvider(),
    FlixLatamProvider(),
    SoloLatinoProvider(),
    LatinAnimeProvider(),
    LaCartoonsProvider(),
    AnimeFLVProvider(),
    IPTVProvider(),
]

def get_provider(name: str):
    for p in PROVIDERS:
        if p.name.lower() == name.lower():
            return p
    return None
