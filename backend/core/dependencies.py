from typing import Generator

from .config import settings

def get_settings() -> Generator:
    yield settings
