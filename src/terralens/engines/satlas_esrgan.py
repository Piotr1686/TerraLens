"""Satlas ESRGAN super-resolution engine — singleton z lazy loading.

Architektura: Satlas SwinB backbone (pre-trained) + SR dekoder pixel-shuffle 4×.
Wagi dekodera: data/models/satlas_esrgan_x4.pt (opcjonalne — backbone zawsze pre-trained).
"""

from __future__ import annotations

import gc
import logging
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from terralens.config import get_config

logger = logging.getLogger(__name__)

SCALE = 4  # współczynnik SR
_FEAT_CH = 64  # kanały wewnętrzne dekodera
_DECODER_WEIGHTS = "models/satlas_esrgan_x4.pt"


# ──────────────────────── architektura ────────────────────────


class _UpBlock(nn.Module):
    """Blok pixel-shuffle 2× z LeakyReLU."""

    def __init__(self, ch: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(ch, ch * 4, 3, 1, 1),
            nn.PixelShuffle(2),
            nn.LeakyReLU(0.2, inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class _SRDecoder(nn.Module):
    """SR dekoder: feature map full-res → 4× upsample → RGB.

    Satlas FPN zwraca feature mapę w pełnej rozdzielczości wejścia (1/1 scale).
    2 × PixelShuffle(2) = 4× upsample → docelowe 4× SR end-to-end.
    """

    def __init__(self, in_ch: int) -> None:
        super().__init__()
        self.head = nn.Conv2d(in_ch, _FEAT_CH, 3, 1, 1)
        self.ups = nn.ModuleList([_UpBlock(_FEAT_CH) for _ in range(2)])
        self.tail = nn.Conv2d(_FEAT_CH, 3, 3, 1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.head(x)
        for up in self.ups:
            x = up(x)
        return self.tail(x)


def _extract_highest_res(out: object) -> torch.Tensor:
    """Wyciąga feature mapę o najwyższej rozdzielczości z wyjścia backbone."""
    if isinstance(out, torch.Tensor):
        return out
    if isinstance(out, list | tuple) and len(out) > 0:
        return out[0]  # Satlas FPN: indeks 0 = P2 = najwyższa rozdzielczość
    if isinstance(out, dict):
        return next(iter(out.values()))
    raise TypeError(f"Nieobsługiwany typ wyjścia backbone: {type(out)}")


class _ESRGANModel(nn.Module):
    """Pełny model: Satlas SwinB FPN backbone + SR dekoder 4×."""

    def __init__(self) -> None:
        super().__init__()
        import satlaspretrain_models  # noqa: PLC0415

        w = satlaspretrain_models.Weights()
        self.backbone = w.get_pretrained_model("Sentinel2_SwinB_SI_RGB", fpn=True)
        in_ch = self._probe_backbone_channels()
        logger.debug("SwinB FPN high-res channels: %d", in_ch)
        self.decoder = _SRDecoder(in_ch)

    def _probe_backbone_channels(self) -> int:
        """Sprawdza liczbę kanałów backbone przez dummy forward na CPU."""
        try:
            with torch.no_grad():
                dummy = torch.zeros(1, 3, 256, 256)
                out = self.backbone(dummy)
                return _extract_highest_res(out).shape[1]
        except Exception as exc:
            logger.warning("Probe backbone channels failed: %s. Fallback: 128.", exc)
            return 128

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feats = self.backbone(x)
        return self.decoder(_extract_highest_res(feats))


# ──────────────────────── singleton wrapper ────────────────────────


class SatlasESRGAN:
    """Wrapper ESRGAN z lazy loading — model ładowany przy pierwszym upscale()."""

    def __init__(self) -> None:
        self._model: _ESRGANModel | None = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        """Buduje model, ładuje wagi dekodera (jeśli są), przenosi na CUDA FP16."""
        if self._model is not None:
            return

        logger.info("Ładowanie Satlas ESRGAN (SwinB FPN + SR decoder 4×)…")
        model = _ESRGANModel()

        weights_path = get_config().data_dir / _DECODER_WEIGHTS
        if weights_path.exists():
            state = torch.load(weights_path, map_location="cpu", weights_only=True)
            model.decoder.load_state_dict(state)
            logger.info("Załadowano wagi dekodera z %s", weights_path)
        else:
            logger.warning(
                "Brak wag dekodera (%s) — dekoder niezainicjowany (backbone pre-trained).",
                weights_path,
            )

        self._model = model.half().cuda().eval()
        logger.info("ESRGAN gotowy. VRAM: %.0f MB", torch.cuda.memory_allocated() / 1e6)

    def unload(self) -> None:
        """Zwalnia model z GPU i opróżnia cache VRAM."""
        if self._model is None:
            return
        del self._model
        self._model = None
        torch.cuda.empty_cache()
        gc.collect()
        logger.info("ESRGAN zwolniony. VRAM: %.0f MB", torch.cuda.memory_allocated() / 1e6)

    def upscale(self, tile: np.ndarray) -> np.ndarray:
        """Upscale kafelka 4× przez ESRGAN.

        Args:
            tile: ndarray (H, W, 3) float32 [0..1] lub uint8 [0..255].

        Returns:
            ndarray (H*4, W*4, 3) float32 [0..1].
        """
        if self._model is None:
            self.load()

        if tile.dtype == np.uint8:
            tile = tile.astype(np.float32) / 255.0

        x = torch.from_numpy(tile.transpose(2, 0, 1)).unsqueeze(0).half().cuda()

        with torch.inference_mode():
            out = self._model(x)

        return out.squeeze(0).permute(1, 2, 0).float().cpu().numpy().clip(0.0, 1.0)

    def save_decoder_weights(self, path: Path | None = None) -> Path:
        """Zapisuje wagi dekodera SR (bez backbone — backbone jest pre-trained)."""
        if self._model is None:
            raise RuntimeError("Model nie załadowany — wywołaj load() najpierw.")
        out_path = path or (get_config().data_dir / _DECODER_WEIGHTS)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self._model.decoder.state_dict(), out_path)
        logger.info("Wagi dekodera zapisane: %s", out_path)
        return out_path


# ──────────────────────── moduł-level singleton ────────────────────────

_instance: SatlasESRGAN | None = None


def get_esrgan() -> SatlasESRGAN:
    """Zwraca singleton SatlasESRGAN (lazy init klasy, nie modelu)."""
    global _instance
    if _instance is None:
        _instance = SatlasESRGAN()
    return _instance


def reset_esrgan() -> None:
    """Resetuje singleton — używane w testach."""
    global _instance
    if _instance is not None:
        _instance.unload()
    _instance = None
