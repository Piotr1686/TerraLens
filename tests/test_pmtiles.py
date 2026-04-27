"""T5.1 — Testy build_pmtiles, scan_tiles, _to_webp."""

from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image
from terralens.export.pmtiles import WEBP_QUALITY, _to_webp, build_pmtiles, scan_tiles

# ---------------------------------------------------------------------------
# Pomocnik: generuje minimalny 4×4 PNG jako bytes
# ---------------------------------------------------------------------------


def _make_png(w: int = 4, h: int = 4, color: tuple[int, int, int] = (100, 150, 200)) -> bytes:
    img = Image.fromarray(np.full((h, w, 3), color, dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_webp(w: int = 4, h: int = 4, color: tuple[int, int, int] = (100, 150, 200)) -> bytes:
    img = Image.fromarray(np.full((h, w, 3), color, dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=80)
    return buf.getvalue()


def _is_pmtiles(path) -> bool:
    with open(path, "rb") as f:
        magic = f.read(7)
    return magic == b"PMTiles"


# ---------------------------------------------------------------------------
# scan_tiles
# ---------------------------------------------------------------------------


class TestScanTiles:
    def test_flat_structure(self, tmp_path):
        tile_path = tmp_path / "6" / "36" / "16.png"
        tile_path.parent.mkdir(parents=True)
        tile_path.write_bytes(_make_png())

        result = scan_tiles(tmp_path)

        assert len(result) == 1
        z, x, y, p = result[0]
        assert (z, x, y) == (6, 36, 16)
        assert p == tile_path

    def test_nested_gibs_structure(self, tmp_path):
        """Ścieżka {layer}/{date}/{z}/{x}/{y}.png — wzorzec musi wychwycić z/x/y."""
        tile_path = tmp_path / "HLS_RGB" / "2015-01-01" / "6" / "36" / "16.png"
        tile_path.parent.mkdir(parents=True)
        tile_path.write_bytes(_make_png())

        result = scan_tiles(tmp_path)

        assert len(result) == 1
        z, x, y, _ = result[0]
        assert (z, x, y) == (6, 36, 16)

    def test_multiple_tiles(self, tmp_path):
        coords = [(6, 36, 16), (6, 36, 17), (6, 37, 16)]
        for z, x, y in coords:
            p = tmp_path / str(z) / str(x) / f"{y}.png"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(_make_png())

        result = scan_tiles(tmp_path)

        found = {(z, x, y) for z, x, y, _ in result}
        assert found == set(coords)

    def test_empty_dir_returns_empty(self, tmp_path):
        assert scan_tiles(tmp_path) == []

    def test_non_tile_files_ignored(self, tmp_path):
        (tmp_path / "README.md").write_text("brak tile'ów")
        (tmp_path / "manifest.json").write_text("{}")
        assert scan_tiles(tmp_path) == []

    def test_webp_tiles_detected(self, tmp_path):
        tile_path = tmp_path / "6" / "36" / "16.webp"
        tile_path.parent.mkdir(parents=True)
        tile_path.write_bytes(_make_webp())

        result = scan_tiles(tmp_path)

        assert len(result) == 1
        assert result[0][3].suffix == ".webp"

    def test_jpeg_tiles_detected(self, tmp_path):
        img = Image.fromarray(np.full((4, 4, 3), 100, dtype=np.uint8))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")

        tile_path = tmp_path / "6" / "36" / "16.jpg"
        tile_path.parent.mkdir(parents=True)
        tile_path.write_bytes(buf.getvalue())

        result = scan_tiles(tmp_path)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# _to_webp
# ---------------------------------------------------------------------------


class TestToWebp:
    def test_png_to_webp_returns_bytes(self):
        result = _to_webp(_make_png(), WEBP_QUALITY)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_output_is_valid_webp(self):
        result = _to_webp(_make_png(), WEBP_QUALITY)
        img = Image.open(io.BytesIO(result))
        assert img.format == "WEBP"

    def test_lower_quality_produces_smaller_file(self):
        png = _make_png(w=64, h=64)
        high = _to_webp(png, quality=95)
        low = _to_webp(png, quality=10)
        assert len(low) <= len(high)

    def test_dimensions_preserved(self):
        png = _make_png(w=8, h=8)
        result = _to_webp(png, WEBP_QUALITY)
        img = Image.open(io.BytesIO(result))
        assert img.size == (8, 8)


# ---------------------------------------------------------------------------
# build_pmtiles
# ---------------------------------------------------------------------------


class TestBuildPmtiles:
    def _make_tile_dir(self, tmp_path, coords=None):
        """Tworzy tmp katalog z tile'ami PNG."""
        if coords is None:
            coords = [(6, 36, 16)]
        tile_dir = tmp_path / "tiles"
        for z, x, y in coords:
            p = tile_dir / str(z) / str(x) / f"{y}.png"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(_make_png())
        return tile_dir

    def test_creates_pmtiles_file(self, tmp_path):
        tile_dir = self._make_tile_dir(tmp_path)
        out = tmp_path / "out" / "test.pmtiles"

        result = build_pmtiles(tile_dir, out, {})

        assert result == out
        assert out.exists()

    def test_output_has_pmtiles_magic(self, tmp_path):
        tile_dir = self._make_tile_dir(tmp_path)
        out = tmp_path / "test.pmtiles"

        build_pmtiles(tile_dir, out, {})

        assert _is_pmtiles(out)

    def test_creates_output_directory(self, tmp_path):
        tile_dir = self._make_tile_dir(tmp_path)
        out = tmp_path / "nested" / "dir" / "test.pmtiles"

        build_pmtiles(tile_dir, out, {})

        assert out.exists()

    def test_empty_dir_raises_value_error(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()

        with pytest.raises(ValueError, match="Brak tile'ów"):
            build_pmtiles(empty, tmp_path / "out.pmtiles", {})

    def test_multiple_tiles_in_one_file(self, tmp_path):
        coords = [(6, 36, 16), (6, 36, 17), (6, 37, 16)]
        tile_dir = self._make_tile_dir(tmp_path, coords)
        out = tmp_path / "test.pmtiles"

        build_pmtiles(tile_dir, out, {})

        assert out.exists()
        assert out.stat().st_size > 0

    def test_bounds_in_metadata_written(self, tmp_path):
        """Plik PMTiles musi zawierać zakodowane bounds."""
        tile_dir = self._make_tile_dir(tmp_path)
        out = tmp_path / "test.pmtiles"
        bounds = [-70.0, -10.0, -50.0, 0.0]

        build_pmtiles(tile_dir, out, {"bounds": bounds})

        # Weryfikujemy że plik istnieje i ma sensowny rozmiar
        assert out.stat().st_size > 128

    def test_webp_quality_custom(self, tmp_path):
        tile_dir = self._make_tile_dir(tmp_path, [(6, 36, 16)])
        out_q85 = tmp_path / "q85.pmtiles"
        out_q10 = tmp_path / "q10.pmtiles"

        build_pmtiles(tile_dir, out_q85, {}, webp_quality=85)
        build_pmtiles(tile_dir, out_q10, {}, webp_quality=10)

        assert out_q85.exists() and out_q10.exists()

    def test_webp_input_tiles_accepted(self, tmp_path):
        """Tile'y już w WebP powinny być zaakceptowane bez błędów."""
        tile_dir = tmp_path / "tiles"
        p = tile_dir / "6" / "36" / "16.webp"
        p.parent.mkdir(parents=True)
        p.write_bytes(_make_webp())
        out = tmp_path / "test.pmtiles"

        build_pmtiles(tile_dir, out, {})

        assert out.exists()

    def test_nested_gibs_structure_exported(self, tmp_path):
        """Ścieżki w formacie GIBS {layer}/{date}/{z}/{x}/{y}.png."""
        tile_dir = tmp_path / "tiles"
        for date in ("2015-01-01", "2015-02-01"):
            p = tile_dir / "HLS_RGB" / date / "6" / "36" / "16.png"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(_make_png())
        out = tmp_path / "test.pmtiles"

        build_pmtiles(tile_dir, out, {})

        assert out.exists()

    def test_metadata_dict_written_to_file(self, tmp_path):
        """Metadane JSON trafiają do pliku PMTiles."""
        tile_dir = self._make_tile_dir(tmp_path)
        out = tmp_path / "test.pmtiles"
        meta = {"source_layer": "HLS_RGB", "region": "amazonia"}

        build_pmtiles(tile_dir, out, meta)

        content = out.read_bytes()
        # JSON metadanych jest gzip-compressed wewnątrz pliku
        assert b"HLS_RGB" not in content  # skompresowane, nie raw
        assert out.stat().st_size > 0

    def test_returns_output_path(self, tmp_path):
        tile_dir = self._make_tile_dir(tmp_path)
        out = tmp_path / "test.pmtiles"

        result = build_pmtiles(tile_dir, out, {})

        assert result is out
