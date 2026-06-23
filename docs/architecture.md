# Architecture

`news-impact-skill` turns a firehose of free financial news into a short, ranked briefing
scoped to a trader's watchlist. The core is a plain Python CLI (`flags → JSON on stdout`)
that runs anywhere; the `skills/news-impact/` wrapper makes it loadable as a portable agent
skill.

## Design goals

1. **Standalone** — no broker, no MCP server, no external state. Inputs are a config file and
   public news feeds.
2. **Config-driven** — watchlist, model, lookback, severity, and sources all live in one
   `config.yaml`, read on every run. No hidden session state.
3. **Free first, paid optional** — works with zero API keys for fetching (Yahoo RSS); only the
   ranker needs a model key (or a local Ollama with none).
4. **Cheap then smart** — a keyword/entity pre-filter and a content-hash cache discard the bulk
   of the stream before any LLM token is spent.
5. **Advisory only** — output is a briefing for a human. There is no order-placement code path
   and nothing broker-related is imported.

## Pipeline

```
                 ┌──────── sources/ (adapters) ────────┐
   Yahoo RSS ───▶│  fetch raw  →  emit NewsItem        │
   X / paid  ───▶│  (stubs, behind one interface)      │
                 └──────────────────┬──────────────────┘
                                    ▼
                          normalise + dedupe        (lexical: canonical URL + fuzzy title)
                                    ▼
                       pre-filter (watchlist + aliases)   cheap, no LLM; drops zero-hit items
                                    ▼
                          cache lookup (by hash)
                              hit │ miss
                           ┌──────┘ └──────┐
                           ▼               ▼
                    cached impacts   LLM ranker (batched, structured output)
                           │               │ write-through cache
                           └──────┬────────┘
                                  ▼
                    filter by severity / lookback
                                  ▼
                       Briefing[] (ranked JSON) → stdout
```

## Components

| Component | File | Responsibility |
|---|---|---|
| CLI | `scripts/rank.py` | Parse flags, load config, run pipeline, print JSON, set exit codes. The only contract with the agent. |
| Pipeline | `scripts/pipeline.py` | Orchestrates the stages below. |
| Source adapters | `scripts/sources/` | `SourceAdapter` ABC + registry; Yahoo implemented, others stubbed. Each emits `NewsItem[]`. |
| Deduper | `scripts/dedupe.py` | `Deduper` interface; `LexicalDeduper` collapses syndication and near-duplicate titles. |
| Pre-filter | `scripts/prefilter.py` | Word-boundary match of watchlist symbols + alias terms against title+summary. |
| Cache | `scripts/cache.py` | SQLite store of past impacts, keyed so model/watchlist/prompt changes invalidate. |
| Ranker | `scripts/ranker/` | `Ranker` ABC + prompt builder + provider adapters (Anthropic, OpenAI-compatible, Ollama). |
| Config | `scripts/config.py` | Pydantic config load/validate, CLI override merge, model→provider resolution. |
| Models | `scripts/models.py` | `NewsItem`, `Impact`, `Briefing`, and the ranker output schemas (Pydantic). |

## Data model

**`NewsItem`** — the normalisation boundary every adapter emits:

```jsonc
{
  "id": "sha256(title + url + published)",   // computed; unique item identity
  "title": "US CPI comes in above forecast at 3.4% y/y",
  "summary": "…",
  "url": "https://…",
  "source": "yahoo",
  "published": "2026-06-19T12:30:00+00:00",  // tz-aware UTC
  "sentiment": null,                          // pre-filled by sources that tag it
  "matched_symbols": ["XAUUSD"]               // attached by the pre-filter
}
```

**`Briefing`** — one entry per surviving story, assembled by the pipeline from a `NewsItem` plus
the impacts the ranker returns for its `id`:

```jsonc
{
  "headline": "…",
  "source": "yahoo",
  "published": "2026-06-19T12:30:00+00:00",
  "impacts": [
    { "symbol": "XAUUSD", "direction": "bullish|bearish|neutral",
      "severity": "low|medium|high", "horizon": "intraday|swing|longterm",
      "confidence": 0.0-1.0, "why": "…" }
  ],
  "grounding": "Based only on the provided headline and summary."
}
```

Pydantic generates the JSON Schema that drives structured output for all three providers and
validates the model's response on the way back.

## Cost & correctness boundaries

- **Cost is structural**: pre-filter → cache → batched ranking, in that order. The model only
  ever sees a fraction of the stream, and each unique story is paid once. The cache key is
  `sha256(item.id + sorted(watchlist) + model_id + prompt_version)`, so changing your watchlist,
  switching models, or bumping the prompt correctly re-ranks; re-runs over the same config are
  free.
- **No hallucinated facts**: the ranker is instructed to reason only from the supplied
  title+summary, return an empty `impacts` array when nothing on the watchlist is affected, and
  prefer low confidence when unsure. Malformed output triggers one retry, then that batch is
  skipped — the run still emits everything else.
- **Graceful degradation**: a source fetch error logs a warning to stderr and the run continues;
  stdout stays clean JSON.

## Extension points

- **New source** — implement `SourceAdapter.fetch(watchlist) -> list[NewsItem]`, decorate with
  `@register`, and enable it in `config.yaml`. Symbol mapping lives in the adapter.
- **New model provider** — the registry in `config.py` maps a friendly `model:` value to a
  provider adapter; add a row or a prefix (`openai:`, `openrouter:`, …).
- **Semantic dedup** — the current `LexicalDeduper` catches syndication and minor title variants
  but not cross-source paraphrase. A `SemanticDeduper` (embedding cosine-cluster) can drop in
  behind the same `Deduper` interface when multiple sources are enabled — no pipeline change.

## Composing with a trading stack (not a dependency)

If a separate market-data or execution tool is also installed, the *agent* — not this skill —
can call both in one turn ("show my XAUUSD exposure given this bearish headline"). That
composition happens at the agent layer; `news-impact-skill` neither knows nor cares whether
anything else is present.
