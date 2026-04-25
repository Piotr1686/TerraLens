"""SQLite cache dla pobranych tile'ów — bez ORM, czyste SQL."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS tiles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    layer       TEXT    NOT NULL,
    date        TEXT    NOT NULL,
    z           INTEGER NOT NULL,
    x           INTEGER NOT NULL,
    y           INTEGER NOT NULL,
    filepath    TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'ok',
    expires_at  TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    UNIQUE (layer, date, z, x, y)
);
"""


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expires(ttl_days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=ttl_days)).isoformat()


def init_db(db_path: Path, ttl_days: int = 30) -> sqlite3.Connection:
    """Tworzy (lub otwiera) cache.db i inicjalizuje schemat."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def insert_tile(
    conn: sqlite3.Connection,
    layer: str,
    date: str,
    z: int,
    x: int,
    y: int,
    filepath: str,
    ttl_days: int = 30,
    status: str = "ok",
) -> None:
    conn.execute(
        """
        INSERT INTO tiles (layer, date, z, x, y, filepath, status, expires_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (layer, date, z, x, y) DO UPDATE SET
            filepath   = excluded.filepath,
            status     = excluded.status,
            expires_at = excluded.expires_at,
            created_at = excluded.created_at
        """,
        (layer, date, z, x, y, filepath, status, _expires(ttl_days), _now_utc()),
    )
    conn.commit()


def get_tile_status(
    conn: sqlite3.Connection,
    layer: str,
    date: str,
    z: int,
    x: int,
    y: int,
) -> dict | None:
    """Zwraca wiersz tile'a lub None jeśli nie istnieje."""
    row = conn.execute(
        "SELECT filepath, status, expires_at FROM tiles WHERE layer=? AND date=? AND z=? AND x=? AND y=?",
        (layer, date, z, x, y),
    ).fetchone()
    if row is None:
        return None
    return {"filepath": row[0], "status": row[1], "expires_at": row[2]}


def is_expired(tile_row: dict) -> bool:
    """Zwraca True jeśli tile wygasł (expires_at < teraz)."""
    expires = datetime.fromisoformat(tile_row["expires_at"])
    return datetime.now(timezone.utc) > expires


def cleanup_expired(conn: sqlite3.Connection) -> int:
    """Usuwa wygasłe wpisy. Zwraca liczbę usuniętych wierszy."""
    cur = conn.execute(
        "DELETE FROM tiles WHERE expires_at < ?",
        (_now_utc(),),
    )
    conn.commit()
    return cur.rowcount
