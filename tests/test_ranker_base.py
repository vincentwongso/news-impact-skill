import json
import pytest
from datetime import datetime, timezone
from models import NewsItem
from ranker.base import Ranker, RankerError, build_system_prompt, build_user_payload

def _item():
    it = NewsItem(title="US CPI hot", summary="up", url="u", source="yahoo",
                  published=datetime(2026, 6, 19, tzinfo=timezone.utc))
    it.matched_symbols = ["XAUUSD"]
    return it

class FakeRanker(Ranker):
    def __init__(self, responses):
        self._responses = list(responses)
    def _complete(self, system, user):
        return self._responses.pop(0)

def _good_response(item_id):
    return json.dumps({"results": [{"id": item_id, "grounding": "g", "impacts": [
        {"symbol": "XAUUSD", "direction": "bearish", "severity": "high",
         "horizon": "intraday", "confidence": 0.7, "why": "hot"}]}]})

def test_prompt_mentions_watchlist_and_grounding_rule():
    p = build_system_prompt(["EURUSD"], {"USD": ["Fed"]})
    assert "EURUSD" in p
    assert "only" in p.lower()  # reason-only-from-text instruction

def test_user_payload_includes_id_and_matched_symbols():
    payload = json.loads(build_user_payload([_item()]))
    assert payload[0]["matched_symbols"] == ["XAUUSD"]
    assert "id" in payload[0]

def test_rank_parses_results():
    item = _item()
    out = FakeRanker([_good_response(item.id)]).rank([item], ["XAUUSD"], {})
    assert out[0].id == item.id
    assert out[0].impacts[0].severity == "high"

def test_retry_once_then_succeeds():
    item = _item()
    r = FakeRanker(["not json", _good_response(item.id)])
    out = r.rank([item], ["XAUUSD"], {})
    assert out[0].impacts[0].direction == "bearish"

def test_two_failures_raise_rankererror():
    item = _item()
    with pytest.raises(RankerError):
        FakeRanker(["bad", "still bad"]).rank([item], ["XAUUSD"], {})
