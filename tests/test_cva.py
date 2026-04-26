"""T4.5 — Testy compute_cva, classify_changes, compute_cva_stats."""

from __future__ import annotations

import numpy as np
from terralens.processors.cva import classify_changes, compute_cva, compute_cva_stats

_EXPECTED_STATS_KEYS = {
    "delta_e_mean",
    "delta_e_std",
    "delta_e_p50",
    "delta_e_p95",
    "change_threshold",
    "pixels_total",
    "pixels_changed",
    "change_fraction",
}


def _img(h: int, w: int, value: float = 128.0, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.uniform(value - 20, value + 20, (h, w, 3)).astype(np.float32)


class TestComputeCva:
    def test_identical_images_delta_zero(self):
        """Identyczne obrazy → ΔE ≈ 0."""
        img = _img(16, 16, 128.0)
        delta_e = compute_cva(img, img.copy())
        valid = delta_e[~np.isnan(delta_e)]
        np.testing.assert_allclose(valid, 0.0, atol=1e-4)

    def test_output_shape(self):
        img = _img(16, 16)
        assert compute_cva(img, img.copy()).shape == (16, 16)

    def test_output_dtype_float32(self):
        img = _img(8, 8)
        assert compute_cva(img, img.copy()).dtype == np.float32

    def test_delta_e_nonnegative(self):
        """ΔE jest zawsze ≥ 0."""
        rng = np.random.default_rng(7)
        a = rng.uniform(0, 255, (16, 16, 3)).astype(np.float32)
        b = rng.uniform(0, 255, (16, 16, 3)).astype(np.float32)
        delta_e = compute_cva(a, b)
        assert np.all(delta_e[~np.isnan(delta_e)] >= 0)

    def test_cva_detects_color_change_without_structure(self):
        """DoD: CVA wykrywa zmiany koloru które SSIM pomija (płynna zmiana barwy).

        Obraz z jednolitym kolorem → zmieniony na inny jednolity kolor.
        SSIM = 1.0 (brak zmiany struktury), ale CVA > 0.
        """
        before = np.full((16, 16, 3), [100.0, 100.0, 100.0], dtype=np.float32)
        after = np.full((16, 16, 3), [200.0, 50.0, 50.0], dtype=np.float32)

        delta_e = compute_cva(before, after)
        assert np.nanmean(delta_e) > 5.0, "CVA powinno wykryć dużą zmianę koloru"

    def test_changed_region_higher_delta_e(self):
        """Obszar ze zmianą → wyższe ΔE niż obszar bez zmiany."""
        ref = _img(32, 32, 128.0, seed=1)
        target = ref.copy()
        rng = np.random.default_rng(42)
        target[:12, :12] = rng.uniform(200, 255, (12, 12, 3)).astype(np.float32)

        delta_e = compute_cva(target, ref)

        changed = np.nanmean(delta_e[2:10, 2:10])
        unchanged = np.nanmean(delta_e[20:, 20:])
        assert changed > unchanged

    def test_nan_input_propagates(self):
        """NaN w target → NaN w ΔE."""
        img = _img(8, 8, 128.0)
        img[3, 3] = np.nan
        delta_e = compute_cva(img, img.copy())
        assert np.isnan(delta_e[3, 3])

    def test_uint8_input_accepted(self):
        """uint8 wejście nie rzuca błędu."""
        img = np.full((8, 8, 3), 128, dtype=np.uint8)
        delta_e = compute_cva(img, img.copy())
        assert delta_e.shape == (8, 8)


class TestClassifyChanges:
    def test_no_change_below_threshold(self):
        """ΔE < threshold → klasa 0 (brak zmian)."""
        delta_e = np.full((8, 8), 5.0, dtype=np.float32)
        result = classify_changes(delta_e, threshold=10.0)
        assert np.all(result == 0)

    def test_change_above_threshold(self):
        """ΔE >= threshold → klasa 1 (zmiana)."""
        delta_e = np.full((8, 8), 15.0, dtype=np.float32)
        result = classify_changes(delta_e, threshold=10.0)
        assert np.all(result == 1)

    def test_nan_gets_class_255(self):
        """NaN piksele → klasa 255 (brak danych)."""
        delta_e = np.full((4, 4), 5.0, dtype=np.float32)
        delta_e[1, 1] = np.nan
        result = classify_changes(delta_e)
        assert result[1, 1] == 255

    def test_output_dtype_uint8(self):
        delta_e = np.ones((8, 8), dtype=np.float32)
        assert classify_changes(delta_e).dtype == np.uint8

    def test_mixed_classes(self):
        delta_e = np.array([[5.0, 15.0], [np.nan, 10.0]], dtype=np.float32)
        result = classify_changes(delta_e, threshold=10.0)
        assert result[0, 0] == 0  # poniżej progu
        assert result[0, 1] == 1  # powyżej progu
        assert result[1, 0] == 255  # NaN
        assert result[1, 1] == 1  # dokładnie na progu → zmiana


class TestComputeCvaStats:
    def test_stats_keys_present(self):
        delta_e = np.ones((8, 8), dtype=np.float32) * 5.0
        stats = compute_cva_stats(delta_e)
        assert _EXPECTED_STATS_KEYS.issubset(stats.keys())

    def test_change_fraction_correct(self):
        """50% pikseli powyżej progu → change_fraction = 0.5."""
        delta_e = np.zeros((4, 4), dtype=np.float32)
        delta_e[:2, :] = 20.0  # 8 px z 16 = 50%
        stats = compute_cva_stats(delta_e, threshold=10.0)
        np.testing.assert_allclose(stats["change_fraction"], 0.5, atol=0.01)

    def test_nan_excluded_from_stats(self):
        """NaN nie wchodzą do pixels_total."""
        delta_e = np.ones((4, 4), dtype=np.float32) * 5.0
        delta_e[0, 0] = np.nan
        stats = compute_cva_stats(delta_e)
        assert stats["pixels_total"] == 15

    def test_all_nan_returns_zeros(self):
        """Cały obraz NaN → statystyki = 0."""
        delta_e = np.full((4, 4), np.nan, dtype=np.float32)
        stats = compute_cva_stats(delta_e)
        assert stats["pixels_total"] == 0
        assert stats["change_fraction"] == 0.0

    def test_delta_e_mean_correct(self):
        delta_e = np.full((4, 4), 8.0, dtype=np.float32)
        stats = compute_cva_stats(delta_e)
        np.testing.assert_allclose(stats["delta_e_mean"], 8.0, atol=1e-5)

    def test_sanity_check_ndvi_cva_consistency(self):
        """DoD: sanity check — obszar ze zmianą koloru ma change_fraction > 0."""
        rng = np.random.default_rng(0)
        ref = rng.uniform(50, 100, (32, 32, 3)).astype(np.float32)
        target = ref.copy()
        target[:16, :16] = rng.uniform(150, 255, (16, 16, 3))  # duże zmiany koloru

        delta_e = compute_cva(target, ref)
        stats = compute_cva_stats(delta_e, threshold=10.0)
        assert stats["change_fraction"] > 0
