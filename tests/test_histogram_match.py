"""T4.2 — Testy match_to_reference: histogram matching z NaN handling."""

from __future__ import annotations

import numpy as np
from terralens.processors.histogram_match import match_to_reference


def _img(h: int, w: int, mean: float, std: float = 20.0, seed: int = 0) -> np.ndarray:
    """Losowy obraz float32 z zadaną średnią i odchyleniem."""
    rng = np.random.default_rng(seed)
    return rng.normal(mean, std, (h, w, 3)).astype(np.float32)


class TestMatchToReference:
    def test_output_shape_preserved(self):
        t = _img(8, 8, 100)
        r = _img(8, 8, 150)
        result = match_to_reference(t, r)
        assert result.shape == t.shape

    def test_output_dtype_float32(self):
        result = match_to_reference(_img(4, 4, 100), _img(4, 4, 150))
        assert result.dtype == np.float32

    def test_mean_brightness_within_5_percent(self):
        """Po match średnia jasności target powinna być bliska reference (< 5% różnicy)."""
        t = _img(32, 32, 80.0, seed=1)
        r = _img(32, 32, 160.0, seed=2)
        result = match_to_reference(t, r)
        ref_mean = np.nanmean(r)
        res_mean = np.nanmean(result)
        relative_diff = abs(res_mean - ref_mean) / (ref_mean + 1e-6)
        assert relative_diff < 0.05, f"Różnica średniej: {relative_diff:.1%}"

    def test_nan_pixels_preserved(self):
        """NaN w target muszą pozostać NaN w output."""
        t = _img(8, 8, 100)
        t[2, 3] = np.nan
        t[5, 1] = np.nan
        r = _img(8, 8, 150)
        result = match_to_reference(t, r)
        assert np.all(np.isnan(result[2, 3]))
        assert np.all(np.isnan(result[5, 1]))

    def test_nan_not_spread(self):
        """NaN nie może pojawić się w miejscach gdzie go nie było."""
        t = _img(8, 8, 100)
        t[0, 0] = np.nan
        r = _img(8, 8, 150)
        result = match_to_reference(t, r)
        non_nan_before = ~np.any(np.isnan(t), axis=-1)
        non_nan_after = ~np.any(np.isnan(result), axis=-1)
        # Każde miejsce bez NaN przed → bez NaN po
        assert np.all(non_nan_after[non_nan_before])

    def test_all_nan_returns_unchanged(self):
        """Gdy wszystkie piksele to NaN, zwróć target bez zmian."""
        t = np.full((4, 4, 3), np.nan, dtype=np.float32)
        r = _img(4, 4, 150)
        result = match_to_reference(t, r)
        assert np.all(np.isnan(result))

    def test_identical_images_unchanged_mean(self):
        """Match identycznych obrazów → wynik bliski oryginałowi."""
        img = _img(16, 16, 120.0)
        result = match_to_reference(img.copy(), img.copy())
        np.testing.assert_allclose(np.nanmean(result), np.nanmean(img), rtol=0.01)

    def test_mask_parameter_accepted(self):
        """mask=(H,W) bool powinien być akceptowany bez błędu."""
        t = _img(8, 8, 100)
        r = _img(8, 8, 150)
        mask = np.ones((8, 8), dtype=bool)
        result = match_to_reference(t, r, mask=mask)
        assert result.shape == t.shape

    def test_uint8_input_accepted(self):
        """Wejście uint8 powinno być skonwertowane do float32."""
        t = np.full((4, 4, 3), 100, dtype=np.uint8)
        r = np.full((4, 4, 3), 200, dtype=np.uint8)
        result = match_to_reference(t, r)
        assert result.dtype == np.float32
