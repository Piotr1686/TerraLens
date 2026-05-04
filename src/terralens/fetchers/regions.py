"""Definicje regionów i konwersja bbox → tile coordinates (EPSG:4326 WMTS)."""

from __future__ import annotations

# Bounding boxes: [lon_min, lat_min, lon_max, lat_max]
REGIONS: dict[str, list[float]] = {
    "amazonia": [-70.0, -10.0, -50.0, 0.0],
    "dubai": [54.5, 24.8, 55.5, 25.5],
    "arctic": [-30.0, 78.0, 30.0, 82.0],
}

# GIBS EPSG:4326 GlobalCRS84Scale TileMatrixSet — niestandardowe wymiary (nie 2^z).
# Zweryfikowane przez GIBS GetCapabilities dla TileMatrixSet 250m.
# z=1,2 wg OGC GlobalCRS84Scale (patrz MEMORY.md [2026-05-03]).
GIBS_MATRIX_WIDTHS: dict[int, int] = {
    0: 2,
    1: 3,
    2: 5,
    3: 10,
    4: 20,
    5: 40,
    6: 80,
    7: 160,
    8: 320,
}
GIBS_MATRIX_HEIGHTS: dict[int, int] = {
    0: 1,
    1: 2,
    2: 3,
    3: 5,
    4: 10,
    5: 20,
    6: 40,
    7: 80,
    8: 160,
}


def lon_to_col(lon: float, matrix_width: int) -> int:
    """Longitude → TileCol. matrix_width = liczba kolumn przy danym zoom."""
    return int((lon + 180.0) / 360.0 * matrix_width)


def lat_to_row(lat: float, matrix_height: int) -> int:
    """Latitude → TileRow (90° → wiersz 0). matrix_height = liczba wierszy."""
    return int((90.0 - lat) / 180.0 * matrix_height)


def bbox_to_tiles(
    bbox: list[float],
    zoom: int,
) -> list[tuple[int, int, int]]:
    """Konwertuje bbox [lon_min, lat_min, lon_max, lat_max] na listę (z, x, y).

    Returns:
        Lista krotek (zoom, col, row) — (z, x, y) w notacji fetch_tile.
    """
    if zoom not in GIBS_MATRIX_WIDTHS:
        raise ValueError(f"Zoom {zoom} poza zakresem GIBS (0–8)")

    mw = GIBS_MATRIX_WIDTHS[zoom]
    mh = GIBS_MATRIX_HEIGHTS[zoom]

    lon_min, lat_min, lon_max, lat_max = bbox

    col_min = lon_to_col(lon_min, mw)
    col_max = lon_to_col(lon_max, mw)
    # lat_max → mniejszy row (oś Y odwrócona)
    row_min = lat_to_row(lat_max, mh)
    row_max = lat_to_row(lat_min, mh)

    col_min = max(0, col_min)
    col_max = min(mw - 1, col_max)
    row_min = max(0, row_min)
    row_max = min(mh - 1, row_max)

    tiles = []
    for row in range(row_min, row_max + 1):
        for col in range(col_min, col_max + 1):
            tiles.append((zoom, col, row))
    return tiles


def region_tiles(region: str, zoom: int) -> list[tuple[int, int, int]]:
    """Zwraca listę (z, x, y) dla nazwanego regionu przy danym poziomie zoomu."""
    if region not in REGIONS:
        raise ValueError(f"Nieznany region: {region!r}. Dostępne: {list(REGIONS)}")
    return bbox_to_tiles(REGIONS[region], zoom)
