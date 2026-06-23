from __future__ import annotations

from models import NewsItem
from sources.base import SourceAdapter, register


class _Stub(SourceAdapter):
    def fetch(self, watchlist: list[str]) -> list[NewsItem]:
        raise NotImplementedError(
            f"Source '{self.name}' is not implemented in this build. "
            f"It is reserved behind the SourceAdapter interface."
        )


@register
class XSource(_Stub):
    name = "x"


@register
class FinnhubSource(_Stub):
    name = "finnhub"


@register
class MarketauxSource(_Stub):
    name = "marketaux"
