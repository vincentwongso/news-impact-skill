from __future__ import annotations

from ranker.openai_compat import OpenAICompatRanker


class OllamaRanker(OpenAICompatRanker):
    def _api_key(self) -> str:
        # Local Ollama needs no real key; the OpenAI client requires a non-empty string.
        return "ollama"
