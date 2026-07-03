"""Provider registry."""
from .cinecalidad import CineCalidadProvider
from .sololatino import SoloLatinoProvider
from .latinanime import LatinAnimeProvider
from .lacartoons import LaCartoonsProvider
from .jkanime import JKanimeProvider
from .pelisplusto import PelisplustoProvider
from .flixlatam import FlixLatamProvider
from .iptv import IPTVProvider
from .cablevisionhd import CableVisionHDProvider

PROVIDERS = [
    CineCalidadProvider(),
    PelisplustoProvider(),
    FlixLatamProvider(),
    SoloLatinoProvider(),
    LatinAnimeProvider(),
    LaCartoonsProvider(),
    JKanimeProvider(),
    IPTVProvider(),
    CableVisionHDProvider(),
]

def get_provider(name: str):
    for p in PROVIDERS:
        if p.name.lower() == name.lower():
            return p
    return None
