---
name: news-impact
description: Turn free financial news into a short, ranked briefing scoped to a trader's watchlist. Use when the user wants to know which recent headlines matter for their symbols (forex, gold, indices) and how. Advisory only — never places or sizes trades.
---

# news-impact

Fetches Yahoo Finance RSS, dedupes and pre-filters against your watchlist, and uses an
LLM to rank each surviving story's impact per symbol. Output is JSON on stdout.

## Setup

1. `pip install -e .` (from the repo root).
2. Copy `config.example.yaml` to `config.yaml`; set your `watchlist` and `model`.
3. Default model is **local Ollama** (free, no key): `ollama pull llama3.1:8b`,
   then keep `ollama serve` running on `localhost:11434`.
   For a paid hosted model instead, set `model: deepseek-v4-flash` and
   `export DEEPSEEK_API_KEY=...` (or `haiku` → `ANTHROPIC_API_KEY`).

## Run

```bash
python scripts/rank.py --config config.yaml --since 4h --min-severity medium
```

Flags override config: `--since`, `--min-severity`, `--watchlist`, `--source`, `--model`,
`--config`, `--cache`. No flags = pure config.

## Output

`{"briefings": [{ "headline", "source", "published", "impacts": [...], "grounding" }]}`
Each impact has `symbol, direction, severity, horizon, confidence, why`.

## Boundaries

Advisory only. No order placement, no broker integration. Reasons only from the supplied
headline + summary; returns empty impacts when nothing on the watchlist is affected.

## References

- `references/symbol-aliases.md` — how the alias pre-filter works.
- `references/sources.md` — source coverage, limits, and the dedup upgrade path.
