"""Manifest JSON z wersjonowaniem PMTiles dla TerraLens frontendu."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# Trasy kamery dla Guided Tour (Amazonia → Dubai → Arctic, 10-second hook)
TOUR_PATHS: dict[str, dict] = {
    "amazonia": {
        "lat": -5.0,
        "lon": -60.0,
        "altitude": 2_000_000,
        "duration_s": 3.5,
        "label": "Amazonia — Deforestation 2015–2024",
    },
    "dubai": {
        "lat": 25.2,
        "lon": 55.3,
        "altitude": 500_000,
        "duration_s": 3.0,
        "label": "Dubai — Urban Expansion",
    },
    "arctic": {
        "lat": 79.0,
        "lon": 15.0,
        "altitude": 3_000_000,
        "duration_s": 3.5,
        "label": "Svalbard — Sea Ice Retreat",
    },
}

MANIFEST_SCHEMA: dict = {
    "type": "object",
    "required": ["version", "generated", "regions"],
    "properties": {
        "version": {"type": "string"},
        "generated": {"type": "string"},
        "regions": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["latest", "timeline"],
                "properties": {
                    "latest": {"type": ["string", "null"]},
                    "all_versions": {"type": "array"},
                    "timeline": {"type": "array"},
                    "changes": {"type": ["object", "null"]},
                    "tour": {"type": ["object", "null"]},
                },
            },
        },
    },
}


def list_pmtiles(export_dir: Path, region: str) -> list[str]:
    """Zwraca nazwy plików PMTiles dla regionu, posortowane chronologicznie."""
    return sorted(p.name for p in export_dir.glob(f"{region}_v*.pmtiles"))


def get_timeline(db_path: Path, layer: str = "HLS_RGB") -> list[dict]:
    """Odczytuje unikalne daty z cache.db dla danej warstwy.

    Returns:
        Lista słowników ``{"date": "YYYY-MM-DD", "cloud_cover": None}``.
        Zwraca [] jeśli db_path nie istnieje lub wystąpił błąd SQL.
    """
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT DISTINCT date FROM tiles WHERE layer=? ORDER BY date",
            (layer,),
        ).fetchall()
        conn.close()
    except sqlite3.Error:
        return []
    return [{"date": row[0], "cloud_cover": None} for row in rows]


def get_changes(processed_dir: Path, region: str) -> dict | None:
    """Wczytuje data/processed/{region}/changes.json. Zwraca None jeśli brak."""
    path = processed_dir / region / "changes.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def generate_manifest(
    regions: list[str],
    export_dir: Path,
    db_path: Path | None = None,
    processed_dir: Path | None = None,
) -> dict:
    """Buduje słownik manifestu TerraLens.

    Args:
        regions:       Lista nazw regionów (np. ["amazonia", "dubai", "arctic"]).
        export_dir:    Katalog z plikami .pmtiles (skanowany per region).
        db_path:       Ścieżka do cache.db (do budowy timeline). None → timeline=[].
        processed_dir: Katalog data/processed/ (do wczytania changes.json). None → changes=None.

    Returns:
        Słownik gotowy do serializacji jako manifest.json.
    """
    manifest: dict = {
        "version": "1.0",
        "generated": datetime.now(tz=timezone.utc).isoformat(),
        "regions": {},
    }
    for region in regions:
        versions = list_pmtiles(export_dir, region)
        manifest["regions"][region] = {
            "latest": versions[-1] if versions else None,
            "all_versions": versions,
            "timeline": get_timeline(db_path, layer="HLS_RGB") if db_path else [],
            "changes": get_changes(processed_dir, region) if processed_dir else None,
            "tour": TOUR_PATHS.get(region),
        }
    return manifest


def validate_manifest(manifest: dict) -> None:
    """Waliduje manifest względem MANIFEST_SCHEMA.

    Raises:
        ValueError: Gdy manifest nie spełnia schematu.
    """
    import jsonschema

    try:
        jsonschema.validate(manifest, MANIFEST_SCHEMA)
    except jsonschema.ValidationError as exc:
        raise ValueError(f"Niepoprawny manifest: {exc.message}") from exc


def save_manifest(manifest: dict, output_path: Path) -> Path:
    """Waliduje i zapisuje manifest do JSON UTF-8. Tworzy katalog jeśli brak.

    Returns: output_path po zapisaniu.
    """
    validate_manifest(manifest)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path
