from __future__ import annotations

import os

from config import ConfigError, ModelSpec
from models import RankerOutput
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

    def _schema(self) -> dict:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "ranker_output",
                "schema": RankerOutput.model_json_schema(),
                "strict": False,
            },
        }

    def _complete(self, system: str, user: str) -> str:
        client = self._client()
        completion = client.chat.completions.create(
            model=self.spec.model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format=self._schema(),
        )
        return completion.choices[0].message.content or ""
