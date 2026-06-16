"""Ranking dat HLS_RGB wg zachmurzenia (proxy QA) dla regionu — wybór najczystszego snapshotu SR.

Reużywa istniejących funkcji CV (bez nowej logiki):
- get_dates / _load_rgb / cloud_proxy_qa z scripts/run_change_detection.py
- cloud_fraction z terralens.processors.cloud_mask
- region_tiles z terralens.fetchers.regions

Użycie:
    python scripts/scan_cloud_cover.py --region amazonia --zoom 7
"""

import argparse
import sys
from pathlib import Path

# Pozwól na import zarówno z scripts/ jak i z roota
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_change_detection import _load_rgb, cloud_proxy_qa, get_dates  # noqa: E402
from terralens.config import get_config  # noqa: E402
from terralens.export.pmtiles import scan_tiles  # noqa: E402
from terralens.fetchers.regions import region_tiles  # noqa: E402
from terralens.processors.cloud_mask import cloud_fraction  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="amazonia")
    ap.add_argument("--layer", default="HLS_RGB")
    ap.add_argument("--zoom", type=int, default=7)
    ap.add_argument("--threshold", type=float, default=0.2)
    args = ap.parse_args()

    cfg = get_config()
    layer_dir = cfg.data_dir / "tiles" / args.layer
    # region_tiles zwraca (z, x, y); filtrujemy kafle po (z, x, y) dla zadanego zoomu
    region_set = {(args.zoom, x, y) for _, x, y in region_tiles(args.region, args.zoom)}

    dates = get_dates(layer_dir)
    if not dates:
        print(f"Brak dat w {layer_dir}")
        return

    print(
        f"Region: {args.region} | zoom: {args.zoom} | kafli w regionie: {len(region_set)} | dat: {len(dates)}"
    )
    print(f"{'data':<14}{'cloud_frac':>12}{'kafli':>8}")
    print("-" * 34)

    ranking: list[tuple[float, str, int]] = []
    for d in dates:
        date_dir = layer_dir / d
        tiles = [(z, x, y, p) for z, x, y, p in scan_tiles(date_dir) if (z, x, y) in region_set]
        if not tiles:
            continue
        fracs = []
        for _, _, _, p in tiles:
            rgb = _load_rgb(p)
            qa = cloud_proxy_qa(rgb)
            fracs.append(cloud_fraction(qa, args.threshold))
        mean_frac = sum(fracs) / len(fracs)
        ranking.append((mean_frac, d, len(tiles)))

    ranking.sort()
    for frac, d, n in ranking:
        print(f"{d:<14}{frac:>12.3f}{n:>8}")

    print("-" * 34)
    if ranking:
        best_frac, best_date, _ = ranking[0]
        print(f"NAJCZYSTSZA: {best_date}  (cloud_frac={best_frac:.3f})")


if __name__ == "__main__":
    main()
