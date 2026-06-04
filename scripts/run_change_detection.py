"""Uruchamia change detection na dostępnych danych NDVI + SSIM.

Generuje data/processed/{region}/changes.json per region z:
  - summary  — agregat first-vs-last (całkowita zmiana w okresie),
  - series   — szereg czasowy (kolejne pary dat / kolejne daty), fundament wykresu.

SSIM liczone na KOLEJNYCH parach dat (date[i] vs date[i+1]), nie tylko first-vs-last,
z pełnym preprocessingiem: cloud_mask (proxy z RGB) → histogram_match → SSIM.
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from terralens.fetchers.regions import region_tiles
from terralens.processors.cloud_mask import InsufficientDataWarning
from terralens.processors.ndvi import compute_ndvi_diff
from terralens.processors.ssim import compute_change_map

NDVI_DIR = Path("data/tiles/MODIS_NDVI")
RGB_DIR = Path("data/tiles/HLS_RGB")
PROCESSED_DIR = Path("data/processed")
REGIONS = ["amazonia", "dubai", "arctic"]
ZOOM = 7
NDVI_ZOOM = 6

# Próg SSIM poniżej którego piksel uznajemy za "zmieniony"
SSIM_CHANGE_THRESHOLD = 0.5
# Próg QA dla cloud_mask. Proxy chmur (bright + low-sat) daje ~0.85 dla grubej chmury,
# ~0.45-0.55 dla jasnego piasku/pustyni → 0.6 maskuje chmury, oszczędza pustynię.
CLOUD_QA_THRESHOLD = 0.6


def find_tile(tile_dir: Path, date: str, z: int, x: int, y: int) -> Path | None:
    for ext in ("png", "jpg", "jpeg", "webp"):
        p = tile_dir / date / str(z) / str(x) / f"{y}.{ext}"
        if p.exists():
            return p
    return None


def get_dates(tile_dir: Path) -> list[str]:
    """Zwraca posortowane daty katalogów które faktycznie zawierają pliki."""
    if not tile_dir.exists():
        return []
    return sorted(d.name for d in tile_dir.iterdir() if d.is_dir() and any(d.rglob("*.*")))


def cloud_proxy_qa(rgb: np.ndarray) -> np.ndarray:
    """Wylicza pseudo-QA band z RGB jako proxy zachmurzenia (brak prawdziwego QA w GIBS HLS).

    Grube chmury są jednocześnie JASNE i NISKO NASYCONE (biało-szare). Pustynia/piasek
    jest jasny, ale nasycony (tan/pomarańcz) → niski wynik proxy, nie zostanie zamaskowany.

    Args:
        rgb: ndarray (H, W, 3) float32 w zakresie [0, 255].

    Returns:
        ndarray (H, W) float32 w [0, 1] — wyżej = większe prawdopodobieństwo chmury.

    Uwaga: to heurystyka, nie prawdziwy QA band. Docelowo (follow-up) — fetch warstwy
    cloud mask z GIBS. Tu redukuje najbardziej rażące false-positives z grubych chmur.
    """
    rgb01 = np.clip(rgb / 255.0, 0.0, 1.0)
    mx = rgb01.max(axis=-1)
    mn = rgb01.min(axis=-1)
    lum = rgb01.mean(axis=-1)
    sat = np.where(mx > 1e-6, (mx - mn) / mx, 0.0)
    return (lum * (1.0 - sat)).astype(np.float32)


def _load_rgb(path: Path) -> np.ndarray:
    return np.array(Image.open(path).convert("RGB"), dtype=np.float32)


def _ssim_pair(
    region_coords: list[tuple[int, int, int]],
    date_before: str,
    date_after: str,
) -> dict | None:
    """Liczy SSIM dla jednej pary dat po wszystkich wspólnych tile'ach regionu.

    Pipeline per tile: cloud_proxy_qa → compute_change_map (cloud_mask → histogram_match → SSIM).
    Zwraca agregat statystyk dla pary lub None gdy brak wspólnych tile'ów / brak ważnych pikseli.
    """
    ssim_values: list[float] = []
    matched = 0
    for z, x, y in region_coords:
        p_before = find_tile(RGB_DIR, date_before, z, x, y)
        p_after = find_tile(RGB_DIR, date_after, z, x, y)
        if not (p_before and p_after):
            continue
        before = _load_rgb(p_before)
        after = _load_rgb(p_after)
        qa_before = cloud_proxy_qa(before)
        qa_after = cloud_proxy_qa(after)
        # compute_change_map: cloud_mask(QA) → histogram_match → gaussian blur → SSIM
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InsufficientDataWarning)
            ssim_map = compute_change_map(
                after,
                before,
                target_qa=qa_after,
                reference_qa=qa_before,
                qa_threshold=CLOUD_QA_THRESHOLD,
            )
        valid = ssim_map[~np.isnan(ssim_map)]
        if valid.size > 0:
            ssim_values.extend(valid.tolist())
            matched += 1

    if matched == 0 or not ssim_values:
        return None

    arr = np.asarray(ssim_values, dtype=np.float32)
    n_changed = int((arr < SSIM_CHANGE_THRESHOLD).sum())
    return {
        "date_before": date_before,
        "date_after": date_after,
        "ssim_mean": float(arr.mean()),
        "ssim_std": float(arr.std()),
        "ssim_min": float(arr.min()),
        "pixels_total": int(arr.size),
        "pixels_changed": n_changed,
        "change_fraction": n_changed / arr.size,
        "tiles_compared": matched,
    }


def run_ssim_detection(region: str, coords: list[tuple[int, int, int]]) -> dict | None:
    """SSIM change detection — kolejne pary dat (szereg czasowy) + summary first-vs-last."""
    dates = get_dates(RGB_DIR)
    if len(dates) < 2:
        print(f"  [SSIM] Za mało dat ({len(dates)}), pomijam")
        return None

    # Szereg czasowy: kolejne pary dat (zmiana okres-do-okresu)
    series: list[dict] = []
    for d_before, d_after in zip(dates, dates[1:], strict=False):
        pair = _ssim_pair(coords, d_before, d_after)
        if pair:
            series.append(pair)
            print(
                f"  [SSIM] {d_before} → {d_after}: "
                f"change={pair['change_fraction']:.3f} mean={pair['ssim_mean']:.3f} "
                f"({pair['tiles_compared']} tiles)"
            )

    if not series:
        print(f"  [SSIM] Brak wspólnych tile'ów dla regionu {region}")
        return None

    # Summary: całkowita zmiana first-vs-last (nie suma kroków).
    # Przy dokładnie 2 datach para first-vs-last == series[0] — reużyj zamiast liczyć drugi raz.
    if len(dates) == 2:
        overall = series[0]
    else:
        overall = _ssim_pair(coords, dates[0], dates[-1])
        if overall is None:
            # fallback: użyj statystyk z szeregu jeśli skrajne daty nie mają wspólnych tile'ów
            overall = series[-1]

    return {
        "source": "HLS_RGB_SSIM",
        "change_threshold": SSIM_CHANGE_THRESHOLD,
        "cloud_qa_threshold": CLOUD_QA_THRESHOLD,
        "date_before": overall["date_before"],
        "date_after": overall["date_after"],
        "ssim_mean": overall["ssim_mean"],
        "ssim_std": overall["ssim_std"],
        "ssim_min": overall["ssim_min"],
        "pixels_total": overall["pixels_total"],
        "pixels_changed": overall["pixels_changed"],
        "change_fraction": overall["change_fraction"],
        "tiles_compared": overall["tiles_compared"],
        "n_periods": len(series),
        "series": series,
    }


def _ndvi_region_mean(region_coords: list[tuple[int, int, int]], date: str) -> float | None:
    """Średnie NDVI [0,1] po wszystkich tile'ach regionu dla danej daty."""
    vals: list[float] = []
    for z, x, y in region_coords:
        p = find_tile(NDVI_DIR, date, z, x, y)
        if p:
            arr = np.array(Image.open(p).convert("L"), dtype=np.float32) / 255.0
            vals.append(float(arr.mean()))
    if not vals:
        return None
    return float(np.mean(vals))


def run_ndvi_detection(region: str) -> dict | None:
    """NDVI diff — summary first-vs-last + szereg czasowy średniej NDVI per data."""
    dates = get_dates(NDVI_DIR)
    if len(dates) < 2:
        print(f"  [NDVI] Za mało dat ({len(dates)}), pomijam")
        return None

    ndvi_coords = region_tiles(region, NDVI_ZOOM)

    # Szereg czasowy: średnia NDVI dla każdej dostępnej daty
    series: list[dict] = []
    for date in dates:
        m = _ndvi_region_mean(ndvi_coords, date)
        if m is not None:
            series.append({"date": date, "ndvi_mean": m})

    if not series:
        print(f"  [NDVI] Brak tile'ów dla regionu {region}")
        return None

    first_date, last_date = series[0]["date"], series[-1]["date"]

    # Summary first-vs-last: diff per-piksel na skonkatenowanych tile'ach
    all_before, all_after = [], []
    matched = 0
    for z, x, y in ndvi_coords:
        p_before = find_tile(NDVI_DIR, first_date, z, x, y)
        p_after = find_tile(NDVI_DIR, last_date, z, x, y)
        if p_before and p_after:
            arr_b = np.array(Image.open(p_before).convert("L"), dtype=np.uint8)
            arr_a = np.array(Image.open(p_after).convert("L"), dtype=np.uint8)
            all_before.append(arr_b.flatten())
            all_after.append(arr_a.flatten())
            matched += 1

    if matched == 0:
        print(f"  [NDVI] Brak wspólnych tile'ów {first_date} vs {last_date}")
        return None

    before_flat = np.concatenate(all_before).astype(np.uint8)
    after_flat = np.concatenate(all_after).astype(np.uint8)
    _, stats = compute_ndvi_diff(before_flat, after_flat)
    print(
        f"  [NDVI] {first_date} → {last_date}: "
        f"defor={stats['deforestation_fraction']:.3f} "
        f"Δmean={stats['ndvi_mean_diff']:+.3f} ({matched} tiles, {len(series)} dat)"
    )

    stats["date_before"] = first_date
    stats["date_after"] = last_date
    stats["tiles_compared"] = matched
    stats["source"] = "MODIS_NDVI"
    stats["n_dates"] = len(series)
    stats["series"] = series
    return stats


def main() -> None:
    for region in REGIONS:
        print(f"\n=== {region.upper()} ===")
        coords = sorted(set(region_tiles(region, ZOOM)))
        print(f"  Tile coords (z={ZOOM}): {len(coords)} tile'ów")

        ndvi_stats = run_ndvi_detection(region)
        ssim_stats = run_ssim_detection(region, coords)

        changes: dict = {}
        if ndvi_stats:
            changes["ndvi"] = ndvi_stats
        if ssim_stats:
            changes["ssim"] = ssim_stats

        if changes:
            out_path = PROCESSED_DIR / region / "changes.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(changes, indent=2), encoding="utf-8")
            print(f"  Zapisano: {out_path}")
        else:
            print(f"  Brak danych dla {region}")


if __name__ == "__main__":
    main()
