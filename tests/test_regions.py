"""T2.2 — Testy bbox_to_tiles i region_tiles (EPSG:4326 WMTS GIBS)."""

from __future__ import annotations

import pytest
from terralens.fetchers.regions import (
    GIBS_MATRIX_HEIGHTS,
    GIBS_MATRIX_WIDTHS,
    REGIONS,
    lat_to_row,
    lon_to_col,
    region_tiles,
)


def test_lon_to_col_basic() -> None:
    # lon=-180 → col 0 przy z=0 (matrix_width=2)
    assert lon_to_col(-180.0, GIBS_MATRIX_WIDTHS[0]) == 0
    # lon=0 → środek → col = 2 / 2 = 1
    assert lon_to_col(0.0, GIBS_MATRIX_WIDTHS[0]) == 1


def test_lat_to_row_basic() -> None:
    # lat=90 → row 0 (góra), matrix_height=1
    assert lat_to_row(90.0, GIBS_MATRIX_HEIGHTS[0]) == 0
    # lat=-90 → ostatni row przy matrix_height=1
    assert lat_to_row(-90.0, GIBS_MATRIX_HEIGHTS[0]) == 1


def test_gibs_z6_matrix_dimensions() -> None:
    # Zoom 6 = 80×40 (zweryfikowane przez GIBS GetCapabilities)
    assert GIBS_MATRIX_WIDTHS[6] == 80
    assert GIBS_MATRIX_HEIGHTS[6] == 40


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


def test_bbox_to_tiles_tiles_within_gibs_bounds() -> None:
    zoom = 5
    mw = GIBS_MATRIX_WIDTHS[zoom]
    mh = GIBS_MATRIX_HEIGHTS[zoom]
    for name in REGIONS:
        for z, x, y in region_tiles(name, zoom):
            assert 0 <= x <= mw - 1, f"{name}: x={x} poza zakresem GIBS z={zoom}"
            assert 0 <= y <= mh - 1, f"{name}: y={y} poza zakresem GIBS z={zoom}"


def test_unknown_region_raises() -> None:
    with pytest.raises(ValueError, match="Nieznany region"):
        region_tiles("atlantyda", zoom=6)


def test_zoom_out_of_range_raises() -> None:
    with pytest.raises(ValueError, match="poza zakresem GIBS"):
        region_tiles("amazonia", zoom=9)
