from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


def init_db(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                path TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input_path TEXT NOT NULL,
                style_intent TEXT,
                status TEXT NOT NULL,
                message TEXT,
                recipe_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


@contextmanager
def db_conn(db_path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def history_insert(
    db_path: Path,
    *,
    input_path: str,
    style_intent: str | None,
    status: str,
    message: str,
    recipe: dict[str, Any] | None = None,
) -> None:
    with db_conn(db_path) as conn:
        conn.execute(
            """
            INSERT INTO history(input_path, style_intent, status, message, recipe_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (input_path, style_intent, status, message, json.dumps(recipe) if recipe is not None else None),
        )


def history_recent(db_path: Path, limit: int = 30) -> list[dict[str, Any]]:
    with db_conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, input_path, style_intent, status, message, recipe_json, created_at
            FROM history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]

