"""T4.3 — Testy compute_ssim_map, export_heatmap, compute_change_map."""

from __future__ import annotations

import numpy as np
from terralens.processors.ssim import compute_change_map, compute_ssim_map, export_heatmap


def _img(h: int, w: int, value: float = 128.0, channels: int = 3, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.uniform(value - 20, value + 20, (h, w, channels)).astype(np.float32)


class TestComputeSsimMap:
    def test_identical_images_ssim_one(self):
        """DoD: dwa identyczne obrazy → SSIM heatmap = 1.0 wszędzie."""
        img = _img(32, 32, 128.0)
        ssim_map = compute_ssim_map(img, img.copy())
        valid = ssim_map[~np.isnan(ssim_map)]
        assert valid.size > 0
        np.testing.assert_allclose(valid, 1.0, atol=1e-4)

    def test_output_shape(self):
        img = _img(16, 16, 128.0)
        ssim_map = compute_ssim_map(img, img.copy())
        assert ssim_map.shape == (16, 16)

    def test_output_dtype_float32(self):
        img = _img(8, 8, 128.0)
        assert compute_ssim_map(img, img.copy()).dtype == np.float32

    def test_changed_region_lower_ssim(self):
        """DoD: obszar ze zmianą (deforestacja-like) → niższy SSIM niż obszar niezmieniony."""
        ref = _img(32, 32, 128.0, seed=1)
        target = ref.copy()
        rng = np.random.default_rng(42)
        target[:12, :12] = rng.uniform(20, 40, (12, 12, 3)).astype(np.float32)

        ssim_map = compute_ssim_map(target, ref)

        changed = np.nanmean(ssim_map[2:10, 2:10])
        unchanged = np.nanmean(ssim_map[20:, 20:])
        assert (
            changed < unchanged
        ), f"Zmieniony obszar SSIM {changed:.3f} >= niezmieniony {unchanged:.3f}"

    def test_nan_input_propagates(self):
        """NaN w target → NaN w mapie SSIM na tej pozycji."""
        img = _img(16, 16, 128.0)
        img[5, 5] = np.nan
        ssim_map = compute_ssim_map(img, img.copy())
        assert np.isnan(ssim_map[5, 5])

    def test_grayscale_input(self):
        """Wejście (H, W) 2D bez osi kanałów → SSIM = 1.0 dla identycznych."""
        rng = np.random.default_rng(0)
        img = rng.uniform(0, 255, (16, 16)).astype(np.float32)
        ssim_map = compute_ssim_map(img, img.copy())
        assert ssim_map.shape == (16, 16)
        valid = ssim_map[~np.isnan(ssim_map)]
        np.testing.assert_allclose(valid, 1.0, atol=1e-4)

    def test_ssim_max_one(self):
        """Wartości SSIM nie mogą przekroczyć 1.0."""
        ref = _img(32, 32, 100.0, seed=0)
        rng = np.random.default_rng(99)
        target = rng.uniform(0, 255, (32, 32, 3)).astype(np.float32)
        ssim_map = compute_ssim_map(target, ref)
        assert np.all(ssim_map[~np.isnan(ssim_map)] <= 1.0 + 1e-5)

    def test_small_image_win_size_auto(self):
        """Obraz mniejszy niż domyślne okno SSIM 7×7 nie rzuca błędu."""
        img = _img(4, 4, 128.0)
        ssim_map = compute_ssim_map(img, img.copy())
        assert ssim_map.shape == (4, 4)


class TestExportHeatmap:
    def test_creates_png_file(self, tmp_path):
        out = tmp_path / "heatmap.png"
        export_heatmap(np.ones((16, 16), dtype=np.float32), out)
        assert out.exists()

    def test_output_correct_dimensions(self, tmp_path):
        from PIL import Image

        out = tmp_path / "heatmap.png"
        export_heatmap(np.ones((24, 32), dtype=np.float32) * 0.8, out)
        img = Image.open(out)
        assert img.size == (32, 24)  # PIL: (width, height)

    def test_nan_gets_zero_alpha(self, tmp_path):
        """NaN piksele → alpha = 0 w PNG."""
        from PIL import Image

        ssim_map = np.ones((8, 8), dtype=np.float32)
        ssim_map[3, 4] = np.nan
        out = tmp_path / "heatmap_nan.png"
        export_heatmap(ssim_map, out)
        arr = np.array(Image.open(out))
        assert arr[3, 4, 3] == 0, "NaN piksel powinien mieć alpha=0"

    def test_output_is_rgba(self, tmp_path):
        from PIL import Image

        out = tmp_path / "heatmap_rgba.png"
        export_heatmap(np.ones((8, 8), dtype=np.float32) * 0.5, out)
        img = Image.open(out)
        assert img.mode == "RGBA"

    def test_string_path_accepted(self, tmp_path):
        out = str(tmp_path / "heatmap_str.png")
        export_heatmap(np.ones((8, 8), dtype=np.float32), out)
        from pathlib import Path

        assert Path(out).exists()


class TestComputeChangeMap:
    def test_identical_images_no_change(self):
        """DoD: compute_change_map z identycznymi obrazami → SSIM ≈ 1.0."""
        img = _img(32, 32, 128.0)
        ssim_map = compute_change_map(img, img.copy())
        valid = ssim_map[~np.isnan(ssim_map)]
        np.testing.assert_allclose(valid, 1.0, atol=1e-4)

    def test_output_shape(self):
        img = _img(32, 32)
        assert compute_change_map(img, img.copy()).shape == (32, 32)

    def test_output_dtype_float32(self):
        img = _img(16, 16)
        assert compute_change_map(img, img.copy()).dtype == np.float32

    def test_with_zero_qa_bands(self):
        """Pipeline z QA band wszystkich zer (brak chmur) nie rzuca błędu."""
        img = _img(16, 16, 128.0)
        qa = np.zeros((16, 16), dtype=np.float32)
        ssim_map = compute_change_map(img, img.copy(), target_qa=qa, reference_qa=qa)
        assert ssim_map.shape == (16, 16)

    def test_with_qa_masks_nan_propagates(self):
        """QA band z chmurami → odpowiednie NaN w mapie wyjściowej."""
        img = _img(16, 16, 128.0)
        qa = np.zeros((16, 16), dtype=np.float32)
        qa[0, :] = 1.0  # cały pierwszy rząd = chmury
        ssim_map = compute_change_map(img, img.copy(), target_qa=qa)
        assert np.any(np.isnan(ssim_map))
