from __future__ import annotations

import json
from abc import ABC, abstractmethod

from pydantic import ValidationError

from config import ModelSpec
from models import ItemImpacts, NewsItem, RankerOutput

PROMPT_VERSION = "v1"


class RankerError(Exception):
    pass


def build_system_prompt(watchlist: list[str], aliases: dict[str, list[str]]) -> str:
    alias_lines = "\n".join(f"  {k}: {', '.join(v)}" for k, v in aliases.items())
    return (
        "You are a financial-news impact ranker. For each news item, judge its "
        "impact on the trader's watchlist symbols.\n\n"
        f"Watchlist symbols: {', '.join(watchlist)}\n"
        f"Symbol aliases:\n{alias_lines}\n\n"
        "Rules:\n"
        "- Reason ONLY from the supplied title and summary. Never invent facts.\n"
        "- Return one result per input item, keyed by its exact 'id'.\n"
        "- If nothing on the watchlist is affected, return an empty 'impacts' array.\n"
        "- Prefer low confidence when unsure. Only use watchlist symbols.\n"
        "- 'direction' ∈ bullish|bearish|neutral; 'severity' ∈ low|medium|high; "
        "'horizon' ∈ intraday|swing|longterm; 'confidence' ∈ [0,1].\n"
        'Respond with a single JSON object of the form '
        '{"results": [{"id": "<item id>", "impacts": [{"symbol", "direction", '
        '"severity", "horizon", "confidence", "why"}], "grounding": "<note>"}]} '
        "with exactly one element in 'results' per input item."
    )


def build_user_payload(items: list[NewsItem]) -> str:
    rows = [
        {
            "id": it.id,
            "title": it.title,
            "summary": it.summary,
            "published": it.published.isoformat(),
            "matched_symbols": it.matched_symbols,
        }
        for it in items
    ]
    return json.dumps(rows)


class Ranker(ABC):
    @abstractmethod
    def _complete(self, system: str, user: str) -> str:
        """Return a RankerOutput JSON string from the provider."""

    def _complete_with_retry(self, system: str, user: str) -> RankerOutput:
        last_exc: Exception | None = None
        for _ in range(2):
            try:
                raw = self._complete(system, user)
                data = json.loads(raw)
                # Some providers (e.g. DeepSeek in json_object mode) emit the
                # results array at the top level rather than the documented
                # {"results": [...]} wrapper; accept either shape.
                if isinstance(data, list):
                    data = {"results": data}
                return RankerOutput.model_validate(data)
            except (ValidationError, ValueError) as exc:
                last_exc = exc
        raise RankerError(f"Ranker returned unparseable output: {last_exc}")

    def rank(
        self, items: list[NewsItem], watchlist: list[str], aliases: dict[str, list[str]]
    ) -> list[ItemImpacts]:
        system = build_system_prompt(watchlist, aliases)
        user = build_user_payload(items)
        return self._complete_with_retry(system, user).results


def build_ranker(spec: ModelSpec) -> Ranker:
    if spec.provider == "anthropic":
        from ranker.anthropic import AnthropicRanker
        return AnthropicRanker(spec)
    if spec.provider == "ollama":
        from ranker.ollama import OllamaRanker
        return OllamaRanker(spec)
    from ranker.openai_compat import OpenAICompatRanker
    return OpenAICompatRanker(spec)
