"""T1.4 — Testy SQLite cache (insert + query + expiry check)."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from terralens.db.queries import (
    cleanup_expired,
    get_tile_status,
    init_db,
    insert_tile,
    is_expired,
)


@pytest.fixture
def db(tmp_path: Path):
    return init_db(tmp_path / "cache.db")


def test_init_creates_db(tmp_path: Path) -> None:
    conn = init_db(tmp_path / "sub" / "cache.db")
    assert (tmp_path / "sub" / "cache.db").exists()
    conn.close()


def test_insert_and_query(db) -> None:
    insert_tile(db, "rgb", "2020-01-01", 6, 10, 20, "/data/tile.tif")
    row = get_tile_status(db, "rgb", "2020-01-01", 6, 10, 20)
    assert row is not None
    assert row["filepath"] == "/data/tile.tif"
    assert row["status"] == "ok"


def test_missing_tile_returns_none(db) -> None:
    assert get_tile_status(db, "rgb", "2099-01-01", 0, 0, 0) is None


def test_upsert_updates_filepath(db) -> None:
    insert_tile(db, "ndvi", "2021-06-01", 5, 1, 2, "/old/path.tif")
    insert_tile(db, "ndvi", "2021-06-01", 5, 1, 2, "/new/path.tif")
    row = get_tile_status(db, "ndvi", "2021-06-01", 5, 1, 2)
    assert row["filepath"] == "/new/path.tif"


def test_is_not_expired_fresh_tile(db) -> None:
    insert_tile(db, "rgb", "2022-01-01", 6, 0, 0, "/f.tif", ttl_days=30)
    row = get_tile_status(db, "rgb", "2022-01-01", 6, 0, 0)
    assert not is_expired(row)


def test_is_expired_old_tile(db) -> None:
    insert_tile(db, "rgb", "2000-01-01", 6, 0, 0, "/old.tif", ttl_days=30)
    row = get_tile_status(db, "rgb", "2000-01-01", 6, 0, 0)
    # Ręcznie ustaw expires_at w przeszłości
    db.execute(
        "UPDATE tiles SET expires_at=? WHERE layer='rgb' AND date='2000-01-01'",
        [(datetime.now(timezone.utc) - timedelta(days=1)).isoformat()],
    )
    db.commit()
    row = get_tile_status(db, "rgb", "2000-01-01", 6, 0, 0)
    assert is_expired(row)


def test_cleanup_expired(db) -> None:
    insert_tile(db, "rgb", "1990-01-01", 6, 0, 0, "/a.tif", ttl_days=30)
    db.execute(
        "UPDATE tiles SET expires_at=? WHERE layer='rgb' AND date='1990-01-01'",
        [(datetime.now(timezone.utc) - timedelta(days=1)).isoformat()],
    )
    db.commit()
    insert_tile(db, "rgb", "2090-01-01", 6, 1, 1, "/b.tif", ttl_days=30)

    deleted = cleanup_expired(db)
    assert deleted == 1
    assert get_tile_status(db, "rgb", "1990-01-01", 6, 0, 0) is None
    assert get_tile_status(db, "rgb", "2090-01-01", 6, 1, 1) is not None
