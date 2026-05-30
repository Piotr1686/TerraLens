"""Testy silnika Real-ESRGAN (RRDBNet x4) — unit + integration."""

from __future__ import annotations

import numpy as np
import pytest
import torch
from terralens.config import Config, reset_config
from terralens.engines.realesrgan import (
    _RRDB,
    SCALE,
    RealESRGAN,
    _ResidualDenseBlock,
    _RRDBNet,
    get_esrgan,
    reset_esrgan,
)


@pytest.fixture(autouse=True)
def _clean_singleton():
    reset_esrgan()
    yield
    reset_esrgan()


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path):
    # data_dir wskazuje na repo, żeby integracja używała pobranych wag (models/),
    # ale unit testy i tak nie ładują modelu.
    cfg = Config(data_dir=tmp_path / "data", cache_db=tmp_path / "data" / "cache.db")
    reset_config(cfg)
    yield cfg
    reset_config(None)


# ──────────────────────── unit tests (bez CUDA, bez wag) ────────────────────────


class TestArchitecture:
    def test_rdb_preserves_shape(self):
        block = _ResidualDenseBlock(num_feat=64, num_grow_ch=32)
        x = torch.randn(1, 64, 16, 16)
        assert block(x).shape == (1, 64, 16, 16)

    def test_rrdb_preserves_shape(self):
        block = _RRDB(num_feat=64, num_grow_ch=32)
        x = torch.randn(1, 64, 16, 16)
        assert block(x).shape == (1, 64, 16, 16)

    def test_rrdbnet_4x_upscale(self):
        """RRDBNet daje 4× w przestrzeni (mała sieć dla szybkości testu)."""
        net = _RRDBNet(num_feat=8, num_block=1, num_grow_ch=4)
        x = torch.randn(1, 3, 16, 16)
        out = net(x)
        assert out.shape == (1, 3, 16 * SCALE, 16 * SCALE)


class TestRealESRGANInterface:
    def test_initial_state_not_loaded(self):
        assert not RealESRGAN().is_loaded

    def test_unload_on_unloaded_is_noop(self):
        eng = RealESRGAN()
        eng.unload()
        assert not eng.is_loaded


class TestGetEsrgan:
    def test_singleton_same_instance(self):
        assert get_esrgan() is get_esrgan()

    def test_reset_creates_new_instance(self):
        a = get_esrgan()
        reset_esrgan()
        assert a is not get_esrgan()


# ──────────────────────── integration (wymaga CUDA + wag) ────────────────────────

cuda_required = pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA niedostępna — pomijam testy integracyjne",
)


@cuda_required
class TestRealESRGANIntegration:
    """Wymaga pobranych wag data/models/RealESRGAN_x4plus.pth (auto-download przy load)."""

    @pytest.fixture(autouse=True)
    def _repo_data_dir(self):
        # Użyj prawdziwego data_dir repo (z wagami), nie tmp_path.
        reset_config(Config())
        yield
        reset_config(None)

    def test_upscale_128_to_512(self):
        eng = RealESRGAN()
        tile = np.random.rand(128, 128, 3).astype(np.float32)
        result = eng.upscale(tile)
        assert result.shape == (128 * SCALE, 128 * SCALE, 3)
        eng.unload()

    def test_upscale_not_black(self):
        """Regresja: poprzedni silnik (Satlas) produkował czarne kafle."""
        eng = RealESRGAN()
        tile = np.random.rand(128, 128, 3).astype(np.float32)
        result = eng.upscale(tile)
        assert result.max() > 0.05, "Output prawie czarny — silnik SR nie działa!"
        eng.unload()

    def test_upscale_output_clipped(self):
        eng = RealESRGAN()
        tile = np.ones((128, 128, 3), dtype=np.float32)
        result = eng.upscale(tile)
        assert result.min() >= 0.0
        assert result.max() <= 1.0
        eng.unload()
