import json
import pytest
from datetime import datetime, timezone
from models import NewsItem
from config import ModelSpec, ConfigError
from ranker.openai_compat import OpenAICompatRanker
from ranker.ollama import OllamaRanker

def _spec():
    return ModelSpec(provider="openai_compat", model_id="deepseek-chat",
                     base_url="https://api.deepseek.com", api_key_env="DEEPSEEK_API_KEY")

def _item():
    return NewsItem(title="CPI hot", summary="up", url="u", source="yahoo",
                    published=datetime(2026, 6, 19, tzinfo=timezone.utc))

class _FakeMessage:
    def __init__(self, content): self.content = content
class _FakeChoice:
    def __init__(self, content): self.message = _FakeMessage(content)
class _FakeCompletion:
    def __init__(self, content): self.choices = [_FakeChoice(content)]

class _FakeClient:
    # Mimics openai client: client.chat.completions.create(...)
    def __init__(self, content):
        self._content = content
        self.last_kwargs = None
    @property
    def chat(self): return self
    @property
    def completions(self): return self
    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeCompletion(self._content)

def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        OpenAICompatRanker(_spec())._client()

def test_complete_sends_schema_and_returns_content(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "x")
    item = _item()
    content = json.dumps({"results": [{"id": item.id, "grounding": "g", "impacts": []}]})
    ranker = OpenAICompatRanker(_spec())
    fake = _FakeClient(content)
    ranker._client = lambda: fake  # type: ignore
    out = ranker.rank([item], ["EURUSD"], {})
    assert out[0].id == item.id
    # schema was attached to the request
    assert fake.last_kwargs["response_format"]["type"] == "json_schema"

def test_ollama_needs_no_key(monkeypatch):
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    spec = ModelSpec(provider="ollama", model_id="llama3.1:8b",
                     base_url="http://localhost:11434/v1")
    # constructing the client must not raise for missing key
    r = OllamaRanker(spec)
    assert r._api_key() == "ollama"
