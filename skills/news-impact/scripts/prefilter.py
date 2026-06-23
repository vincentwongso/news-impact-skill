from __future__ import annotations

import re

from models import NewsItem


def build_symbol_terms(
    watchlist: list[str], aliases: dict[str, list[str]]
) -> dict[str, set[str]]:
    terms: dict[str, set[str]] = {}
    for sym in watchlist:
        bag = {sym}
        upper = sym.upper()
        for code, alias_list in aliases.items():
            if code.upper() in upper:
                bag.add(code)
                bag.update(alias_list)
        terms[sym] = bag
    return terms


def _matchers(terms: set[str]) -> list[re.Pattern]:
    return [re.compile(rf"\b{re.escape(t)}\b", re.IGNORECASE) for t in terms]


def prefilter(
    items: list[NewsItem], watchlist: list[str], aliases: dict[str, list[str]]
) -> list[NewsItem]:
    symbol_terms = build_symbol_terms(watchlist, aliases)
    compiled = {sym: _matchers(t) for sym, t in symbol_terms.items()}
    survivors: list[NewsItem] = []
    for item in items:
        text = f"{item.title} {item.summary}"
        hits = [sym for sym in watchlist
                if any(p.search(text) for p in compiled[sym])]
        if hits:
            item.matched_symbols = hits
            survivors.append(item)
    return survivors
