"""T3.2 — Testy @vram_safe decorator + adaptive_tile_size (unit, mock mem_get_info)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from terralens.models.vram_safe import adaptive_tile_size, vram_safe

# ──────────────────────── helpers ──────────────────────────────────────────

_2GB = 2 * 1024**3
_1GB = 1 * 1024**3
_400MB = 400 * 1024**2
_1_6GB = int(1.6 * 1024**3)


def _mock_cuda(free: int, total: int = _2GB):
    """Patch torch.cuda w vram_safe na podane wartości."""
    return (
        patch("terralens.models.vram_safe.vram_safe.__wrapped__", wraps=None),
        patch("torch.cuda.mem_get_info", return_value=(free, total)),
        patch("torch.cuda.empty_cache"),
        patch("torch.cuda.synchronize"),
        patch("gc.collect"),
    )


# ──────────────────────── @vram_safe ───────────────────────────────────────


class TestVramSafeDecorator:
    def test_calls_function_when_vram_sufficient(self):
        sentinel = object()

        @vram_safe
        def _fn():
            return sentinel

        with (
            patch("torch.cuda.mem_get_info", return_value=(_1GB, _2GB)),
            patch("torch.cuda.empty_cache"),
            patch("torch.cuda.synchronize"),
            patch("gc.collect"),
        ):
            assert _fn() is sentinel

    def test_raises_on_insufficient_vram(self):
        @vram_safe
        def _fn():
            return 42

        with (
            patch("torch.cuda.mem_get_info", return_value=(_400MB, _2GB)),
            patch("torch.cuda.empty_cache"),
            patch("gc.collect"),
        ):
            with pytest.raises(RuntimeError, match="Niewystarczające VRAM"):
                _fn()

    def test_error_message_contains_free_mb(self):
        """Komunikat błędu musi podać wolne MB — czytelny diagnostyk."""

        @vram_safe
        def _fn():
            pass

        free = 200_000_000  # dokładnie 200 MB (dziesiętne, :.0f → "200")
        with (
            patch("torch.cuda.mem_get_info", return_value=(free, _2GB)),
            patch("torch.cuda.empty_cache"),
            patch("gc.collect"),
        ):
            with pytest.raises(RuntimeError, match="200 MB"):
                _fn()

    def test_synchronize_called_after_function(self):
        """synchronize() musi być wywołane po udanym wywołaniu."""

        @vram_safe
        def _fn():
            return 1

        with (
            patch("torch.cuda.mem_get_info", return_value=(_1GB, _2GB)),
            patch("torch.cuda.empty_cache"),
            patch("torch.cuda.synchronize") as mock_sync,
            patch("gc.collect"),
        ):
            _fn()
            mock_sync.assert_called_once()

    def test_empty_cache_called_before_function(self):
        call_order: list[str] = []

        @vram_safe
        def _fn():
            call_order.append("fn")
            return 1

        with (
            patch("torch.cuda.mem_get_info", return_value=(_1GB, _2GB)),
            patch("torch.cuda.empty_cache", side_effect=lambda: call_order.append("cache")),
            patch("torch.cuda.synchronize"),
            patch("gc.collect"),
        ):
            _fn()

        assert call_order == ["cache", "fn"]

    def test_preserves_function_name(self):
        @vram_safe
        def my_named_function():
            pass

        assert my_named_function.__name__ == "my_named_function"

    def test_synchronize_not_called_on_oom(self):
        """synchronize() NIE może być wywołane gdy RuntimeError (CUDA jest w złym stanie)."""

        @vram_safe
        def _fn():
            pass

        with (
            patch("torch.cuda.mem_get_info", return_value=(_400MB, _2GB)),
            patch("torch.cuda.empty_cache"),
            patch("torch.cuda.synchronize") as mock_sync,
            patch("gc.collect"),
        ):
            with pytest.raises(RuntimeError):
                _fn()
            mock_sync.assert_not_called()


# ──────────────────────── adaptive_tile_size ───────────────────────────────


class TestAdaptiveTileSize:
    def test_returns_512_when_vram_above_1500mb(self):
        with patch("torch.cuda.mem_get_info", return_value=(_1_6GB, _2GB)):
            assert adaptive_tile_size() == 512

    def test_returns_256_when_vram_below_1500mb(self):
        with patch("torch.cuda.mem_get_info", return_value=(_400MB, _2GB)):
            assert adaptive_tile_size() == 256

    def test_boundary_exactly_1500mb_returns_512(self):
        exactly_1500 = 1500 * 1024**2
        with patch("torch.cuda.mem_get_info", return_value=(exactly_1500, _2GB)):
            assert adaptive_tile_size() == 512

    def test_returns_int(self):
        with patch("torch.cuda.mem_get_info", return_value=(_1GB, _2GB)):
            result = adaptive_tile_size()
            assert isinstance(result, int)
