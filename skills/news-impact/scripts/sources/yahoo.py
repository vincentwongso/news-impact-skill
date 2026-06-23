from __future__ import annotations

import sys
from datetime import datetime, timezone

import feedparser
import httpx

from models import NewsItem
from sources.base import SourceAdapter, register

_FEED_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={sym}&region=US&lang=en-US"
# Symbols needing a non-default Yahoo mapping go here; default appends "=X".
_OVERRIDES: dict[str, str] = {}


def yahoo_symbol(symbol: str) -> str:
    if symbol in _OVERRIDES:
        return _OVERRIDES[symbol]
    return symbol if "=" in symbol else f"{symbol}=X"


def _to_utc(entry) -> datetime | None:
    tm = entry.get("published_parsed")
    if tm is None:
        return None
    return datetime(*tm[:6], tzinfo=timezone.utc)


def parse_feed(xml: str, source: str = "yahoo") -> list[NewsItem]:
    parsed = feedparser.parse(xml)
    items: list[NewsItem] = []
    for entry in parsed.entries:
        title = entry.get("title")
        link = entry.get("link")
        if not title or not link:
            continue
        published = _to_utc(entry)
        if published is None:
            print(f"[warn] yahoo: skipping undated entry: {title}", file=sys.stderr)
            continue
        items.append(
            NewsItem(
                title=title,
                summary=entry.get("summary", ""),
                url=link,
                source=source,
                published=published,
            )
        )
    return items


@register
class YahooSource(SourceAdapter):
    name = "yahoo"

    def fetch(self, watchlist: list[str]) -> list[NewsItem]:
        out: list[NewsItem] = []
        for symbol in watchlist:
            url = _FEED_URL.format(sym=yahoo_symbol(symbol))
            try:
                resp = httpx.get(url, timeout=10.0,
                                 headers={"User-Agent": "news-impact-skill/0.1"})
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                print(f"[warn] yahoo fetch failed for {symbol}: {exc}", file=sys.stderr)
                continue
            out.extend(parse_feed(resp.text))
        return out
