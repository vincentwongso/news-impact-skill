# news-impact-skill

Turn free financial news into a short, ranked briefing scoped to your watchlist.

A standalone Python CLI (and portable agent skill) that fetches Yahoo Finance RSS,
dedupes and pre-filters against your symbols, then uses an LLM to rank each story's
likely impact per symbol. Output is JSON on stdout.

> **Advisory only.** It reads, ranks, and reports. It never places, sizes, or suggests
> orders, and imports nothing broker-related.

## How it works

```
fetch (Yahoo RSS) → dedupe → pre-filter (watchlist + aliases) → cache → LLM ranker → JSON
```

The pre-filter and content-hash cache keep cost down: only watchlist-relevant, uncached
stories ever reach the model. See [`docs/architecture.md`](docs/architecture.md) for the full
design, data model, and extension points.

## Install

> **AI agents:** point your agent at [`AGENTS.md`](AGENTS.md) — it has a
> deterministic, copy-pasteable install + verify sequence written for Claude Code,
> Hermes, OpenClaw, and other agentskills.io runtimes.

```bash
pip install -e .          # Python 3.11+
cp skills/news-impact/config.example.yaml config.yaml
```

The ranker needs a model. The default is a **local Ollama** — free, no key, and
nothing leaves your machine:

```bash
# 1. Install Ollama — https://ollama.com/download
# 2. Pull the model the example config uses (one-time, ~4.7 GB):
ollama pull llama3.1:8b
# 3. Make sure it's serving (the macOS/Windows app starts this for you):
ollama serve
```

Ollama listens on `http://localhost:11434`, which is where the skill looks by default.

**Paid alternative — DeepSeek (or any hosted model).** To use a hosted model instead
of running one locally, set `model: deepseek-v4-flash` in `config.yaml` and export the
matching key:

```bash
export DEEPSEEK_API_KEY=...   # or ANTHROPIC_API_KEY for haiku, OPENAI_API_KEY for openai:<model>
```

API keys are read from environment variables only — never from config.

## Usage

```bash
python skills/news-impact/scripts/rank.py --config config.yaml --since 4h --min-severity medium
```

Flags override config: `--since`, `--min-severity`, `--watchlist`, `--source`, `--model`,
`--cache`. With no flags, it reads `config.yaml` as-is. It also runs from cron or any shell.

### Output

```json
{
  "briefings": [
    {
      "headline": "US CPI comes in above forecast at 3.4% y/y",
      "source": "yahoo",
      "published": "2026-06-19T12:30:00+00:00",
      "impacts": [
        { "symbol": "XAUUSD", "direction": "bearish", "severity": "high",
          "horizon": "intraday", "confidence": 0.72,
          "why": "Hotter inflation pushes back rate-cut expectations." }
      ],
      "grounding": "Based only on the provided headline and summary."
    }
  ]
}
```

## Configuration

```yaml
watchlist: [EURUSD, XAUUSD, GBPUSD]
model: ollama:llama3.1:8b     # local default; or deepseek-v4-flash | haiku | openai:<model>
lookback_hours: 4
min_severity: medium          # low | medium | high
sources:
  yahoo: { enabled: true }
aliases:
  USD: [Powell, Fed, FOMC, CPI, NFP]
  XAU: [gold, bullion, XAU]
```

See `skills/news-impact/references/` for the alias map and source details.

## Models

Provider is resolved from the `model` value:

| `model:`            | Provider                | Key env            |
|---------------------|-------------------------|--------------------|
| `ollama:<model>`    | local Ollama (default)  | none               |
| `deepseek-v4-flash` | OpenAI-compatible       | `DEEPSEEK_API_KEY` |
| `haiku`             | Anthropic               | `ANTHROPIC_API_KEY`|
| `openai:<model>`    | OpenAI                  | `OPENAI_API_KEY`   |

## Sources

Yahoo Finance RSS (free, no key) is implemented. X and paid adapters (Finnhub, MarketAux)
are stubs behind a stable `SourceAdapter` interface — add one by implementing `fetch()` and
registering it. Cross-source semantic dedup is a documented future extension.

## Development

```bash
pip install -e ".[dev]"
pytest          # offline, no network
ruff check skills tests
```

## Use as an agent skill

The `skills/news-impact/` directory follows the [agentskills.io](https://agentskills.io)
`SKILL.md` layout, so it loads into compatible agents (Claude Code, Hermes, etc.). The CLI
is the contract — the agent invokes it and narrates the JSON.

## License

[MIT](LICENSE)
