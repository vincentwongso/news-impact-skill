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

def test_parse_feed_skips_entries_without_date():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item>
    <title>Dated item</title>
    <link>https://finance.yahoo.com/news/dated.html</link>
    <description>has a date</description>
    <pubDate>Thu, 19 Jun 2026 12:30:00 GMT</pubDate>
  </item>
  <item>
    <title>Undated item</title>
    <link>https://finance.yahoo.com/news/undated.html</link>
    <description>no pubDate</description>
  </item>
</channel></rss>"""
    items = parse_feed(xml, source="yahoo")
    assert len(items) == 1
    assert items[0].title == "Dated item"
