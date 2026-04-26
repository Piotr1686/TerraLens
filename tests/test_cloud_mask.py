"""T4.1 — Testy apply_cloud_mask + cloud_fraction."""

from __future__ import annotations

import warnings

import numpy as np
import pytest
from terralens.processors.cloud_mask import (
    InsufficientDataWarning,
    apply_cloud_mask,
    cloud_fraction,
)


def _image(h: int = 4, w: int = 4, val: int = 128) -> np.ndarray:
    return np.full((h, w, 3), val, dtype=np.uint8)


def _qa(h: int = 4, w: int = 4, val: float = 0.0) -> np.ndarray:
    return np.full((h, w), val, dtype=np.float32)


# ──────────────────────── apply_cloud_mask ─────────────────────────────────


class TestApplyCloudMask:
    def test_output_dtype_float32(self):
        result = apply_cloud_mask(_image(), _qa())
        assert result.dtype == np.float32

    def test_output_shape_unchanged(self):
        result = apply_cloud_mask(_image(8, 8), _qa(8, 8))
        assert result.shape == (8, 8, 3)

    def test_clear_sky_no_nans(self):
        """qa_band = 0.0 wszędzie → brak NaN."""
        result = apply_cloud_mask(_image(), _qa(val=0.0))
        assert not np.any(np.isnan(result))

    def test_cloudy_pixels_become_nan(self):
        """Piksele powyżej progu → NaN."""
        qa = _qa(4, 4, 0.0)
        qa[1, 1] = 0.5  # jeden cloudy piksel
        result = apply_cloud_mask(_image(), qa, threshold=0.2)
        assert np.isnan(result[1, 1, 0])
        assert not np.isnan(result[0, 0, 0])

    def test_threshold_boundary_excluded(self):
        """Piksel dokładnie na progu NIE jest maskowany (> nie >=)."""
        qa = _qa(val=0.2)
        result = apply_cloud_mask(_image(), qa, threshold=0.2)
        assert not np.any(np.isnan(result))

    def test_threshold_just_above_masked(self):
        qa = _qa(val=0.21)
        result = apply_cloud_mask(_image(), qa, threshold=0.2)
        assert np.all(np.isnan(result))

    def test_partial_mask_correct_count(self):
        """50% pikseli powyżej progu → 50% NaN."""
        img = _image(2, 2)
        qa = np.array([[0.0, 0.5], [0.0, 0.5]], dtype=np.float32)
        result = apply_cloud_mask(img, qa, threshold=0.2)
        nan_count = np.sum(np.isnan(result[:, :, 0]))
        assert nan_count == 2

    def test_100_percent_clouds_raises_warning(self):
        """100% chmur → InsufficientDataWarning."""
        with pytest.warns(InsufficientDataWarning, match="Zbyt duże zachmurzenie"):
            apply_cloud_mask(_image(), _qa(val=1.0), threshold=0.2)

    def test_51_percent_clouds_raises_warning(self):
        img = _image(10, 10)
        qa = np.zeros((10, 10), dtype=np.float32)
        qa[:6, :] = 0.5  # 60% > próg
        with pytest.warns(InsufficientDataWarning):
            apply_cloud_mask(img, qa, threshold=0.2)

    def test_49_percent_clouds_no_warning(self):
        img = _image(10, 10)
        qa = np.zeros((10, 10), dtype=np.float32)
        qa[:4, :9] = 0.5  # 36% > próg — poniżej 50%
        with warnings.catch_warnings():
            warnings.simplefilter("error", InsufficientDataWarning)
            apply_cloud_mask(img, qa, threshold=0.2)  # nie powinno rzucić

    def test_shape_mismatch_raises(self):
        with pytest.raises(ValueError, match="Niezgodne wymiary"):
            apply_cloud_mask(_image(4, 4), _qa(8, 8))

    def test_original_values_preserved_outside_mask(self):
        img = np.zeros((4, 4, 3), dtype=np.uint8)
        img[0, 0] = [10, 20, 30]
        qa = _qa(val=0.0)
        result = apply_cloud_mask(img, qa)
        np.testing.assert_array_almost_equal(result[0, 0], [10.0, 20.0, 30.0])


# ──────────────────────── cloud_fraction ───────────────────────────────────


class TestCloudFraction:
    def test_all_clear(self):
        assert cloud_fraction(_qa(val=0.0)) == pytest.approx(0.0)

    def test_all_cloudy(self):
        assert cloud_fraction(_qa(val=1.0)) == pytest.approx(1.0)

    def test_half_cloudy(self):
        qa = np.array([[0.0, 0.5], [0.0, 0.5]], dtype=np.float32)
        assert cloud_fraction(qa) == pytest.approx(0.5)

    def test_returns_float(self):
        assert isinstance(cloud_fraction(_qa()), float)
