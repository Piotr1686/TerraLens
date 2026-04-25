"""T2.2 — Testy bbox_to_tiles i region_tiles (EPSG:4326 WMTS)."""

from __future__ import annotations

import pytest
from terralens.fetchers.regions import REGIONS, lat_to_row, lon_to_col, region_tiles


def test_lon_to_col_basic() -> None:
    # lon=-180 → col 0 przy z=0 (2 kolumny)
    assert lon_to_col(-180.0, 0) == 0
    # lon=0 → środek → col = 2^1 / 2 = 1
    assert lon_to_col(0.0, 0) == 1


def test_lat_to_row_basic() -> None:
    # lat=90 → row 0 (góra)
    assert lat_to_row(90.0, 0) == 0
    # lat=-90 → ostatni row
    assert lat_to_row(-90.0, 0) == 1


def test_dubai_z8_less_than_20_tiles() -> None:
    tiles = region_tiles("dubai", zoom=8)
    assert len(tiles) < 20, f"Dubai @ z=8 ma {len(tiles)} tile'ów, oczekiwano < 20"


def test_all_tiles_have_correct_zoom(zoom: int = 6) -> None:
    tiles = region_tiles("amazonia", zoom)
    for z, x, y in tiles:
        assert z == zoom


def test_bbox_to_tiles_returns_nonempty_for_all_regions() -> None:
    for name in REGIONS:
        tiles = region_tiles(name, zoom=4)
        assert len(tiles) > 0, f"Region {name} zwrócił 0 tile'ów"


def test_bbox_to_tiles_tiles_within_bounds() -> None:
    zoom = 5
    max_col = 2 ** (zoom + 1) - 1
    max_row = 2**zoom - 1
    for name in REGIONS:
        for z, x, y in region_tiles(name, zoom):
            assert 0 <= x <= max_col, f"{name}: x={x} poza zakresem"
            assert 0 <= y <= max_row, f"{name}: y={y} poza zakresem"


def test_unknown_region_raises() -> None:
    with pytest.raises(ValueError, match="Nieznany region"):
        region_tiles("atlantyda", zoom=6)
