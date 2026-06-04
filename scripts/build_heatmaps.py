"""Buduje REALNE heatmapy SSIM (PNG per tile) z pipeline'u change detection.

Dla każdego regionu renderuje mapę zmiany (1 - SSIM) dla pary first-vs-last po
wszystkich tile'ach z=7, tą samą ścieżką co run_change_detection
(cloud_proxy_qa → compute_change_map → SSIM). NaN (chmury / brak danych) →
przezroczystość. Zmiana strukturalna = jasny/gorący piksel (colormap inferno).

Wyjście: data/processed/{region}/heatmap/{z}/{x}/{y}.png — indeksy w siatce
GIBS EPSG:4326 (jak region_tiles), NIE Web Mercator.

UWAGA (podłączenie do frontu): `useHeatmapLayer.ts` konsumuje produkcyjny URL przez
deck.gl TileLayer (siatka Web Mercator OSM). Te PNG mają indeksy 4326 → bezpośrednie
podstawienie pod TileLayer da złe pozycje (patrz MEMORY [2026-05-12] PMTiles overlay).
Render PNG to krok 1 (weryfikacja samych map); decyzja o ścieżce renderu we froncie
(manualny BitmapLayer 4326 jak usePMTilesLayer vs przeliczenie do Web Mercator) — osobno.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))  # dla importu run_change_detection

# Reużycie helperów i stałych z pipeline'u change detection (jedno źródło prawdy).
from run_change_detection import (  # noqa: E402
    CLOUD_QA_THRESHOLD,
    RGB_DIR,
    ZOOM,
    _load_rgb,
    cloud_proxy_qa,
    find_tile,
    get_dates,
)
from terralens.fetchers.regions import region_tiles
from terralens.processors.cloud_mask import InsufficientDataWarning
from terralens.processors.ssim import compute_change_map, export_heatmap

PROCESSED_DIR = Path("data/processed")
REGIONS = ["amazonia", "dubai", "arctic"]
# Zmiana = jasna/gorąca; brak zmiany (SSIM≈1 → change≈0) = ciemna.
HEATMAP_CMAP = "inferno"


def build_region_heatmaps(
    region: str,
    coords: list[tuple[int, int, int]],
    date_before: str,
    date_after: str,
) -> int:
    """Renderuje PNG mapy zmiany dla wszystkich tile'ów regionu (para first-vs-last).

    Zwraca liczbę wyrenderowanych tile'ów (z dostępną parą before/after).
    """
    out_dir = PROCESSED_DIR / region / "heatmap"
    rendered = 0
    for z, x, y in coords:
        p_before = find_tile(RGB_DIR, date_before, z, x, y)
        p_after = find_tile(RGB_DIR, date_after, z, x, y)
        if not (p_before and p_after):
            continue

        before = _load_rgb(p_before)
        after = _load_rgb(p_after)
        qa_before = cloud_proxy_qa(before)
        qa_after = cloud_proxy_qa(after)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InsufficientDataWarning)
            ssim_map = compute_change_map(
                after,
                before,
                target_qa=qa_after,
                reference_qa=qa_before,
                qa_threshold=CLOUD_QA_THRESHOLD,
            )

        # Mapa ZMIANY = 1 - SSIM (NaN zachowane); wysoka wartość = duża zmiana.
        change_map = (1.0 - ssim_map).astype(np.float32)

        tile_path = out_dir / str(z) / str(x) / f"{y}.png"
        tile_path.parent.mkdir(parents=True, exist_ok=True)
        export_heatmap(change_map, tile_path, colormap=HEATMAP_CMAP)
        rendered += 1

    return rendered


def main() -> None:
    dates = get_dates(RGB_DIR)
    if len(dates) < 2:
        print(f"Za mało dat HLS_RGB ({len(dates)}) — potrzebne min. 2. Przerywam.")
        return

    date_before, date_after = dates[0], dates[-1]
    for region in REGIONS:
        print(f"\n=== {region.upper()} ===")
        coords = sorted(set(region_tiles(region, ZOOM)))
        n = build_region_heatmaps(region, coords, date_before, date_after)
        out = PROCESSED_DIR / region / "heatmap"
        if n:
            print(f"  Heatmapy {date_before} → {date_after}: {n} tile'ów → {out}")
        else:
            print(f"  Brak wspólnych tile'ów {date_before}/{date_after} — pominięto")


if __name__ == "__main__":
    main()
