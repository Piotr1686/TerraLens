"""T5.2 — Testy generate_manifest, save_manifest, validate_manifest, helpers."""

from __future__ import annotations

import json
import sqlite3

import pytest
from terralens.export.manifest import (
    generate_manifest,
    get_changes,
    get_timeline,
    list_pmtiles,
    save_manifest,
    validate_manifest,
)

# ---------------------------------------------------------------------------
# Pomocniki
# ---------------------------------------------------------------------------


def _make_db(path, rows: list[tuple[str, str]]) -> None:
    """Tworzy cache.db z podanymi wierszami (layer, date)."""
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE tiles (
            id INTEGER PRIMARY KEY,
            layer TEXT, date TEXT, z INT, x INT, y INT,
            filepath TEXT, status TEXT, expires_at TEXT, created_at TEXT,
            UNIQUE(layer, date, z, x, y)
        )"""
    )
    for layer, date in rows:
        conn.execute(
            "INSERT INTO tiles (layer, date, z, x, y, filepath, status, expires_at, created_at)"
            " VALUES (?,?,0,0,0,'','ok','2099-01-01','2026-01-01')",
            (layer, date),
        )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# list_pmtiles
# ---------------------------------------------------------------------------


class TestListPmtiles:
    def test_returns_sorted_filenames(self, tmp_path):
        for name in ("amazonia_v20260420.pmtiles", "amazonia_v20260419.pmtiles"):
            (tmp_path / name).write_bytes(b"")

        result = list_pmtiles(tmp_path, "amazonia")

        assert result == ["amazonia_v20260419.pmtiles", "amazonia_v20260420.pmtiles"]

    def test_empty_dir_returns_empty(self, tmp_path):
        assert list_pmtiles(tmp_path, "amazonia") == []

    def test_filters_by_region(self, tmp_path):
        (tmp_path / "amazonia_v1.pmtiles").write_bytes(b"")
        (tmp_path / "dubai_v1.pmtiles").write_bytes(b"")

        result = list_pmtiles(tmp_path, "amazonia")

        assert result == ["amazonia_v1.pmtiles"]

    def test_non_pmtiles_ignored(self, tmp_path):
        (tmp_path / "amazonia_v1.pmtiles").write_bytes(b"")
        (tmp_path / "amazonia_manifest.json").write_text("{}")

        result = list_pmtiles(tmp_path, "amazonia")

        assert result == ["amazonia_v1.pmtiles"]


# ---------------------------------------------------------------------------
# get_timeline
# ---------------------------------------------------------------------------


class TestGetTimeline:
    def test_returns_dates_from_db(self, tmp_path):
        db = tmp_path / "cache.db"
        _make_db(db, [("HLS_RGB", "2015-01-01"), ("HLS_RGB", "2015-02-01")])

        result = get_timeline(db, layer="HLS_RGB")

        dates = [e["date"] for e in result]
        assert dates == ["2015-01-01", "2015-02-01"]

    def test_deduplicates_dates(self, tmp_path):
        db = tmp_path / "cache.db"
        conn = sqlite3.connect(db)
        conn.execute(
            """CREATE TABLE tiles (
                id INTEGER PRIMARY KEY, layer TEXT, date TEXT,
                z INT, x INT, y INT, filepath TEXT, status TEXT,
                expires_at TEXT, created_at TEXT,
                UNIQUE(layer, date, z, x, y)
            )"""
        )
        for x in range(3):
            conn.execute(
                "INSERT INTO tiles VALUES (?,?,?,0,?,0,'','ok','2099-01-01','2026-01-01')",
                (None, "HLS_RGB", "2015-01-01", x),
            )
        conn.commit()
        conn.close()

        result = get_timeline(db, layer="HLS_RGB")

        assert len(result) == 1
        assert result[0]["date"] == "2015-01-01"

    def test_nonexistent_db_returns_empty(self, tmp_path):
        assert get_timeline(tmp_path / "missing.db") == []

    def test_filters_by_layer(self, tmp_path):
        db = tmp_path / "cache.db"
        _make_db(db, [("HLS_RGB", "2015-01-01"), ("MODIS_NDVI", "2015-02-01")])

        result = get_timeline(db, layer="HLS_RGB")

        assert len(result) == 1
        assert result[0]["date"] == "2015-01-01"

    def test_cloud_cover_is_none(self, tmp_path):
        db = tmp_path / "cache.db"
        _make_db(db, [("HLS_RGB", "2015-01-01")])

        result = get_timeline(db)

        assert result[0]["cloud_cover"] is None

    def test_returns_sorted(self, tmp_path):
        db = tmp_path / "cache.db"
        _make_db(
            db, [("HLS_RGB", "2015-03-01"), ("HLS_RGB", "2015-01-01"), ("HLS_RGB", "2015-02-01")]
        )

        result = get_timeline(db)

        dates = [e["date"] for e in result]
        assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# get_changes
# ---------------------------------------------------------------------------


class TestGetChanges:
    def test_reads_changes_json(self, tmp_path):
        region_dir = tmp_path / "amazonia"
        region_dir.mkdir()
        data = {"deforestation_fraction": 0.12}
        (region_dir / "changes.json").write_text(json.dumps(data))

        result = get_changes(tmp_path, "amazonia")

        assert result == data

    def test_missing_file_returns_none(self, tmp_path):
        assert get_changes(tmp_path, "amazonia") is None

    def test_invalid_json_returns_none(self, tmp_path):
        region_dir = tmp_path / "amazonia"
        region_dir.mkdir()
        (region_dir / "changes.json").write_text("{ not valid json }")

        result = get_changes(tmp_path, "amazonia")

        assert result is None


# ---------------------------------------------------------------------------
# generate_manifest
# ---------------------------------------------------------------------------


class TestGenerateManifest:
    def test_structure_keys(self, tmp_path):
        result = generate_manifest(["amazonia"], tmp_path)

        assert "version" in result
        assert "generated" in result
        assert "regions" in result
        assert "amazonia" in result["regions"]

    def test_region_keys(self, tmp_path):
        result = generate_manifest(["amazonia"], tmp_path)

        region = result["regions"]["amazonia"]
        assert "latest" in region
        assert "all_versions" in region
        assert "timeline" in region
        assert "changes" in region
        assert "tour" in region

    def test_latest_is_none_when_no_pmtiles(self, tmp_path):
        result = generate_manifest(["amazonia"], tmp_path)

        assert result["regions"]["amazonia"]["latest"] is None

    def test_latest_points_to_newest_pmtiles(self, tmp_path):
        for name in ("amazonia_v20260419.pmtiles", "amazonia_v20260420.pmtiles"):
            (tmp_path / name).write_bytes(b"")

        result = generate_manifest(["amazonia"], tmp_path)

        assert result["regions"]["amazonia"]["latest"] == "amazonia_v20260420.pmtiles"

    def test_all_versions_preserved(self, tmp_path):
        names = ["amazonia_v20260419.pmtiles", "amazonia_v20260420.pmtiles"]
        for name in names:
            (tmp_path / name).write_bytes(b"")

        result = generate_manifest(["amazonia"], tmp_path)

        assert result["regions"]["amazonia"]["all_versions"] == sorted(names)

    def test_rerun_updates_latest(self, tmp_path):
        (tmp_path / "amazonia_v20260419.pmtiles").write_bytes(b"")
        first = generate_manifest(["amazonia"], tmp_path)

        (tmp_path / "amazonia_v20260420.pmtiles").write_bytes(b"")
        second = generate_manifest(["amazonia"], tmp_path)

        assert first["regions"]["amazonia"]["latest"] == "amazonia_v20260419.pmtiles"
        assert second["regions"]["amazonia"]["latest"] == "amazonia_v20260420.pmtiles"
        assert len(second["regions"]["amazonia"]["all_versions"]) == 2

    def test_multiple_regions(self, tmp_path):
        result = generate_manifest(["amazonia", "dubai", "arctic"], tmp_path)

        assert set(result["regions"].keys()) == {"amazonia", "dubai", "arctic"}

    def test_tour_paths_included(self, tmp_path):
        result = generate_manifest(["amazonia"], tmp_path)

        tour = result["regions"]["amazonia"]["tour"]
        assert tour is not None
        assert "lat" in tour and "lon" in tour

    def test_unknown_region_tour_is_none(self, tmp_path):
        result = generate_manifest(["unknown_region"], tmp_path)

        assert result["regions"]["unknown_region"]["tour"] is None

    def test_timeline_from_db(self, tmp_path):
        db = tmp_path / "cache.db"
        _make_db(db, [("HLS_RGB", "2015-01-01"), ("HLS_RGB", "2015-02-01")])

        result = generate_manifest(["amazonia"], tmp_path, db_path=db)

        assert len(result["regions"]["amazonia"]["timeline"]) == 2

    def test_timeline_empty_without_db(self, tmp_path):
        result = generate_manifest(["amazonia"], tmp_path, db_path=None)

        assert result["regions"]["amazonia"]["timeline"] == []

    def test_changes_from_processed_dir(self, tmp_path):
        processed = tmp_path / "processed"
        (processed / "amazonia").mkdir(parents=True)
        (processed / "amazonia" / "changes.json").write_text('{"frac": 0.1}')

        result = generate_manifest(["amazonia"], tmp_path, processed_dir=processed)

        assert result["regions"]["amazonia"]["changes"] == {"frac": 0.1}


# ---------------------------------------------------------------------------
# validate_manifest
# ---------------------------------------------------------------------------


class TestValidateManifest:
    def _valid(self):
        return {
            "version": "1.0",
            "generated": "2026-04-27T10:00:00+00:00",
            "regions": {
                "amazonia": {
                    "latest": "amazonia_v1.pmtiles",
                    "all_versions": ["amazonia_v1.pmtiles"],
                    "timeline": [],
                    "changes": None,
                    "tour": None,
                }
            },
        }

    def test_valid_manifest_passes(self):
        validate_manifest(self._valid())  # nie rzuca

    def test_missing_version_raises(self):
        m = self._valid()
        del m["version"]
        with pytest.raises(ValueError, match="version"):
            validate_manifest(m)

    def test_missing_generated_raises(self):
        m = self._valid()
        del m["generated"]
        with pytest.raises(ValueError, match="generated"):
            validate_manifest(m)

    def test_missing_regions_raises(self):
        m = self._valid()
        del m["regions"]
        with pytest.raises(ValueError, match="regions"):
            validate_manifest(m)


# ---------------------------------------------------------------------------
# save_manifest
# ---------------------------------------------------------------------------


class TestSaveManifest:
    def _valid_manifest(self):
        return {
            "version": "1.0",
            "generated": "2026-04-27T10:00:00+00:00",
            "regions": {},
        }

    def test_creates_file(self, tmp_path):
        out = tmp_path / "manifest.json"

        save_manifest(self._valid_manifest(), out)

        assert out.exists()

    def test_creates_parent_directory(self, tmp_path):
        out = tmp_path / "sub" / "manifest.json"

        save_manifest(self._valid_manifest(), out)

        assert out.exists()

    def test_output_is_valid_json(self, tmp_path):
        out = tmp_path / "manifest.json"

        save_manifest(self._valid_manifest(), out)

        data = json.loads(out.read_text())
        assert data["version"] == "1.0"

    def test_output_is_utf8(self, tmp_path):
        out = tmp_path / "manifest.json"
        m = self._valid_manifest()
        m["regions"]["amazonia"] = {
            "latest": None,
            "timeline": [],
            "tour": {"label": "Amazonia — Deforestação"},
        }

        save_manifest(m, out)

        content = out.read_text(encoding="utf-8")
        assert "Deforestação" in content

    def test_returns_output_path(self, tmp_path):
        out = tmp_path / "manifest.json"

        result = save_manifest(self._valid_manifest(), out)

        assert result is out

    def test_invalid_manifest_raises(self, tmp_path):
        out = tmp_path / "manifest.json"
        with pytest.raises(ValueError):
            save_manifest({"bad": "data"}, out)
