"""Offline weryfikator PMTiles — sprawdza header, metadata i integralność tile'ów."""

from __future__ import annotations

import argparse
import io
import random
import sys
from pathlib import Path

from PIL import Image
from pmtiles.reader import MmapSource, Reader
from pmtiles.tile import TileType

# Dodaj root projektu do path żeby zaimportować scan_tiles
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from terralens.export.pmtiles import scan_tiles

TILE_SAMPLE_PER_ZOOM = 3


def _tile_type_name(tt: int) -> str:
    names = {v: k for k, v in vars(TileType).items() if not k.startswith("_")}
    return names.get(tt, f"UNKNOWN({tt})")


def verify(pmtiles_path: Path, tile_dir: Path | None) -> bool:
    print(f"\n=== verify_pmtiles: {pmtiles_path} ===\n")

    with open(pmtiles_path, "rb") as f:
        reader = Reader(MmapSource(f))
        header = reader.header()
        metadata = reader.metadata()

        # --- Header ---
        tile_type = _tile_type_name(header.get("tile_type", -1))
        center_zoom = header.get("center_zoom", "?")
        min_lon = header.get("min_lon_e7", 0) / 1e7
        min_lat = header.get("min_lat_e7", 0) / 1e7
        max_lon = header.get("max_lon_e7", 0) / 1e7
        max_lat = header.get("max_lat_e7", 0) / 1e7

        print(f"tile_type    : {tile_type}")
        print(f"center_zoom  : {center_zoom}")
        print(f"bounds       : [{min_lon:.4f}, {min_lat:.4f}, {max_lon:.4f}, {max_lat:.4f}]")
        print(f"tile_count   : {header.get('tile_entries_count', '?')}")
        print(f"addressed    : {header.get('addressed_tiles_count', '?')}")
        print()

        # --- Metadata ---
        print("metadata:")
        for k, v in metadata.items():
            print(f"  {k}: {v}")
        print()

        # --- Tile sample ---
        if tile_dir is None:
            print("SKIP tile sample (nie podano --tile-dir)")
            return True

        if not tile_dir.exists():
            print(f"BŁĄD: tile_dir nie istnieje: {tile_dir}", file=sys.stderr)
            return False

        raw_tiles = scan_tiles(tile_dir)
        seen: dict[tuple[int, int, int], tuple[int, int, int, Path]] = {}
        for z, x, y, p in raw_tiles:
            key = (z, x, y)
            if key not in seen or str(p) > str(seen[key][3]):
                seen[key] = (z, x, y, p)

        by_zoom: dict[int, list[tuple[int, int, int]]] = {}
        for z, x, y, _ in seen.values():
            by_zoom.setdefault(z, []).append((z, x, y))

        zooms = sorted(by_zoom)
        print(f"Unikalne tile'y w tile_dir: {len(seen)} (zoom levels: {zooms})")
        print(f"Próbkuję {TILE_SAMPLE_PER_ZOOM} tile'ów per zoom...\n")

        all_ok = True
        for z in zooms:
            candidates = by_zoom[z]
            sample = random.sample(candidates, min(TILE_SAMPLE_PER_ZOOM, len(candidates)))
            for tz, tx, ty in sample:
                data = reader.get(tz, tx, ty)
                if data is None:
                    print(f"  [{tz}/{tx}/{ty}] MISSING w PMTiles")
                    all_ok = False
                    continue
                try:
                    img = Image.open(io.BytesIO(data))
                    fmt = img.format
                    ok = fmt == "WEBP"
                    status = "OK" if ok else f"BŁĄD format={fmt}"
                    if not ok:
                        all_ok = False
                except Exception as e:
                    status = f"BŁĄD decode: {e}"
                    all_ok = False
                print(f"  [{tz}/{tx}/{ty}] {status}")
            print()

        return all_ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline weryfikator PMTiles")
    parser.add_argument("--input", required=True, type=Path, help="Ścieżka do pliku .pmtiles")
    parser.add_argument(
        "--tile-dir",
        type=Path,
        default=None,
        help="Katalog tile'ów do próbkowania (opcjonalny, domyślnie data/tiles/HLS_RGB)",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"BŁĄD: plik nie istnieje: {args.input}", file=sys.stderr)
        sys.exit(1)

    tile_dir = args.tile_dir
    if tile_dir is None:
        # Heurystyka: katalog projektu / data/tiles/HLS_RGB
        project_root = Path(__file__).parent.parent
        default_tile_dir = project_root / "data" / "tiles" / "HLS_RGB"
        if default_tile_dir.exists():
            tile_dir = default_tile_dir

    ok = verify(args.input, tile_dir)
    if ok:
        print("WYNIK: OK — PMTiles gotowy do deployu")
        sys.exit(0)
    else:
        print("WYNIK: BŁĘDY — nie deployuj bez naprawy", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
