from __future__ import annotations

import hashlib
import json
import sqlite3

from pydantic import TypeAdapter

from models import Impact

_ADAPTER = TypeAdapter(list[Impact])


def cache_key(item_id: str, watchlist: list[str], model_id: str, prompt_version: str) -> str:
    raw = f"{item_id}|{','.join(sorted(watchlist))}|{model_id}|{prompt_version}"
    return hashlib.sha256(raw.encode()).hexdigest()


class ImpactCache:
    def __init__(self, path: str):
        self._conn = sqlite3.connect(path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS impacts "
            "(cache_key TEXT PRIMARY KEY, impacts_json TEXT NOT NULL)"
        )
        self._conn.commit()

    def get(self, key: str) -> list[Impact] | None:
        row = self._conn.execute(
            "SELECT impacts_json FROM impacts WHERE cache_key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        return _ADAPTER.validate_json(row[0])

    def set(self, key: str, impacts: list[Impact]) -> None:
        payload = _ADAPTER.dump_json(impacts).decode()
        self._conn.execute(
            "INSERT OR REPLACE INTO impacts (cache_key, impacts_json) VALUES (?, ?)",
            (key, payload),
        )
        self._conn.commit()
