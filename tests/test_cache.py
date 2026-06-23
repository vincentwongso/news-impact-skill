from models import Impact
from cache import ImpactCache, cache_key


def _impact():
    return Impact(symbol="XAUUSD", direction="bearish", severity="high",
                  horizon="intraday", confidence=0.7, why="hot cpi")


def test_key_changes_with_watchlist_model_and_prompt():
    base = cache_key("id1", ["EURUSD"], "m1", "v1")
    assert base != cache_key("id1", ["EURUSD", "XAUUSD"], "m1", "v1")
    assert base != cache_key("id1", ["EURUSD"], "m2", "v1")
    assert base != cache_key("id1", ["EURUSD"], "m1", "v2")
    # order-independent watchlist
    assert cache_key("id1", ["A", "B"], "m1", "v1") == cache_key("id1", ["B", "A"], "m1", "v1")


def test_set_then_get_round_trips(tmp_path):
    c = ImpactCache(str(tmp_path / "c.sqlite"))
    k = cache_key("id1", ["EURUSD"], "m1", "v1")
    assert c.get(k) is None
    c.set(k, [_impact()])
    got = c.get(k)
    assert got is not None and got[0].direction == "bearish"


def test_persists_across_instances(tmp_path):
    path = str(tmp_path / "c.sqlite")
    k = cache_key("id1", ["EURUSD"], "m1", "v1")
    ImpactCache(path).set(k, [_impact()])
    assert ImpactCache(path).get(k)[0].symbol == "XAUUSD"
