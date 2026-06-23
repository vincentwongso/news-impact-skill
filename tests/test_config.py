import pytest
from config import load_config, apply_overrides, Config, ConfigError

VALID = """
watchlist: [EURUSD, XAUUSD]
model: deepseek-v4-flash
lookback_hours: 4
min_severity: medium
sources:
  yahoo: { enabled: true }
  finnhub: { enabled: false, api_key_env: FINNHUB_KEY }
aliases:
  USD: [Powell, Fed]
"""

def _write(tmp_path, text):
    p = tmp_path / "config.yaml"
    p.write_text(text)
    return str(p)

def test_load_valid(tmp_path):
    cfg = load_config(_write(tmp_path, VALID))
    assert cfg.watchlist == ["EURUSD", "XAUUSD"]
    assert cfg.sources["yahoo"].enabled is True
    assert cfg.min_severity == "medium"

def test_reject_bad_min_severity(tmp_path):
    bad = VALID.replace("min_severity: medium", "min_severity: critical")
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, bad))

def test_reject_empty_watchlist(tmp_path):
    bad = VALID.replace("watchlist: [EURUSD, XAUUSD]", "watchlist: []")
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, bad))

def test_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_config(str(tmp_path / "nope.yaml"))

def test_apply_overrides(tmp_path):
    cfg = load_config(_write(tmp_path, VALID))
    out = apply_overrides(cfg, since_hours=8, min_severity="high",
                          watchlist=["GBPUSD"], model="haiku")
    assert out.lookback_hours == 8
    assert out.min_severity == "high"
    assert out.watchlist == ["GBPUSD"]
    assert out.model == "haiku"
    # original unchanged
    assert cfg.lookback_hours == 4
