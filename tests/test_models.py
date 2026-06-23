import pytest
from datetime import datetime, timezone
from models import NewsItem, Impact, RankerOutput, make_id

def _dt():
    return datetime(2026, 6, 19, 12, 30, tzinfo=timezone.utc)

def test_newsitem_id_is_deterministic_and_url_sensitive():
    a = NewsItem(title="CPI hot", summary="s", url="http://x/1", source="yahoo", published=_dt())
    b = NewsItem(title="CPI hot", summary="s", url="http://x/1", source="yahoo", published=_dt())
    c = NewsItem(title="CPI hot", summary="s", url="http://x/2", source="yahoo", published=_dt())
    assert a.id == b.id
    assert a.id != c.id
    assert a.id == make_id("CPI hot", "http://x/1", _dt())

def test_newsitem_naive_datetime_is_coerced_to_utc():
    item = NewsItem(title="t", summary="s", url="u", source="yahoo",
                    published=datetime(2026, 6, 19, 12, 30))
    assert item.published.tzinfo is not None
    assert item.published.utcoffset().total_seconds() == 0

def test_impact_confidence_bounds_enforced():
    with pytest.raises(Exception):
        Impact(symbol="EURUSD", direction="bullish", severity="high",
               horizon="intraday", confidence=1.5, why="x")

def test_ranker_output_round_trips_json():
    payload = '{"results":[{"id":"abc","grounding":"g","impacts":[' \
              '{"symbol":"XAUUSD","direction":"bearish","severity":"high",' \
              '"horizon":"intraday","confidence":0.7,"why":"hot inflation"}]}]}'
    out = RankerOutput.model_validate_json(payload)
    assert out.results[0].id == "abc"
    assert out.results[0].impacts[0].direction == "bearish"
