from __future__ import annotations

import json
import os

from config import ConfigError, ModelSpec
from models import RankerOutput
from ranker.base import Ranker


# Non-streaming output cap. Haiku 4.5 supports up to 64K output tokens, but the
# SDK recommends staying near ~16K for non-streaming requests to avoid HTTP
# timeouts. 16K gives a batch of ~10 items ample room for multi-impact results.
MAX_OUTPUT_TOKENS = 16000


class AnthropicRanker(Ranker):
    TOOL_NAME = "emit_ranker_output"

    def __init__(self, spec: ModelSpec):
        self.spec = spec

    def _api_key(self) -> str:
        key = os.environ.get(self.spec.api_key_env or "ANTHROPIC_API_KEY")
        if not key:
            raise ConfigError("Missing API key: set $ANTHROPIC_API_KEY in the environment.")
        return key

    def _client(self):
        from anthropic import Anthropic
        return Anthropic(api_key=self._api_key())

    def _complete(self, system: str, user: str) -> str:
        client = self._client()
        msg = client.messages.create(
            model=self.spec.model_id,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=system,
            tools=[{
                "name": self.TOOL_NAME,
                "description": "Emit the ranked impact results.",
                "input_schema": RankerOutput.model_json_schema(),
            }],
            tool_choice={"type": "tool", "name": self.TOOL_NAME},
            messages=[{"role": "user", "content": user}],
        )
        for block in msg.content:
            if getattr(block, "type", None) == "tool_use":
                return json.dumps(block.input)
        raise ValueError("No tool_use block in Anthropic response")
