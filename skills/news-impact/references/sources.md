# Sources

| Source | Status | Key | Notes |
|---|---|---|---|
| yahoo | implemented | none | Per-symbol RSS (`EURUSD` → `EURUSD=X`). Free, no key. |
| x (Twitter) | stub | paid | No free read API since Feb 2026 (pay-per-use); Nitter RSS effectively dead. |
| finnhub | stub | `FINNHUB_KEY` | Reserved behind the SourceAdapter interface. |
| marketaux | stub | key | Reserved; pre-tags sentiment. |

## Adding a source

Implement `SourceAdapter` (`sources/base.py`): set `name`, implement
`fetch(watchlist) -> list[NewsItem]`, and decorate with `@register`. Enable it in
`config.yaml` under `sources:`. Keys are read from the environment only.

## Dedup upgrade path

This build uses **Tier A lexical** dedup (canonical URL + fuzzy title via rapidfuzz). It
collapses syndication and minor headline variants but not cross-source paraphrase. When
multiple sources are enabled, a `SemanticDeduper` (embedding cosine-cluster) can drop in
behind the same `Deduper` interface (`dedupe.py`) — config-selected, no pipeline change.
