from __future__ import annotations

from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

Severity = Literal["low", "medium", "high"]


class ConfigError(Exception):
    pass


class SourceConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    enabled: bool = False


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")
    watchlist: list[str] = Field(min_length=1)
    model: str = "deepseek-v4-flash"
    lookback_hours: int = Field(default=4, gt=0)
    min_severity: Severity = "medium"
    sources: dict[str, SourceConfig] = Field(default_factory=dict)
    aliases: dict[str, list[str]] = Field(default_factory=dict)


def load_config(path: str) -> Config:
    try:
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
    except FileNotFoundError as exc:
        raise ConfigError(f"Config file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    try:
        return Config.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"Invalid config: {exc}") from exc


def apply_overrides(
    cfg: Config,
    *,
    since_hours: int | None = None,
    min_severity: str | None = None,
    watchlist: list[str] | None = None,
    source: str | None = None,
    model: str | None = None,
) -> Config:
    data = cfg.model_dump()
    if since_hours is not None:
        data["lookback_hours"] = since_hours
    if min_severity is not None:
        data["min_severity"] = min_severity
    if watchlist is not None:
        data["watchlist"] = watchlist
    if model is not None:
        data["model"] = model
    if source is not None:
        data["sources"] = {
            name: ({**sc, "enabled": name == source})
            for name, sc in data["sources"].items()
        }
    try:
        return Config.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"Invalid override: {exc}") from exc


Provider = Literal["anthropic", "openai_compat", "ollama"]


class ModelSpec(BaseModel):
    provider: Provider
    model_id: str
    base_url: str | None = None
    api_key_env: str | None = None


# Friendly alias -> concrete provider spec.
# NOTE: confirm the exact DeepSeek API model string; placeholder below.
_REGISTRY: dict[str, ModelSpec] = {
    "deepseek-v4-flash": ModelSpec(
        provider="openai_compat",
        model_id="deepseek-chat",  # TODO-CONFIRM exact DeepSeek model id
        base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
    ),
    "haiku": ModelSpec(
        provider="anthropic",
        model_id="claude-haiku-4-5",
        api_key_env="ANTHROPIC_API_KEY",
    ),
}

_PREFIX = {
    "ollama": ModelSpec(provider="ollama", model_id="",
                        base_url="http://localhost:11434/v1"),
    "openai": ModelSpec(provider="openai_compat", model_id="",
                        base_url="https://api.openai.com/v1",
                        api_key_env="OPENAI_API_KEY"),
    "openrouter": ModelSpec(provider="openai_compat", model_id="",
                            base_url="https://openrouter.ai/api/v1",
                            api_key_env="OPENROUTER_API_KEY"),
}


def resolve_model(model: str) -> ModelSpec:
    if ":" in model:
        prefix, rest = model.split(":", 1)
        if prefix in _PREFIX:
            return _PREFIX[prefix].model_copy(update={"model_id": rest})
    if model in _REGISTRY:
        return _REGISTRY[model]
    raise ConfigError(
        f"Unknown model '{model}'. Use deepseek-v4-flash, haiku, "
        f"ollama:<model>, openai:<model>, or openrouter:<model>."
    )
