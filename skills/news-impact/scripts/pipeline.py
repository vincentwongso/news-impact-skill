# skills/news-impact/scripts/pipeline.py
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

from cache import ImpactCache, cache_key
from config import Config
from dedupe import LexicalDeduper
from models import Briefing, Impact, ItemImpacts, NewsItem
from prefilter import prefilter
from ranker.base import PROMPT_VERSION, Ranker, RankerError
from sources.base import SOURCE_REGISTRY

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}
BATCH_SIZE = 10


def _fetch_enabled(config: Config) -> list[NewsItem]:
    items: list[NewsItem] = []
    for name, sc in config.sources.items():
        if not sc.enabled:
            continue
        cls = SOURCE_REGISTRY.get(name)
        if cls is None:
            print(f"[warn] unknown source '{name}' — skipped", file=sys.stderr)
            continue
        try:
            items.extend(cls().fetch(config.watchlist))
        except NotImplementedError as exc:
            print(f"[warn] {exc}", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 — never let one source kill the run
            print(f"[warn] source '{name}' failed: {exc}", file=sys.stderr)
    return items


def _chunks(items: list[NewsItem], size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def run_pipeline(
    config: Config,
    *,
    model_id: str,
    ranker: Ranker,
    cache: ImpactCache,
    now: datetime | None = None,
    source_items: list[NewsItem] | None = None,
) -> dict:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=config.lookback_hours)

    items = source_items if source_items is not None else _fetch_enabled(config)
    items = LexicalDeduper().dedupe(items)
    items = prefilter(items, config.watchlist, config.aliases)
    items = [it for it in items if it.published >= cutoff]

    # cache lookup
    impacts_by_id: dict[str, list[Impact]] = {}
    grounding_by_id: dict[str, str] = {}
    misses: list[NewsItem] = []
    for it in items:
        key = cache_key(it.id, config.watchlist, model_id, PROMPT_VERSION)
        cached = cache.get(key)
        if cached is None:
            misses.append(it)
        else:
            impacts_by_id[it.id] = cached
            grounding_by_id[it.id] = "Served from cache."

    # rank misses in batches
    for batch in _chunks(misses, BATCH_SIZE):
        try:
            results: list[ItemImpacts] = ranker.rank(batch, config.watchlist, config.aliases)
        except RankerError as exc:
            print(f"[warn] ranker batch dropped: {exc}", file=sys.stderr)
            continue
        by_id = {r.id: r for r in results}
        for it in batch:
            r = by_id.get(it.id)
            if r is None:
                continue
            impacts_by_id[it.id] = r.impacts
            grounding_by_id[it.id] = r.grounding
            cache.set(cache_key(it.id, config.watchlist, model_id, PROMPT_VERSION), r.impacts)

    # assemble + filter
    floor = SEVERITY_ORDER[config.min_severity]
    briefings: list[Briefing] = []
    for it in items:
        impacts = [im for im in impacts_by_id.get(it.id, [])
                   if SEVERITY_ORDER[im.severity] >= floor]
        if not impacts:
            continue
        briefings.append(Briefing(
            headline=it.title, source=it.source, published=it.published,
            impacts=impacts, grounding=grounding_by_id.get(it.id, ""),
        ))

    return {"briefings": [b.model_dump(mode="json") for b in briefings]}
