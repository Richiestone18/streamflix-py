"""streamflix-py — Backend API server.

Run: uvicorn app.server:app --reload
"""

from . import providers
from . import base


def get_provider(name: str):
    return providers.get_provider(name)