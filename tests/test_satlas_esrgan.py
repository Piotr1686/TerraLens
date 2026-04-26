"""T3.1 — Testy SatlasESRGAN wrapper (unit + integration)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch
from terralens.config import Config, reset_config
from terralens.engines.satlas_esrgan import (
    SCALE,
    SatlasESRGAN,
    _extract_highest_res,
    _SRDecoder,
    _UpBlock,
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
    cfg = Config(data_dir=tmp_path / "data", cache_db=tmp_path / "data" / "cache.db")
    reset_config(cfg)
    yield cfg
    reset_config(None)


# ──────────────────────── unit tests (bez CUDA) ────────────────────────


class TestUpBlock:
    def test_output_shape_doubles(self):
        block = _UpBlock(16)
        x = torch.randn(1, 16, 8, 8)
        out = block(x)
        assert out.shape == (1, 16, 16, 16)

    def test_channels_preserved(self):
        block = _UpBlock(32)
        x = torch.randn(1, 32, 4, 4)
        assert block(x).shape[1] == 32


class TestSRDecoder:
    def test_output_is_4x_upsample(self):
        """2 × PixelShuffle(2) = 4× całkowite powiększenie."""
        dec = _SRDecoder(in_ch=32)
        x = torch.randn(1, 32, 4, 4)
        out = dec(x)
        assert out.shape == (1, 3, 16, 16)  # 4 × 4 = 16 ✓

    def test_output_rgb_channels(self):
        dec = _SRDecoder(in_ch=16)
        x = torch.randn(1, 16, 8, 8)
        assert dec(x).shape[1] == 3

    def test_4x_sr_math(self):
        """Satlas FPN zwraca full-res (1/1), dekoder 4× → 4× SR end-to-end."""
        dec = _SRDecoder(in_ch=64)
        h, w = 256, 256  # FPN output = pełna rozdzielczość wejścia
        x = torch.randn(1, 64, h, w)
        out = dec(x)
        assert out.shape == (1, 3, h * 4, w * 4)  # 256*4 = 1024 ✓


class TestExtractHighestRes:
    def test_tensor_passthrough(self):
        t = torch.zeros(1, 64, 8, 8)
        assert _extract_highest_res(t) is t

    def test_list_returns_first(self):
        t1 = torch.zeros(1, 64, 8, 8)
        t2 = torch.zeros(1, 128, 4, 4)
        assert _extract_highest_res([t1, t2]) is t1

    def test_tuple_returns_first(self):
        t = torch.zeros(1, 64, 8, 8)
        assert _extract_highest_res((t, torch.zeros(1, 128, 4, 4))) is t

    def test_dict_returns_first_value(self):
        t = torch.zeros(1, 64, 8, 8)
        assert _extract_highest_res({"p2": t, "p3": torch.zeros(1, 128, 4, 4)}) is t

    def test_unknown_type_raises(self):
        with pytest.raises(TypeError):
            _extract_highest_res("not a tensor")


class TestSatlasESRGANInterface:
    def test_initial_state_not_loaded(self):
        esrgan = SatlasESRGAN()
        assert not esrgan.is_loaded

    def test_unload_on_unloaded_is_noop(self):
        esrgan = SatlasESRGAN()
        esrgan.unload()  # nie rzuca wyjątku
        assert not esrgan.is_loaded

    def test_save_decoder_weights_raises_when_unloaded(self):
        esrgan = SatlasESRGAN()
        with pytest.raises(RuntimeError, match="nie załadowany"):
            esrgan.save_decoder_weights()

    @patch("terralens.engines.satlas_esrgan._ESRGANModel")
    @patch("torch.cuda.memory_allocated", return_value=0)
    def test_load_sets_is_loaded(self, _mock_mem, MockModel):
        mock_model = MagicMock()
        mock_model.half.return_value = mock_model
        mock_model.cuda.return_value = mock_model
        mock_model.eval.return_value = mock_model
        MockModel.return_value = mock_model

        esrgan = SatlasESRGAN()
        esrgan.load()
        assert esrgan.is_loaded

    @patch("terralens.engines.satlas_esrgan._ESRGANModel")
    @patch("torch.cuda.memory_allocated", return_value=0)
    def test_load_idempotent(self, _mock_mem, MockModel):
        mock_model = MagicMock()
        mock_model.half.return_value = mock_model
        mock_model.cuda.return_value = mock_model
        mock_model.eval.return_value = mock_model
        MockModel.return_value = mock_model

        esrgan = SatlasESRGAN()
        esrgan.load()
        esrgan.load()  # drugi call = noop
        assert MockModel.call_count == 1

    @patch("terralens.engines.satlas_esrgan._ESRGANModel")
    @patch("torch.cuda.memory_allocated", return_value=0)
    @patch("torch.cuda.empty_cache")
    def test_unload_clears_model(self, _mock_cache, _mock_mem, MockModel):
        mock_model = MagicMock()
        mock_model.half.return_value = mock_model
        mock_model.cuda.return_value = mock_model
        mock_model.eval.return_value = mock_model
        MockModel.return_value = mock_model

        esrgan = SatlasESRGAN()
        esrgan.load()
        assert esrgan.is_loaded
        esrgan.unload()
        assert not esrgan.is_loaded


class TestGetEsrgan:
    def test_singleton_same_instance(self):
        a = get_esrgan()
        b = get_esrgan()
        assert a is b

    def test_reset_creates_new_instance(self):
        a = get_esrgan()
        reset_esrgan()
        b = get_esrgan()
        assert a is not b


# ──────────────────────── integration tests (wymaga CUDA) ────────────────────────

cuda_required = pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA niedostępna — pomijam testy integracyjne",
)


@cuda_required
class TestSatlasESRGANIntegration:
    def test_upscale_256_to_1024(self):
        """DoD T3.1: upscale(tile_256x256) → tile_1024x1024."""
        esrgan = SatlasESRGAN()
        tile = np.random.rand(256, 256, 3).astype(np.float32)
        result = esrgan.upscale(tile)
        assert result.shape == (256 * SCALE, 256 * SCALE, 3)
        esrgan.unload()

    def test_upscale_uint8_input(self):
        esrgan = SatlasESRGAN()
        tile = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
        result = esrgan.upscale(tile)
        assert result.shape == (1024, 1024, 3)
        assert result.dtype == np.float32
        esrgan.unload()

    def test_upscale_output_clipped(self):
        esrgan = SatlasESRGAN()
        tile = np.ones((256, 256, 3), dtype=np.float32)
        result = esrgan.upscale(tile)
        assert result.min() >= 0.0
        assert result.max() <= 1.0
        esrgan.unload()

    def test_lazy_load_on_first_upscale(self):
        esrgan = SatlasESRGAN()
        assert not esrgan.is_loaded
        esrgan.upscale(np.zeros((256, 256, 3), dtype=np.float32))
        assert esrgan.is_loaded
        esrgan.unload()

    def test_vram_stability_10_iterations(self):
        """DoD T3.1: delta VRAM < 50 MB przez 10 iteracji."""
        esrgan = SatlasESRGAN()
        esrgan.load()
        tile = np.random.rand(256, 256, 3).astype(np.float32)

        vrams: list[float] = []
        for _ in range(10):
            esrgan.upscale(tile)
            torch.cuda.synchronize()
            vrams.append(torch.cuda.memory_allocated() / 1e6)

        delta = max(vrams) - min(vrams)
        esrgan.unload()
        assert delta < 50.0, f"VRAM delta {delta:.1f} MB ≥ 50 MB — niestabilny!"

    def test_unload_frees_vram(self):
        """DoD T3.1: .unload() zwalnia VRAM do < 200 MB."""
        esrgan = SatlasESRGAN()
        esrgan.load()
        esrgan.unload()
        torch.cuda.synchronize()
        vram = torch.cuda.memory_allocated() / 1e6
        assert vram < 200.0, f"VRAM po unload: {vram:.0f} MB ≥ 200 MB"
