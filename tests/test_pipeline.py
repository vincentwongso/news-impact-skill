# tests/test_pipeline.py
from datetime import datetime, timezone, timedelta
from models import NewsItem, ItemImpacts, Impact
from config import Config
from cache import ImpactCache
from ranker.base import Ranker
from pipeline import run_pipeline

NOW = datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc)


def _cfg():
    return Config(watchlist=["XAUUSD"], model="x", lookback_hours=4,
                  min_severity="medium", sources={}, aliases={"XAU": ["gold"]})


def _item(title, minutes_ago=0):
    return NewsItem(title=title, summary="", url="u" + title, source="yahoo",
                    published=NOW - timedelta(minutes=minutes_ago))


class StubRanker(Ranker):
    def __init__(self, by_title_severity):
        self.map = by_title_severity
        self.calls = 0

    def _complete(self, system, user):
        raise AssertionError("unused")

    def rank(self, items, watchlist, aliases):
        self.calls += 1
        out = []
        for it in items:
            sev = self.map.get(it.title)
            impacts = (
                [Impact(symbol="XAUUSD", direction="bearish", severity=sev,
                        horizon="intraday", confidence=0.6, why="x")]
                if sev
                else []
            )
            out.append(ItemImpacts(id=it.id, impacts=impacts, grounding="g"))
        return out


def test_filters_below_min_severity_and_drops_empty(tmp_path):
    items = [_item("Gold low impact"), _item("Gold big move")]
    ranker = StubRanker({"Gold low impact": "low", "Gold big move": "high"})
    cache = ImpactCache(str(tmp_path / "c.sqlite"))
    out = run_pipeline(_cfg(), model_id="x", ranker=ranker, cache=cache,
                       now=NOW, source_items=items)
    titles = [b["headline"] for b in out["briefings"]]
    assert titles == ["Gold big move"]  # low dropped, empty dropped


def test_lookback_excludes_old_items(tmp_path):
    items = [_item("Gold big move", minutes_ago=10),
             _item("Gold stale", minutes_ago=600)]  # 10h ago > 4h lookback
    ranker = StubRanker({"Gold big move": "high", "Gold stale": "high"})
    cache = ImpactCache(str(tmp_path / "c.sqlite"))
    out = run_pipeline(_cfg(), model_id="x", ranker=ranker, cache=cache,
                       now=NOW, source_items=items)
    assert [b["headline"] for b in out["briefings"]] == ["Gold big move"]


def test_cache_hit_skips_ranker(tmp_path):
    items = [_item("Gold big move")]
    cache = ImpactCache(str(tmp_path / "c.sqlite"))
    r1 = StubRanker({"Gold big move": "high"})
    run_pipeline(_cfg(), model_id="x", ranker=r1, cache=cache, now=NOW, source_items=items)
    r2 = StubRanker({"Gold big move": "high"})
    run_pipeline(_cfg(), model_id="x", ranker=r2, cache=cache, now=NOW, source_items=list(items))
    assert r2.calls == 0  # served entirely from cache


def test_prefilter_drops_unrelated(tmp_path):
    items = [_item("Local sports result")]
    ranker = StubRanker({})
    cache = ImpactCache(str(tmp_path / "c.sqlite"))
    out = run_pipeline(_cfg(), model_id="x", ranker=ranker, cache=cache,
                       now=NOW, source_items=items)
    assert out["briefings"] == []
    assert ranker.calls == 0
