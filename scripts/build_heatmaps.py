"""Buduje REALNE heatmapy zmian (PNG per tile) z pipeline'u change detection.

Dwie metryki, para first-vs-last, indeksy w siatce GIBS EPSG:4326 (jak region_tiles):
  - SSIM (HLS_RGB, z=7): mapa zmiany (1 - SSIM) tą samą ścieżką co run_change_detection
    (cloud_proxy_qa → compute_change_map). Zmiana strukturalna = jasny piksel (inferno).
    Wyjście: data/processed/{region}/heatmap/{z}/{x}/{y}.png
  - NDVI (MODIS_NDVI, z=6): dywergentna mapa diff (after-before) — czerwień=utrata
    roślinności, zieleń=przyrost (RdYlGn). Wyjście: data/processed/{region}/ndvi_heatmap/...
NaN (chmury / brak danych / zmiana < progu) → przezroczystość.

Podłączenie do frontu: `useHeatmapLayer.ts` renderuje te PNG manualnym multi-BitmapLayer
w natywnych bounds 4326 (jak usePMTilesLayer), NIE deck.gl TileLayer (Web Mercator) —
patrz MEMORY [2026-05-12] PMTiles overlay i [2026-06-04] realne heatmapy SSIM.
Deploy: `terralens deploy-heatmaps` → HF {region}_ssim_heatmap / {region}_ndvi_heatmap.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))  # dla importu run_change_detection

# Reużycie helperów i stałych z pipeline'u change detection (jedno źródło prawdy).
from PIL import Image  # noqa: E402
from run_change_detection import (  # noqa: E402
    CLOUD_QA_THRESHOLD,
    NDVI_DIR,
    NDVI_ZOOM,
    RGB_DIR,
    ZOOM,
    _load_rgb,
    cloud_proxy_qa,
    find_tile,
    get_dates,
)
from terralens.fetchers.regions import region_tiles
from terralens.processors.cloud_mask import InsufficientDataWarning
from terralens.processors.ndvi import compute_ndvi_diff
from terralens.processors.ssim import compute_change_map, export_heatmap

PROCESSED_DIR = Path("data/processed")
REGIONS = ["amazonia", "dubai", "arctic"]
# Zmiana = jasna/gorąca; brak zmiany (SSIM≈1 → change≈0) = ciemna.
HEATMAP_CMAP = "inferno"

# --- NDVI (dywergentna): czerwień=utrata roślinności, zieleń=przyrost ---
# diff = after - before (ujemne = utrata). RdYlGn: niska wartość=czerwień, wysoka=zieleń,
# więc z vmin=-VRANGE, vmax=+VRANGE utrata→czerwień, przyrost→zieleń (bez odwracania).
NDVI_CMAP = "RdYlGn"
# Zmiany |diff| poniżej progu → przezroczyste (filtr szumu proxy + czysty glob).
NDVI_MIN_CHANGE = 0.12
# Zakres normalizacji koloru: |diff| = NDVI_VRANGE → pełne nasycenie.
NDVI_VRANGE = 0.4


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


def _load_ndvi(path: Path) -> np.ndarray:
    """Wczytuje tile NDVI jako 2D uint8 (grayscale proxy z palety GIBS)."""
    return np.array(Image.open(path).convert("L"), dtype=np.uint8)


def build_region_ndvi_heatmaps(
    region: str,
    coords: list[tuple[int, int, int]],
    date_before: str,
    date_after: str,
) -> int:
    """Renderuje PNG dywergentnej mapy diff NDVI (after-before) per tile regionu.

    Czerwień = utrata roślinności, zieleń = przyrost; |diff| < progu → przezroczyste.
    Zwraca liczbę wyrenderowanych tile'ów.
    """
    out_dir = PROCESSED_DIR / region / "ndvi_heatmap"
    rendered = 0
    for z, x, y in coords:
        p_before = find_tile(NDVI_DIR, date_before, z, x, y)
        p_after = find_tile(NDVI_DIR, date_after, z, x, y)
        if not (p_before and p_after):
            continue

        before = _load_ndvi(p_before)
        after = _load_ndvi(p_after)
        diff_map, _ = compute_ndvi_diff(before, after)

        # Słabe zmiany (szum proxy) → NaN → przezroczyste; reszta dywergentnie.
        diff_map = np.where(np.abs(diff_map) < NDVI_MIN_CHANGE, np.nan, diff_map)
        if np.all(np.isnan(diff_map)):
            continue  # tile bez istotnej zmiany — nie zapisujemy pustego PNG

        tile_path = out_dir / str(z) / str(x) / f"{y}.png"
        tile_path.parent.mkdir(parents=True, exist_ok=True)
        export_heatmap(diff_map, tile_path, colormap=NDVI_CMAP, vmin=-NDVI_VRANGE, vmax=NDVI_VRANGE)
        rendered += 1

    return rendered


def main() -> None:
    # --- SSIM (HLS_RGB, z=7) ---
    rgb_dates = get_dates(RGB_DIR)
    if len(rgb_dates) >= 2:
        ssim_before, ssim_after = rgb_dates[0], rgb_dates[-1]
        for region in REGIONS:
            print(f"\n=== {region.upper()} · SSIM ===")
            coords = sorted(set(region_tiles(region, ZOOM)))
            n = build_region_heatmaps(region, coords, ssim_before, ssim_after)
            out = PROCESSED_DIR / region / "heatmap"
            if n:
                print(f"  Heatmapy SSIM {ssim_before} → {ssim_after}: {n} tile'ów → {out}")
            else:
                print(f"  Brak wspólnych tile'ów {ssim_before}/{ssim_after} — pominięto")
    else:
        print(f"Za mało dat HLS_RGB ({len(rgb_dates)}) — pomijam SSIM.")

    # --- NDVI (MODIS_NDVI, z=6) ---
    ndvi_dates = get_dates(NDVI_DIR)
    if len(ndvi_dates) >= 2:
        ndvi_before, ndvi_after = ndvi_dates[0], ndvi_dates[-1]
        for region in REGIONS:
            print(f"\n=== {region.upper()} · NDVI ===")
            coords = sorted(set(region_tiles(region, NDVI_ZOOM)))
            n = build_region_ndvi_heatmaps(region, coords, ndvi_before, ndvi_after)
            out = PROCESSED_DIR / region / "ndvi_heatmap"
            if n:
                print(f"  Heatmapy NDVI {ndvi_before} → {ndvi_after}: {n} tile'ów → {out}")
            else:
                print(f"  Brak istotnej zmiany {ndvi_before}/{ndvi_after} — pominięto")
    else:
        print(f"Za mało dat MODIS_NDVI ({len(ndvi_dates)}) — pomijam NDVI.")


if __name__ == "__main__":
    main()
