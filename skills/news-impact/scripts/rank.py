from __future__ import annotations

import argparse
import json
import os
import sys

import pipeline as pipeline_mod
import ranker.base as ranker_mod
from cache import ImpactCache
from config import ConfigError, apply_overrides, load_config, resolve_model


def parse_since(value: str) -> int:
    v = value.strip().lower()
    if v.endswith("h"):
        v = v[:-1]
    try:
        return int(v)
    except ValueError as exc:
        raise ValueError(f"Invalid --since value '{value}' (use e.g. 4h or 4)") from exc


def default_cache_path() -> str:
    base = os.path.join(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, "news_impact_cache.sqlite")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rank.py", description="Watchlist-scoped news briefing.")
    p.add_argument("--config", required=True, help="Path to config.yaml")
    p.add_argument("--since", help="Lookback window, e.g. 4h")
    p.add_argument("--min-severity", choices=["low", "medium", "high"])
    p.add_argument("--watchlist", help="Comma-separated symbols to override config")
    p.add_argument("--source", help="Enable only this source")
    p.add_argument("--model", help="Override model")
    p.add_argument("--cache", help="Path to cache SQLite file")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        cfg = load_config(args.config)
        cfg = apply_overrides(
            cfg,
            since_hours=parse_since(args.since) if args.since else None,
            min_severity=args.min_severity,
            watchlist=[s.strip() for s in args.watchlist.split(",")] if args.watchlist else None,
            source=args.source,
            model=args.model,
        )
        spec = resolve_model(cfg.model)
        ranker = ranker_mod.build_ranker(spec)
        cache = ImpactCache(args.cache or default_cache_path())
        result = pipeline_mod.run_pipeline(
            cfg, model_id=spec.model_id, ranker=ranker, cache=cache
        )
    except ConfigError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"[error] ranking failed: {exc}", file=sys.stderr)
        return 1
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
