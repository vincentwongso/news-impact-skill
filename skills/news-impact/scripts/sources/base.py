from __future__ import annotations

from abc import ABC, abstractmethod

from models import NewsItem

SOURCE_REGISTRY: dict[str, type["SourceAdapter"]] = {}


def register(cls: type["SourceAdapter"]) -> type["SourceAdapter"]:
    SOURCE_REGISTRY[cls.name] = cls
    return cls


class SourceAdapter(ABC):
    name: str = ""

    @abstractmethod
    def fetch(self, watchlist: list[str]) -> list[NewsItem]:
        """Fetch from this source and return normalised NewsItems."""
