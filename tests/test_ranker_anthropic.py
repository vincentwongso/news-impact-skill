import pytest
from datetime import datetime, timezone
from models import NewsItem
from config import ModelSpec, ConfigError
from ranker.anthropic import AnthropicRanker

def _spec():
    return ModelSpec(provider="anthropic", model_id="claude-haiku-4-5",
                     api_key_env="ANTHROPIC_API_KEY")

def _item():
    return NewsItem(title="CPI hot", summary="up", url="u", source="yahoo",
                    published=datetime(2026, 6, 19, tzinfo=timezone.utc))

class _Block:
    def __init__(self, data): self.type = "tool_use"; self.input = data
class _Msg:
    def __init__(self, data): self.content = [_Block(data)]
class _FakeMessages:
    def __init__(self, data): self._data = data; self.last_kwargs = None
    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _Msg(self._data)
class _FakeClient:
    def __init__(self, data): self.messages = _FakeMessages(data)

def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        AnthropicRanker(_spec())._client()

def test_tool_use_input_parsed(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    item = _item()
    data = {"results": [{"id": item.id, "grounding": "g", "impacts": []}]}
    r = AnthropicRanker(_spec())
    fake = _FakeClient(data)
    r._client = lambda: fake  # type: ignore
    out = r.rank([item], ["EURUSD"], {})
    assert out[0].id == item.id
    assert fake.messages.last_kwargs["tool_choice"]["name"] == r.TOOL_NAME
