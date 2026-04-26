"""T4.4 — Testy compute_ndvi_diff, normalize_ndvi, save_changes_json."""

from __future__ import annotations

import json

import numpy as np
from terralens.processors.ndvi import compute_ndvi_diff, normalize_ndvi, save_changes_json

_EXPECTED_STATS_KEYS = {
    "ndvi_mean_before",
    "ndvi_mean_after",
    "ndvi_mean_diff",
    "ndvi_std_diff",
    "deforestation_threshold",
    "pixels_total",
    "pixels_decrease_gt_threshold",
    "deforestation_fraction",
}


class TestNormalizeNdvi:
    def test_uint8_to_float32(self):
        raw = np.array([[0, 128, 255]], dtype=np.uint8)
        result = normalize_ndvi(raw)
        assert result.dtype == np.float32
        np.testing.assert_allclose(result[0, 0], 0.0, atol=1e-6)
        np.testing.assert_allclose(result[0, 2], 1.0, atol=1e-6)

    def test_float32_passthrough(self):
        arr = np.array([[0.3, 0.7]], dtype=np.float32)
        result = normalize_ndvi(arr)
        assert result.dtype == np.float32
        np.testing.assert_allclose(result, arr, atol=1e-6)

    def test_nan_preserved(self):
        arr = np.array([[0.5, np.nan]], dtype=np.float32)
        result = normalize_ndvi(arr)
        assert np.isnan(result[0, 1])


class TestComputeNdviDiff:
    def test_no_change_diff_zero(self):
        """Te same NDVI przed i po → diff = 0."""
        ndvi = np.full((8, 8), 0.7, dtype=np.float32)
        diff, _ = compute_ndvi_diff(ndvi, ndvi.copy())
        np.testing.assert_allclose(diff, 0.0, atol=1e-6)

    def test_output_shape(self):
        ndvi = np.random.default_rng(0).uniform(0, 1, (32, 32)).astype(np.float32)
        diff, _ = compute_ndvi_diff(ndvi, ndvi.copy())
        assert diff.shape == (32, 32)

    def test_output_dtype_float32(self):
        ndvi = np.full((4, 4), 0.5, dtype=np.float32)
        diff, _ = compute_ndvi_diff(ndvi, ndvi.copy())
        assert diff.dtype == np.float32

    def test_diff_direction(self):
        """Wzrost NDVI → diff > 0; spadek → diff < 0."""
        before = np.full((4, 4), 0.4, dtype=np.float32)
        after_high = np.full((4, 4), 0.8, dtype=np.float32)
        after_low = np.full((4, 4), 0.1, dtype=np.float32)
        diff_gain, _ = compute_ndvi_diff(before, after_high)
        diff_loss, _ = compute_ndvi_diff(before, after_low)
        assert np.all(diff_gain > 0)
        assert np.all(diff_loss < 0)

    def test_diff_range(self):
        """Diff musi być w [-1, 1]."""
        rng = np.random.default_rng(0)
        before = rng.uniform(0, 1, (16, 16)).astype(np.float32)
        after = rng.uniform(0, 1, (16, 16)).astype(np.float32)
        diff, _ = compute_ndvi_diff(before, after)
        valid = diff[~np.isnan(diff)]
        assert valid.min() >= -1.0 - 1e-5
        assert valid.max() <= 1.0 + 1e-5

    def test_deforestation_detected(self):
        """DoD: symulacja Amazonia — obszar z NDVI drop > 0.2 → wykryty."""
        before = np.full((16, 16), 0.8, dtype=np.float32)
        after = before.copy()
        after[:8, :8] = 0.3  # NDVI drop = 0.5 > próg 0.2
        _, stats = compute_ndvi_diff(before, after)
        assert stats["pixels_decrease_gt_threshold"] > 0
        assert stats["deforestation_fraction"] > 0

    def test_deforestation_fraction_correct(self):
        """25% obrazu z deforestacją → deforestation_fraction ≈ 0.25."""
        before = np.full((16, 16), 0.8, dtype=np.float32)
        after = before.copy()
        after[:8, :8] = 0.3  # 64 px / 256 px = 25%
        _, stats = compute_ndvi_diff(before, after)
        np.testing.assert_allclose(stats["deforestation_fraction"], 0.25, atol=0.01)

    def test_no_deforestation_when_no_drop(self):
        """Brak znaczącego spadku → deforestation_fraction = 0."""
        before = np.full((8, 8), 0.5, dtype=np.float32)
        after = np.full((8, 8), 0.45, dtype=np.float32)  # drop = 0.05 < próg 0.2
        _, stats = compute_ndvi_diff(before, after)
        assert stats["pixels_decrease_gt_threshold"] == 0

    def test_uint8_input_accepted(self):
        """uint8 [0, 255] → normalizacja do [0, 1] przed diff."""
        before = np.full((8, 8), 200, dtype=np.uint8)
        after = np.full((8, 8), 100, dtype=np.uint8)
        diff, _ = compute_ndvi_diff(before, after)
        expected = (100 - 200) / 255.0
        np.testing.assert_allclose(diff[0, 0], expected, atol=1e-5)

    def test_nan_preserved(self):
        """NaN w wejściu → NaN w diff (nie w obszarach ważnych)."""
        before = np.full((8, 8), 0.7, dtype=np.float32)
        after = before.copy()
        before[3, 3] = np.nan
        diff, _ = compute_ndvi_diff(before, after)
        assert np.isnan(diff[3, 3])
        assert not np.isnan(diff[0, 0])

    def test_nan_excluded_from_stats(self):
        """Piksele NaN nie wchodzą do pixels_total."""
        before = np.full((4, 4), 0.5, dtype=np.float32)
        after = before.copy()
        before[0, 0] = np.nan
        _, stats = compute_ndvi_diff(before, after)
        assert stats["pixels_total"] == 15  # 16 - 1 NaN

    def test_stats_keys_present(self):
        ndvi = np.full((4, 4), 0.5, dtype=np.float32)
        _, stats = compute_ndvi_diff(ndvi, ndvi.copy())
        assert _EXPECTED_STATS_KEYS.issubset(stats.keys())

    def test_custom_threshold(self):
        """Niższy próg → więcej pikseli sklasyfikowanych jako deforestacja."""
        before = np.full((8, 8), 0.7, dtype=np.float32)
        after = np.full((8, 8), 0.55, dtype=np.float32)  # drop = 0.15
        _, stats_strict = compute_ndvi_diff(before, after, deforestation_threshold=0.2)
        _, stats_loose = compute_ndvi_diff(before, after, deforestation_threshold=0.1)
        assert (
            stats_loose["pixels_decrease_gt_threshold"]
            > stats_strict["pixels_decrease_gt_threshold"]
        )


class TestSaveChangesJson:
    def test_creates_file(self, tmp_path):
        out = tmp_path / "changes.json"
        save_changes_json({"key": 1.0}, out)
        assert out.exists()

    def test_creates_parent_dirs(self, tmp_path):
        """DoD: tworzy data/processed/{region}/changes.json."""
        out = tmp_path / "data" / "processed" / "amazonia" / "changes.json"
        save_changes_json({"key": 1}, out)
        assert out.exists()

    def test_json_content_readable(self, tmp_path):
        stats = {"deforestation_fraction": 0.15, "pixels_total": 1024}
        out = tmp_path / "changes.json"
        save_changes_json(stats, out)
        loaded = json.loads(out.read_text())
        assert loaded == stats

    def test_roundtrip_with_real_stats(self, tmp_path):
        """Statystyki z compute_ndvi_diff → save → load → identyczne."""
        before = np.full((16, 16), 0.8, dtype=np.float32)
        after = before.copy()
        after[:8, :8] = 0.3
        _, stats = compute_ndvi_diff(before, after)
        out = tmp_path / "amazonia" / "changes.json"
        save_changes_json(stats, out)
        loaded = json.loads(out.read_text())
        assert loaded["deforestation_fraction"] == stats["deforestation_fraction"]
        assert loaded["pixels_total"] == stats["pixels_total"]

    def test_string_path_accepted(self, tmp_path):
        out = str(tmp_path / "changes.json")
        save_changes_json({"k": 0}, out)
        from pathlib import Path

        assert Path(out).exists()
