"""Definicje regionów i konwersja bbox → tile coordinates (EPSG:4326 WMTS)."""

from __future__ import annotations

# Bounding boxes: [lon_min, lat_min, lon_max, lat_max]
REGIONS: dict[str, list[float]] = {
    "amazonia": [-70.0, -10.0, -50.0, 0.0],
    "dubai": [54.5, 24.8, 55.5, 25.5],
    "arctic": [-30.0, 78.0, 30.0, 82.0],
}


def lon_to_col(lon: float, z: int) -> int:
    """Longitude → TileCol w EPSG:4326 WMTS.
    Przy poziomie z: 2^(z+1) kolumn na [-180, 180].
    """
    return int((lon + 180.0) / 360.0 * (2 ** (z + 1)))


def lat_to_row(lat: float, z: int) -> int:
    """Latitude → TileRow w EPSG:4326 WMTS.
    Przy poziomie z: 2^z wierszy na [-90, 90] (90 → wiersz 0).
    """
    return int((90.0 - lat) / 180.0 * (2**z))


def bbox_to_tiles(
    bbox: list[float],
    zoom: int,
) -> list[tuple[int, int, int]]:
    """Konwertuje bbox [lon_min, lat_min, lon_max, lat_max] na listę (z, x, y).

    Returns:
        Lista krotek (zoom, col, row) — (z, x, y) w notacji fetch_tile.
    """
    lon_min, lat_min, lon_max, lat_max = bbox

    col_min = lon_to_col(lon_min, zoom)
    col_max = lon_to_col(lon_max, zoom)
    # lat_max → mniejszy row (oś odwrócona)
    row_min = lat_to_row(lat_max, zoom)
    row_max = lat_to_row(lat_min, zoom)

    max_col = 2 ** (zoom + 1) - 1
    max_row = 2**zoom - 1

    col_min = max(0, col_min)
    col_max = min(max_col, col_max)
    row_min = max(0, row_min)
    row_max = min(max_row, row_max)

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
