"""Uruchamia change detection na dostępnych danych NDVI + SSIM.

Generuje data/processed/{region}/changes.json per region.
Porównanie tile-by-tile dla (z,x,y) które istnieją w obu datach.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from terralens.fetchers.regions import region_tiles
from terralens.processors.ndvi import compute_ndvi_diff
from terralens.processors.ssim import compute_change_map

NDVI_DIR = Path("data/tiles/MODIS_NDVI")
RGB_DIR = Path("data/tiles/HLS_RGB")
PROCESSED_DIR = Path("data/processed")
REGIONS = ["amazonia", "dubai", "arctic"]
ZOOM = 7
NDVI_ZOOM = 6


def find_tile(tile_dir: Path, date: str, z: int, x: int, y: int) -> Path | None:
    for ext in ("png", "jpg", "jpeg", "webp"):
        p = tile_dir / date / str(z) / str(x) / f"{y}.{ext}"
        if p.exists():
            return p
    return None


def get_dates(tile_dir: Path) -> list[str]:
    """Zwraca daty katalogów które faktycznie zawierają pliki."""
    if not tile_dir.exists():
        return []
    return sorted(d.name for d in tile_dir.iterdir() if d.is_dir() and any(d.rglob("*.*")))


def run_ndvi_detection(region: str, coords: set[tuple[int, int, int]]) -> dict | None:
    dates = get_dates(NDVI_DIR)
    if len(dates) < 2:
        print(f"  [NDVI] Za mało dat ({len(dates)}), pomijam")
        return None

    first_date, last_date = dates[0], dates[-1]

    # NDVI tiles są na z=NDVI_ZOOM, a coords mogą być na innym z
    ndvi_coords = set(region_tiles(region, NDVI_ZOOM))
    all_before, all_after = [], []
    matched = 0
    for z, x, y in sorted(ndvi_coords):
        p_before = find_tile(NDVI_DIR, first_date, z, x, y)
        p_after = find_tile(NDVI_DIR, last_date, z, x, y)
        if p_before and p_after:
            arr_b = np.array(Image.open(p_before).convert("L"), dtype=np.uint8)
            arr_a = np.array(Image.open(p_after).convert("L"), dtype=np.uint8)
            all_before.append(arr_b.flatten())
            all_after.append(arr_a.flatten())
            matched += 1

    if matched == 0:
        print(f"  [NDVI] Brak wspólnych tile'ów dla regionu {region} ({first_date} vs {last_date})")
        return None

    print(f"  [NDVI] {first_date} vs {last_date} — {matched} tile'ów")
    before_flat = np.concatenate(all_before).astype(np.uint8)
    after_flat = np.concatenate(all_after).astype(np.uint8)
    _, stats = compute_ndvi_diff(before_flat, after_flat)
    stats["date_before"] = first_date
    stats["date_after"] = last_date
    stats["tiles_compared"] = matched
    stats["source"] = "MODIS_NDVI"
    return stats


def run_ssim_detection(region: str, coords: set[tuple[int, int, int]]) -> dict | None:
    dates = get_dates(RGB_DIR)
    if len(dates) < 2:
        print(f"  [SSIM] Za mało dat ({len(dates)}), pomijam")
        return None

    first_date, last_date = dates[0], dates[-1]

    ssim_values: list[float] = []
    matched = 0
    for z, x, y in sorted(coords):
        p_before = find_tile(RGB_DIR, first_date, z, x, y)
        p_after = find_tile(RGB_DIR, last_date, z, x, y)
        if p_before and p_after:
            b = np.array(Image.open(p_before).convert("RGB"), dtype=np.float32)
            a = np.array(Image.open(p_after).convert("RGB"), dtype=np.float32)
            ssim_map = compute_change_map(a, b)
            valid = ssim_map[~np.isnan(ssim_map)]
            if len(valid) > 0:
                ssim_values.extend(valid.tolist())
            matched += 1

    if matched == 0:
        print(f"  [SSIM] Brak wspólnych tile'ów dla regionu {region}")
        return None

    print(f"  [SSIM] {first_date} vs {last_date} — {matched} tile'ów")

    arr = np.array(ssim_values, dtype=np.float32)
    change_threshold = 0.5
    n_changed = int((arr < change_threshold).sum())

    return {
        "ssim_mean": float(np.mean(arr)),
        "ssim_std": float(np.std(arr)),
        "ssim_min": float(np.min(arr)),
        "change_threshold": change_threshold,
        "pixels_total": int(len(arr)),
        "pixels_changed": n_changed,
        "change_fraction": n_changed / len(arr) if len(arr) > 0 else 0.0,
        "date_before": first_date,
        "date_after": last_date,
        "tiles_compared": matched,
        "source": "HLS_RGB_SSIM",
    }


def main() -> None:
    for region in REGIONS:
        print(f"\n=== {region.upper()} ===")
        coords = set(region_tiles(region, ZOOM))
        print(f"  Tile coords (z={ZOOM}): {len(coords)} tile'ów")

        ndvi_stats = run_ndvi_detection(region, coords)
        ssim_stats = run_ssim_detection(region, coords)

        changes: dict = {}
        if ndvi_stats:
            changes["ndvi"] = ndvi_stats
            print(f"  [NDVI] deforestation_fraction={ndvi_stats['deforestation_fraction']:.4f}")
        if ssim_stats:
            changes["ssim"] = ssim_stats
            print(
                f"  [SSIM] change_fraction={ssim_stats['change_fraction']:.4f}, mean={ssim_stats['ssim_mean']:.4f}"
            )

        if changes:
            out_path = PROCESSED_DIR / region / "changes.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(changes, indent=2), encoding="utf-8")
            print(f"  Zapisano: {out_path}")
        else:
            print(f"  Brak danych dla {region}")


if __name__ == "__main__":
    main()
