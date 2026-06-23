# news-impact-skill — Design Spec

**Date:** 2026-06-23
**Status:** Approved for planning
**Source architecture:** `news-impact-skill-architecture.md` (high-level); this spec pins down the decisions that doc leaves open and scopes the first build.

## 1. Purpose & scope

A standalone agent skill that turns free financial news into a short, ranked briefing scoped to a trader's watchlist. Built as a portable `SKILL.md` wrapping a plain Python CLI (`flags → JSON on stdout`) that also runs from cron or a shell with no agent.

**This build is a thin vertical slice:** one source (Yahoo Finance RSS) through the entire spine — normalise → dedupe → pre-filter → cache → LLM ranker → JSON briefing. Everything else (X, paid adapters, semantic dedup) ships as a documented, disabled seam behind a stable interface.

**Hard boundaries (unchanged from architecture doc):**
- Advisory only. No order placement, no broker import, no MT5 dependency.
- Free-first. The default path needs zero API keys to *fetch*; only the ranker needs a model key (or a local Ollama with none).
- Config-driven. Watchlist/model/lookback/severity/sources live in `config.yaml`, read every run. No session state.

## 2. Locked decisions (from brainstorming)

| Decision | Choice | Rationale |
|---|---|---|
| Sources (this build) | **Yahoo Finance RSS only**; X + paid adapters are registered NotImplemented stubs behind `SourceAdapter` ABC | X has no free read API (pay-per-use since Feb 2026); Nitter RSS effectively dead. Add sources later behind the ABC. |
| Ranker | **Provider-agnostic**: `Ranker` ABC + `anthropic`, `openai_compat`, `ollama` adapters | Standalone CLI must call a model itself; pluggable from day one. |
| Default model | **`deepseek-v4-flash`** (cheap + good) → **`haiku`** if Anthropic-native → **`ollama:<model>`** for local | User preference. |
| Schemas/validation | **Pydantic v2** for models, config, and structured output | One model def generates JSON Schema for all three providers and validates output. |
| Dedup | **Tier A lexical**: canonical URL + normalized-title fuzzy match (`rapidfuzz`) | Yahoo-only has no cross-source paraphrase case yet; semantic dedup is a documented future seam. |
| Cache key | `sha256(item.id + sorted(watchlist) + model_id + prompt_version)` | Impacts depend on text **and** watchlist + model + prompt. |

## 3. Repo layout

```
news-impact-skill/
├── pyproject.toml                # deps, ruff, pytest config; py3.11+
├── news-impact-skill-architecture.md
├── docs/superpowers/specs/2026-06-23-news-impact-skill-design.md
├── skills/news-impact/
│   ├── SKILL.md                  # agent-facing: when/how to invoke, examples
│   ├── config.example.yaml       # template (default model: deepseek-v4-flash)
│   ├── scripts/
│   │   ├── rank.py               # CLI entrypoint (argparse → pipeline → JSON stdout)
│   │   ├── pipeline.py           # orchestrates stages
│   │   ├── dedupe.py             # Deduper interface + LexicalDeduper (Tier A)
│   │   ├── prefilter.py          # watchlist + alias matching
│   │   ├── cache.py              # SQLite content-hash cache
│   │   ├── config.py             # Pydantic config load/validate + CLI merge + model resolution
│   │   ├── models.py             # NewsItem / Impact / Briefing (Pydantic)
│   │   ├── sources/
│   │   │   ├── base.py           # SourceAdapter ABC + registry
│   │   │   ├── yahoo.py          # implemented
│   │   │   └── stubs.py          # x / finnhub / marketaux … NotImplemented, registered, disabled
│   │   └── ranker/
│   │       ├── base.py           # Ranker ABC + shared prompt builder
│   │       ├── anthropic.py
│   │       ├── openai_compat.py  # OpenAI / DeepSeek / OpenRouter / vLLM
│   │       └── ollama.py         # OpenAI-compatible client → localhost:11434/v1
│   └── references/
│       ├── symbol-aliases.md     # bundled default alias map docs
│       └── sources.md            # per-source coverage/limits/keys; dedup upgrade path
└── tests/                        # pytest, fully offline
```

**Dependencies:** `pydantic`, `pyyaml`, `feedparser`, `httpx`, `rapidfuzz`, `anthropic`, `openai`. Python 3.11+.
(`openai` SDK also drives Ollama via its OpenAI-compatible `/v1` endpoint and any OpenAI-compatible host.)

## 4. Data models (`models.py`, Pydantic v2)

### NewsItem — the normalisation boundary every adapter emits
```python
class NewsItem(BaseModel):
    id: str                       # sha256(title + url + published), computed
    title: str
    summary: str
    url: str
    source: str                   # "yahoo"
    published: datetime           # tz-aware UTC
    sentiment: float | None = None  # pre-filled by sources that tag it; null for Yahoo
    # populated by prefilter, not adapters:
    matched_symbols: list[str] = []
```
- `id` = `sha256((title + url + published.isoformat()).encode()).hexdigest()` — unique item identity.
- **Dedupe key** is *separate* from `id` (see §6): `id` includes the URL, so the same headline under two tickers would not collapse on `id`.

### Impact / Briefing — ranker output
```python
class Impact(BaseModel):
    symbol: str
    direction: Literal["bullish", "bearish", "neutral"]
    severity: Literal["low", "medium", "high"]
    horizon: Literal["intraday", "swing", "longterm"]
    confidence: float = Field(ge=0.0, le=1.0)
    why: str

class Briefing(BaseModel):
    headline: str
    source: str
    published: datetime
    impacts: list[Impact]          # empty when nothing on the watchlist is affected
    grounding: str
```
`Briefing.model_json_schema()` (a wrapper `RankerOutput` with `briefings: list[Briefing]`) feeds all three providers' structured-output mechanisms and validates responses on the way back.

## 5. Configuration (`config.py`)

`config.yaml` shape (matches architecture doc) with `model` defaulting to `deepseek-v4-flash`:

```yaml
watchlist: [EURUSD.z, XAUUSD.z, GBPUSD.z]
model: deepseek-v4-flash      # deepseek-v4-flash (default) | haiku | ollama:llama3.1:8b | openai:gpt-...
lookback_hours: 4
min_severity: medium          # low | medium | high
sources:
  yahoo:   { enabled: true }
  x:       { enabled: false, accounts: ["@..."] }    # stub
  finnhub: { enabled: false, api_key_env: FINNHUB_KEY }  # stub
aliases:
  EUR: [Lagarde, ECB, euro, eurozone]
  USD: [Powell, Fed, FOMC, CPI, NFP]
  XAU: [gold, bullion, XAU]
  OIL: [OPEC, crude, WTI, Brent]
```

- Loaded + validated by a Pydantic `Config` model. Unknown keys rejected; ranges enforced.
- **CLI overrides** merge on top of file values (`--since`, `--min-severity`, `--watchlist`, `--source`, `--model`, `--config`).
- **Model resolution** — a registry maps `model:` → adapter:

| `model:` value | Adapter | Endpoint / real id | Key env |
|---|---|---|---|
| `deepseek-v4-flash` *(default)* | `openai_compat` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` |
| `haiku` | `anthropic` | `claude-haiku-4-5` | `ANTHROPIC_API_KEY` |
| `ollama:<model>` | `ollama` | `http://localhost:11434/v1` | none |
| `openai:<model>` / `openrouter:<model>` | `openai_compat` | provider base URL | provider key env |

The exact DeepSeek API model string lives in the registry (one-line change if it differs from the alias). **API keys come from env only — never the config file.**

## 6. Dedup (`dedupe.py`) — Tier A lexical

`Deduper` interface: `dedupe(items: list[NewsItem]) -> list[NewsItem]`. One implementation now: `LexicalDeduper`.

1. **Canonical URL collapse** — normalise host (lowercase, strip `www.`), drop query/fragment/tracking params; items sharing a canonical URL collapse (syndication).
2. **Normalized-title fuzzy match** — normalise title (lowercase, strip source suffixes like `— Reuters`, strip punctuation, collapse whitespace), then cluster with `rapidfuzz` token-set ratio ≥ **0.85**.
3. **Survivor selection** — within a cluster keep the **earliest `published`**; union `matched_symbols` if already attached.

Limitation (documented in `sources.md`): lexical dedup does not catch cross-source paraphrase. **Future seam:** a `SemanticDeduper` (embedding cosine-cluster) drops in behind the same interface, config-selected, when multi-source/paid sources are enabled — no pipeline change.

## 7. Pipeline (`pipeline.py`)

```
for each enabled source: fetch() → NewsItem[]      # Yahoo only now; errors → stderr warn, continue
   → normalise (already NewsItem) → dedupe (LexicalDeduper)
   → prefilter(watchlist + aliases)                # drop zero-hit; attach matched_symbols
   → cache lookup by cache key
        hit  → cached Impact list
        miss → ranker.rank(batch of ~10) → validate → write-through cache
   → assemble Briefing[]; filter impacts by min_severity; filter items by lookback_hours
   → JSON to stdout
```

- **Pre-filter** (`prefilter.py`): case-insensitive, word-boundary match of each watchlist symbol's base + its alias terms against `title + summary`. Survivors carry `matched_symbols` forward so the ranker focuses on relevant symbols. Zero hits → dropped before any LLM cost.
- **Cache** (`cache.py`): SQLite under the skill dir. Key = `sha256(item.id + sorted(watchlist) + model_id + prompt_version)`. Stores the validated `Impact` list per item. Write-through on ranker miss. `prompt_version` is a constant bumped when the prompt changes.
- **Batching:** cache-miss items chunked (~10/call) into one ranker request returning `RankerOutput.briefings`.

## 8. Ranker (`ranker/`)

- `Ranker` ABC: `rank(items: list[NewsItem], watchlist, aliases) -> list[Briefing]`. Shared prompt builder in `base.py`.
- **Prompt / grounding:** system prompt instructs the model to reason **only** from supplied title + summary, return an **empty `impacts`** array when nothing on the watchlist is affected, prefer **low confidence** when unsure, and never invent facts. Watchlist + aliases passed as context so the model knows valid symbols.
- **Structured output per adapter:**
  - `anthropic.py`: forced tool-use, `input_schema = RankerOutput.model_json_schema()`.
  - `openai_compat.py`: `response_format` json_schema (strict); base URL + key env from registry (DeepSeek default).
  - `ollama.py`: same OpenAI-compatible client, `base_url=http://localhost:11434/v1`, no key.
- **Validation/retry:** responses parsed through Pydantic; malformed output → **one retry**, then that batch is dropped with a stderr warning (run still emits everything else).

## 9. CLI contract (`rank.py`)

```bash
python scripts/rank.py --since 4h --min-severity medium
# → JSON briefing on stdout, scoped to config.yaml's watchlist
```
- Flags: `--since`, `--min-severity`, `--watchlist`, `--source`, `--model`, `--config <path>`. No flags = pure config.
- **stdout = JSON only** (the agent reads & narrates). Logs, warnings, progress → **stderr**.
- Imports nothing trading-related; only network calls are to news sources and the model endpoint.

## 10. Error handling

| Failure | Behaviour |
|---|---|
| Source fetch / RSS parse error | stderr warning, skip that source, continue (empty result is valid JSON `{"briefings": []}`) |
| Pre-filter drops everything | Valid empty briefing, exit 0 |
| Ranker malformed output | one retry → drop that batch with stderr warning; emit the rest |
| Ranker total provider failure (auth/network after backoff) | exit non-zero with a clear stderr message |
| Missing/invalid config | exit non-zero, Pydantic validation error to stderr |
| Missing model key env | exit non-zero with a message naming the expected env var |

## 11. Testing (TDD, `tests/`)

Fully offline. Built test-first.
- **Sources:** recorded Yahoo RSS fixture → expected `NewsItem[]`; malformed feed → graceful skip.
- **Dedupe:** canonical-URL collapse; near-title fuzzy collapse at the 0.85 threshold; earliest-published survivor.
- **Prefilter:** alias hit/miss, word-boundary correctness, `matched_symbols` attachment.
- **Cache:** hit returns cached Impact; key invalidation on watchlist/model/prompt_version change.
- **Pipeline:** end-to-end with a `FakeRanker` (no network) → asserts severity/lookback filtering and JSON shape.
- **Ranker adapters:** against mocked HTTP — request shape (schema in the request) and validation/retry on malformed responses.
- **Config:** valid load, range enforcement, CLI override merge, model resolution registry.

## 12. Out of scope (this build)

- Any source other than Yahoo (stubs only).
- Semantic / embedding dedup (documented seam only).
- `--format text` / human-rendered output (JSON only; the agent narrates).
- Order placement, sizing, broker/MT5 integration — permanently out of scope for this skill.
