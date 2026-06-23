import pytest
from config import resolve_model, ConfigError

def test_deepseek_default():
    s = resolve_model("deepseek-v4-flash")
    assert s.provider == "openai_compat"
    assert s.base_url == "https://api.deepseek.com"
    assert s.api_key_env == "DEEPSEEK_API_KEY"

def test_haiku():
    s = resolve_model("haiku")
    assert s.provider == "anthropic"
    assert s.model_id == "claude-haiku-4-5"
    assert s.api_key_env == "ANTHROPIC_API_KEY"

def test_ollama_prefix_keeps_full_model_tag():
    s = resolve_model("ollama:llama3.1:8b")
    assert s.provider == "ollama"
    assert s.model_id == "llama3.1:8b"
    assert s.base_url == "http://localhost:11434/v1"
    assert s.api_key_env is None

def test_openai_prefix():
    s = resolve_model("openai:gpt-4o-mini")
    assert s.provider == "openai_compat"
    assert s.model_id == "gpt-4o-mini"
    assert s.api_key_env == "OPENAI_API_KEY"

def test_unknown_model_raises():
    with pytest.raises(ConfigError):
        resolve_model("totally-unknown")
