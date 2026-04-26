"""T3.3 — Testy process_tiled: overlap blending, VRAM cleanup, edge cases."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from terralens.config import Config, reset_config
from terralens.processors.tiled import _cosine_window, _extract_tile, process_tiled


@pytest.fixture(autouse=True)
def _isolated_config():
    cfg = Config(empty_cache_every_n_tiles=2)
    reset_config(cfg)
    yield cfg
    reset_config(None)


def _make_model(scale: int = 4) -> MagicMock:
    """Mock modelu: zwraca stałą wartość 0.5 w odpowiednim rozmiarze."""

    def _upscale(tile: np.ndarray) -> np.ndarray:
        H, W = tile.shape[:2]
        return np.full((H * scale, W * scale, 3), 0.5, dtype=np.float32)

    model = MagicMock()
    model.upscale.side_effect = _upscale
    return model


# ──────────────────────── _cosine_window ───────────────────────────────────


class TestCosineWindow:
    def test_shape(self):
        w = _cosine_window(8)
        assert w.shape == (8, 8)

    def test_edges_near_zero(self):
        w = _cosine_window(64)
        assert w[0, 0] < 0.01
        assert w[0, -1] < 0.01
        assert w[-1, 0] < 0.01

    def test_center_near_one(self):
        w = _cosine_window(64)
        c = 32
        assert w[c, c] > 0.99

    def test_symmetric(self):
        w = _cosine_window(16)
        np.testing.assert_allclose(w, w.T, atol=1e-6)


# ──────────────────────── _extract_tile ────────────────────────────────────


class TestExtractTile:
    def test_interior_tile_no_padding(self):
        img = np.arange(100 * 100 * 3, dtype=np.uint8).reshape(100, 100, 3)
        tile = _extract_tile(img, 10, 20, 32)
        assert tile.shape == (32, 32, 3)
        np.testing.assert_array_equal(tile, img[10:42, 20:52])

    def test_edge_tile_padded_to_size(self):
        img = np.zeros((50, 50, 3), dtype=np.uint8)
        tile = _extract_tile(img, 40, 40, 32)
        assert tile.shape == (32, 32, 3)

    def test_corner_tile_padded(self):
        img = np.ones((10, 10, 3), dtype=np.uint8)
        tile = _extract_tile(img, 8, 8, 16)
        assert tile.shape == (16, 16, 3)


# ──────────────────────── process_tiled ────────────────────────────────────


class TestProcessTiled:
    def test_output_shape_4x(self):
        img = np.zeros((64, 64, 3), dtype=np.uint8)
        model = _make_model()
        with patch("torch.cuda.empty_cache"), patch("gc.collect"):
            result = process_tiled(img, model, tile_size=32, overlap=4)
        assert result.shape == (256, 256, 3)

    def test_output_dtype_uint8(self):
        img = np.zeros((32, 32, 3), dtype=np.uint8)
        model = _make_model()
        with patch("torch.cuda.empty_cache"), patch("gc.collect"):
            result = process_tiled(img, model, tile_size=32, overlap=4)
        assert result.dtype == np.uint8

    def test_uniform_input_produces_uniform_output(self):
        """Obraz jednolity → output jednolity (brak artefaktów na szwach)."""
        img = np.full((64, 64, 3), 128, dtype=np.uint8)
        model = _make_model()  # zawsze 0.5 → 128 po *255
        with patch("torch.cuda.empty_cache"), patch("gc.collect"):
            result = process_tiled(img, model, tile_size=32, overlap=8)
        assert result.shape == (256, 256, 3)
        # Wszystkie piksele powinny być ~127–128 (0.5 * 255 = 127.5)
        assert result.min() >= 120
        assert result.max() <= 135

    def test_no_seams_variance(self):
        """Wariancja outputu przy stałym modelu powinna być bliska 0."""
        img = np.zeros((128, 128, 3), dtype=np.uint8)
        model = _make_model()
        with patch("torch.cuda.empty_cache"), patch("gc.collect"):
            result = process_tiled(img, model, tile_size=64, overlap=16)
        assert result.var() < 1.0

    def test_empty_cache_called_every_n_tiles(self):
        """empty_cache musi być wywołane co cfg.empty_cache_every_n_tiles tile'ów."""
        img = np.zeros((128, 128, 3), dtype=np.uint8)
        model = _make_model()
        with (
            patch("torch.cuda.empty_cache") as mock_cache,
            patch("gc.collect"),
        ):
            process_tiled(img, model, tile_size=32, overlap=4)

        # stride=28, 128//28 = ~5 pozycji → ceil. Liczymy ile tile'ów i czy co 2 clean
        calls = mock_cache.call_count
        total_tiles = model.upscale.call_count
        expected_min_calls = total_tiles // 2
        assert calls >= expected_min_calls

    def test_model_called_for_each_tile(self):
        img = np.zeros((64, 64, 3), dtype=np.uint8)
        model = _make_model()
        stride = 32 - 8  # tile_size=32, overlap=8
        import math

        n = math.ceil(64 / stride)
        with patch("torch.cuda.empty_cache"), patch("gc.collect"):
            process_tiled(img, model, tile_size=32, overlap=8)
        assert model.upscale.call_count == n * n

    def test_invalid_overlap_raises(self):
        img = np.zeros((64, 64, 3), dtype=np.uint8)
        model = _make_model()
        with pytest.raises(ValueError, match="overlap"):
            process_tiled(img, model, tile_size=32, overlap=32)

    def test_non_square_image(self):
        img = np.zeros((64, 128, 3), dtype=np.uint8)
        model = _make_model()
        with patch("torch.cuda.empty_cache"), patch("gc.collect"):
            result = process_tiled(img, model, tile_size=32, overlap=4)
        assert result.shape == (256, 512, 3)

    def test_image_smaller_than_tile(self):
        """Obraz mniejszy niż tile_size — jeden tile z paddingiem."""
        img = np.zeros((16, 16, 3), dtype=np.uint8)
        model = _make_model()
        with patch("torch.cuda.empty_cache"), patch("gc.collect"):
            result = process_tiled(img, model, tile_size=32, overlap=4)
        assert result.shape == (64, 64, 3)
        assert model.upscale.call_count == 1
