from datetime import datetime, timezone
from models import NewsItem
from prefilter import prefilter, build_symbol_terms

ALIASES = {"USD": ["Powell", "Fed", "CPI"], "EUR": ["ECB", "Lagarde"],
           "XAU": ["gold", "bullion"]}
WATCH = ["EURUSD", "XAUUSD"]

def _item(title, summary=""):
    return NewsItem(title=title, summary=summary, url="u" + title, source="yahoo",
                    published=datetime(2026, 6, 19, tzinfo=timezone.utc))

def test_terms_decompose_pairs_into_alias_keys():
    terms = build_symbol_terms(WATCH, ALIASES)
    assert "Powell" in terms["EURUSD"]   # USD leg
    assert "ECB" in terms["EURUSD"]      # EUR leg
    assert "gold" in terms["XAUUSD"]     # XAU leg

def test_alias_hit_attaches_symbol():
    out = prefilter([_item("Powell signals higher for longer")], WATCH, ALIASES)
    assert len(out) == 1
    assert out[0].matched_symbols == ["EURUSD", "XAUUSD"]

def test_gold_keyword_hits_xauusd_only():
    out = prefilter([_item("Gold rallies to record")], WATCH, ALIASES)
    assert out[0].matched_symbols == ["XAUUSD"]

def test_zero_hit_dropped():
    assert prefilter([_item("Local sports team wins")], WATCH, ALIASES) == []

def test_word_boundary_no_false_substring():
    # "fedex" must not match the "Fed" alias
    assert prefilter([_item("FedEx earnings beat")], WATCH, ALIASES) == []
