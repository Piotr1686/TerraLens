"""PMTiles raster exporter — konwertuje tile'y PNG/JPEG do WebP PMTiles."""

from __future__ import annotations

import io
import re
from pathlib import Path

from PIL import Image
from pmtiles.tile import Compression, TileType, zxy_to_tileid
from pmtiles.writer import Writer

WEBP_QUALITY = 85

# Dopasowuje ostatni segment {z}/{x}/{y}.{ext} w dowolnej ścieżce
_TILE_RE = re.compile(r"(?P<z>\d+)[/\\](?P<x>\d+)[/\\](?P<y>\d+)\.(png|jpg|jpeg|webp)$")


def _to_webp(data: bytes, quality: int) -> bytes:
    """Konwertuje surowe bajty PNG/JPEG do WebP. WebP przechodzi bez zmian."""
    buf = io.BytesIO()
    Image.open(io.BytesIO(data)).save(buf, format="WEBP", quality=quality, method=4)
    return buf.getvalue()


def scan_tiles(tile_dir: Path) -> list[tuple[int, int, int, Path]]:
    """Skanuje katalog rekurencyjnie dla wzorca {z}/{x}/{y}.{ext}.

    Obsługuje zarówno płaską strukturę `{z}/{x}/{y}.png` jak i zagnieżdżoną
    `{layer}/{date}/{z}/{x}/{y}.png` — regex kotwi do końca ścieżki.

    Returns:
        Lista krotek (z, x, y, path), nieposortowana.
    """
    results: list[tuple[int, int, int, Path]] = []
    for p in tile_dir.rglob("*"):
        if not p.is_file():
            continue
        m = _TILE_RE.search(str(p))
        if m:
            results.append((int(m["z"]), int(m["x"]), int(m["y"]), p))
    return results


def build_pmtiles(
    tile_dir: Path,
    output_path: Path,
    metadata: dict,
    webp_quality: int = WEBP_QUALITY,
) -> Path:
    """Buduje plik PMTiles z katalogu tile'ów PNG/JPEG/WebP.

    Tile'y PNG i JPEG są konwertowane do WebP (quality=webp_quality).
    Tile'y już w WebP są przepisywane bez ponownej kompresji.
    Wynikowy PMTiles ma typ TileType.WEBP, kompresja wewnętrzna GZIP.

    Args:
        tile_dir:     Katalog z tile'ami; wzorzec {z}/{x}/{y}.{ext}.
        output_path:  Ścieżka docelowa pliku .pmtiles (katalog tworzony jeśli brak).
        metadata:     Słownik metadanych — pola specjalne:
                        ``bounds`` [lon_min, lat_min, lon_max, lat_max] → nagłówek PMTiles.
                        Pozostałe pola trafiają do sekcji metadata JSON w pliku.
        webp_quality: Jakość WebP dla konwertowanych tile'ów (0–100).

    Returns: output_path po zapisaniu.

    Raises:
        ValueError: Gdy tile_dir nie zawiera żadnych tile'ów.
    """
    tiles = scan_tiles(tile_dir)
    if not tiles:
        raise ValueError(f"Brak tile'ów w katalogu: {tile_dir}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    bounds = metadata.get("bounds")
    zoom_values = sorted({z for z, _, _, _ in tiles})
    center_zoom = zoom_values[len(zoom_values) // 2]

    header: dict = {
        "tile_type": TileType.WEBP,
        "tile_compression": Compression.NONE,
        "internal_compression": Compression.GZIP,
        "clustered": True,
        "center_zoom": center_zoom,
    }

    if bounds:
        lon_min, lat_min, lon_max, lat_max = bounds
        header["min_lon_e7"] = int(lon_min * 10_000_000)
        header["min_lat_e7"] = int(lat_min * 10_000_000)
        header["max_lon_e7"] = int(lon_max * 10_000_000)
        header["max_lat_e7"] = int(lat_max * 10_000_000)
        header["center_lon_e7"] = int((lon_min + lon_max) / 2 * 10_000_000)
        header["center_lat_e7"] = int((lat_min + lat_max) / 2 * 10_000_000)

    sorted_tiles = sorted(tiles, key=lambda t: zxy_to_tileid(t[0], t[1], t[2]))

    with open(output_path, "wb") as f:
        writer = Writer(f)
        for z, x, y, path in sorted_tiles:
            raw = path.read_bytes()
            if path.suffix.lower() in (".png", ".jpg", ".jpeg"):
                data = _to_webp(raw, webp_quality)
            else:
                data = raw
            writer.write_tile(zxy_to_tileid(z, x, y), data)
        writer.finalize(header, metadata)

    return output_path
