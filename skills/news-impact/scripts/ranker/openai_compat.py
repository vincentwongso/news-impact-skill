from __future__ import annotations

import os

from config import ConfigError, ModelSpec
from ranker.base import Ranker


class OpenAICompatRanker(Ranker):
    def __init__(self, spec: ModelSpec):
        self.spec = spec

    def _api_key(self) -> str:
        env = self.spec.api_key_env
        key = os.environ.get(env) if env else None
        if not key:
            raise ConfigError(f"Missing API key: set ${env} in the environment.")
        return key

    def _client(self):
        from openai import OpenAI
        return OpenAI(base_url=self.spec.base_url, api_key=self._api_key())

    def _complete(self, system: str, user: str) -> str:
        client = self._client()
        # json_object is the portable structured-output mode: OpenAI, DeepSeek,
        # OpenRouter, and Ollama's OpenAI-compatible endpoint all accept it,
        # whereas json_schema is rejected by DeepSeek ("This response_format
        # type is unavailable now"). The system prompt fully specifies the
        # output shape, and _complete_with_retry validates it against
        # RankerOutput, so the looser mode is safe here.
        completion = client.chat.completions.create(
            model=self.spec.model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        return completion.choices[0].message.content or ""
