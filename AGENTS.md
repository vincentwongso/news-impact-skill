# AGENTS.md

Setup instructions for AI agents (Claude Code, Hermes, OpenClaw, and any
agentskills.io-compatible runtime) asked to install and run this repo.

If you were pointed at this repo with "check it out and install it," follow the
steps below top to bottom. Each step ends with a command whose output you can
check before moving on — do not claim success without running the verify steps.

## What this is

A standalone Python CLI (and portable agent skill) that turns free Yahoo Finance
RSS into a short, ranked, watchlist-scoped briefing. It fetches news, dedupes and
pre-filters against the user's symbols, then uses an LLM to rank each story's
likely impact per symbol. Output is JSON on stdout.

**Advisory only.** It reads, ranks, and reports. It never places, sizes, or
suggests orders, and imports nothing broker-related. Do not extend it to do so
without an explicit request.

## Install

Requires Python 3.11+. From the repo root:

```bash
pip install -e ".[dev]"
```

**Verify** the install and that the CLI is wired up — this needs no API key and
no network:

```bash
python skills/news-impact/scripts/rank.py --help
```

Expect a usage block listing `--config`, `--since`, `--min-severity`,
`--watchlist`, `--source`, `--model`, `--cache`. If you get a `ModuleNotFoundError`
instead, the install step failed — re-run it before continuing.

**Verify** the logic offline (no network, no key):

```bash
pytest
```

Expect all tests to pass in well under a second. This exercises the fetch →
dedupe → pre-filter → cache → ranker pipeline against fakes, so green here means
the install is sound regardless of API keys.

## Configure

```bash
cp skills/news-impact/config.example.yaml config.yaml
```

Then edit `config.yaml`: set the user's `watchlist` (e.g. `[EURUSD, XAUUSD]`) and
`model`. The `model` value selects the provider:

| `model:`            | Provider          | Key env            |
|---------------------|-------------------|--------------------|
| `deepseek-v4-flash` | OpenAI-compatible | `DEEPSEEK_API_KEY` |
| `haiku`             | Anthropic         | `ANTHROPIC_API_KEY`|
| `ollama:<model>`    | local Ollama      | none               |
| `openai:<model>`    | OpenAI            | `OPENAI_API_KEY`   |

API keys are read from **environment variables only** — never write a key into
`config.yaml`. Export the one matching the chosen model (skip for Ollama):

```bash
export DEEPSEEK_API_KEY=...   # or ANTHROPIC_API_KEY, OPENAI_API_KEY
```

## Run

```bash
python skills/news-impact/scripts/rank.py --config config.yaml --since 4h --min-severity medium
```

Flags override config; with no flags it reads `config.yaml` as-is. The command
prints a `{"briefings": [...]}` JSON object to stdout. Your job is to invoke it
and narrate that JSON for the user — the CLI is the contract; do not reimplement
its logic.

## How agents discover the skill

This repo follows the agentskills.io `SKILL.md` layout at
`skills/news-impact/SKILL.md`. Runtimes that auto-load skills (e.g. Claude Code)
can invoke it by name; others can read that file directly for the condensed
contract. `references/` holds the alias map and source details.

## Boundaries to respect

- Advisory only — no order placement, no broker integration, no position sizing.
- The ranker reasons **only** from the supplied headline + summary; it returns
  empty impacts when nothing on the watchlist is affected. That is correct
  behavior, not a bug.
- Keys come from the environment, never config or source.

For the full design, data model, and extension points, see
[`docs/architecture.md`](docs/architecture.md).
