import json
import pytest
from rank import parse_since, main


def test_parse_since_variants():
    assert parse_since("4h") == 4
    assert parse_since("12") == 12
    with pytest.raises(ValueError):
        parse_since("soon")


def test_missing_config_exits_nonzero(capsys, tmp_path):
    rc = main(["--config", str(tmp_path / "nope.yaml")])
    assert rc != 0
    assert "not found" in capsys.readouterr().err.lower()


def test_end_to_end_emits_json(monkeypatch, capsys, tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "watchlist: [XAUUSD]\nmodel: haiku\nlookback_hours: 4\n"
        "min_severity: medium\nsources: {yahoo: {enabled: false}}\n"
        "aliases: {XAU: [gold]}\n"
    )
    # stub the ranker + sources so no network is touched
    from datetime import datetime, timezone
    from models import NewsItem, ItemImpacts, Impact
    item = NewsItem(title="Gold surges on hot CPI", summary="gold", url="u",
                    source="yahoo", published=datetime.now(timezone.utc))

    import pipeline as pl
    monkeypatch.setattr(pl, "_fetch_enabled", lambda config: [item])

    import ranker.base as rb
    class _Stub(rb.Ranker):
        def _complete(self, system, user):
            raise AssertionError
        def rank(self, items, watchlist, aliases):
            return [ItemImpacts(id=i.id, grounding="g", impacts=[
                Impact(symbol="XAUUSD", direction="bullish", severity="high",
                       horizon="intraday", confidence=0.6, why="cpi")]) for i in items]
    monkeypatch.setattr(rb, "build_ranker", lambda spec: _Stub())

    rc = main(["--config", str(cfg), "--cache", str(tmp_path / "c.sqlite")])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["briefings"][0]["headline"].startswith("Gold surges")
