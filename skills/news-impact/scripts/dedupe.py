from __future__ import annotations

import re
from abc import ABC, abstractmethod
from urllib.parse import urlsplit, urlunsplit

from rapidfuzz import fuzz

from models import NewsItem

FUZZ_THRESHOLD = 85
_SUFFIX_SEPS = (" - ", " — ", " | ")
_PUNCT = re.compile(r"[^\w\s]")
_WS = re.compile(r"\s+")


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), host, path, "", ""))


def normalize_title(title: str) -> str:
    t = title.strip()
    for sep in _SUFFIX_SEPS:
        if sep in t:
            t = t.split(sep)[0]
    t = _PUNCT.sub("", t.lower())
    return _WS.sub(" ", t).strip()


class Deduper(ABC):
    @abstractmethod
    def dedupe(self, items: list[NewsItem]) -> list[NewsItem]:
        ...


class LexicalDeduper(Deduper):
    def dedupe(self, items: list[NewsItem]) -> list[NewsItem]:
        reps: list[NewsItem] = []
        rep_urls: list[str] = []
        rep_titles: list[str] = []
        for item in items:
            cu = canonical_url(item.url)
            nt = normalize_title(item.title)
            match_idx = None
            for i, (ru, rt) in enumerate(zip(rep_urls, rep_titles)):
                if cu == ru or fuzz.token_set_ratio(nt, rt) >= FUZZ_THRESHOLD:
                    match_idx = i
                    break
            if match_idx is None:
                reps.append(item)
                rep_urls.append(cu)
                rep_titles.append(nt)
            else:
                reps[match_idx] = _merge(reps[match_idx], item)
        return reps


def _merge(keep: NewsItem, other: NewsItem) -> NewsItem:
    winner = keep if keep.published <= other.published else other
    symbols = list(dict.fromkeys([*keep.matched_symbols, *other.matched_symbols]))
    winner.matched_symbols = symbols
    return winner
