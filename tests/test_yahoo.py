from pathlib import Path
from sources.yahoo import parse_feed, yahoo_symbol, YahooSource

FIX = Path(__file__).parent / "fixtures" / "yahoo_eurusd.xml"

def test_symbol_mapping():
    assert yahoo_symbol("EURUSD") == "EURUSD=X"
    assert yahoo_symbol("XAUUSD") == "XAUUSD=X"

def test_parse_feed_yields_newsitems():
    items = parse_feed(FIX.read_text(), source="yahoo")
    assert len(items) == 2
    first = items[0]
    assert first.title.startswith("US CPI")
    assert first.url.endswith("123.html")
    assert first.source == "yahoo"
    assert first.published.year == 2026 and first.published.tzinfo is not None
    assert first.id  # computed

def test_parse_feed_handles_empty_or_garbage():
    assert parse_feed("not xml at all") == []

def test_yahoo_source_registered():
    from sources.base import SOURCE_REGISTRY
    assert SOURCE_REGISTRY["yahoo"] is YahooSource
