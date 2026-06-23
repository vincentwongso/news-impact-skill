from datetime import datetime, timezone, timedelta
from models import NewsItem
from dedupe import LexicalDeduper, canonical_url, normalize_title

BASE = datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc)

def _item(title, url, minutes=0, symbols=None):
    it = NewsItem(title=title, summary="", url=url, source="yahoo",
                  published=BASE + timedelta(minutes=minutes))
    it.matched_symbols = symbols or []
    return it

def test_canonical_url_strips_query_and_www():
    assert canonical_url("https://www.X.com/a?utm=1#frag") == "https://x.com/a"

def test_normalize_title_strips_source_suffix_and_punct():
    assert normalize_title("Fed holds rates! - Reuters") == "fed holds rates"

def test_same_canonical_url_collapses_keeping_earliest():
    items = [_item("A", "https://x.com/a?utm=1", minutes=5),
             _item("A", "https://x.com/a", minutes=0)]
    out = LexicalDeduper().dedupe(items)
    assert len(out) == 1
    assert out[0].published == BASE  # earliest kept

def test_near_titles_collapse_and_union_symbols():
    items = [_item("Fed holds rates steady", "https://x.com/1", minutes=2, symbols=["EURUSD"]),
             _item("Fed holds rates steady today", "https://y.com/2", minutes=0, symbols=["XAUUSD"])]
    out = LexicalDeduper().dedupe(items)
    assert len(out) == 1
    assert set(out[0].matched_symbols) == {"EURUSD", "XAUUSD"}

def test_distinct_titles_survive():
    items = [_item("Fed holds rates", "https://x.com/1"),
             _item("OPEC cuts output", "https://x.com/2")]
    assert len(LexicalDeduper().dedupe(items)) == 2
