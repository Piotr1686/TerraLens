"""Real-ESRGAN super-resolution engine — singleton z lazy loading.

Architektura: RRDBNet (Real-ESRGAN x4plus) — zwendorowana, BEZ zależności od `basicsr`
(basicsr importuje usunięte `torchvision.transforms.functional_tensor` → crash na torchvision>=0.17).
Wagi: data/models/RealESRGAN_x4plus.pth (auto-download przy pierwszym load, ~64MB).

Zastąpił martwy silnik Satlas (SwinB + losowy dekoder → czarne kafle, brak wytrenowanych wag).
Interfejs zgodny z poprzednim silnikiem (load/unload/is_loaded/upscale + get_esrgan/reset_esrgan),
więc komenda `process` nie wymaga zmian poza importem.
"""

from __future__ import annotations

import gc
import logging

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F  # noqa: N812

from terralens.config import get_config

logger = logging.getLogger(__name__)

SCALE = 4  # współczynnik SR
_WEIGHTS_REL = "models/RealESRGAN_x4plus.pth"
_WEIGHTS_URL = (
    "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
)


# ──────────────────────── architektura RRDBNet (zwendorowana) ────────────────────────


class _ResidualDenseBlock(nn.Module):
    """Residual Dense Block — 5 konwolucji z gęstymi połączeniami (Real-ESRGAN)."""

    def __init__(self, num_feat: int = 64, num_grow_ch: int = 32) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(num_feat, num_grow_ch, 3, 1, 1)
        self.conv2 = nn.Conv2d(num_feat + num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv3 = nn.Conv2d(num_feat + 2 * num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv4 = nn.Conv2d(num_feat + 3 * num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv5 = nn.Conv2d(num_feat + 4 * num_grow_ch, num_feat, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * 0.2 + x


class _RRDB(nn.Module):
    """Residual in Residual Dense Block — 3 × RDB z residualem."""

    def __init__(self, num_feat: int, num_grow_ch: int = 32) -> None:
        super().__init__()
        self.rdb1 = _ResidualDenseBlock(num_feat, num_grow_ch)
        self.rdb2 = _ResidualDenseBlock(num_feat, num_grow_ch)
        self.rdb3 = _ResidualDenseBlock(num_feat, num_grow_ch)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.rdb1(x)
        out = self.rdb2(out)
        out = self.rdb3(out)
        return out * 0.2 + x


class _RRDBNet(nn.Module):
    """RRDBNet 4× — architektura zgodna z wagami RealESRGAN_x4plus.pth."""

    def __init__(
        self,
        num_in_ch: int = 3,
        num_out_ch: int = 3,
        num_feat: int = 64,
        num_block: int = 23,
        num_grow_ch: int = 32,
    ) -> None:
        super().__init__()
        self.conv_first = nn.Conv2d(num_in_ch, num_feat, 3, 1, 1)
        self.body = nn.Sequential(*[_RRDB(num_feat, num_grow_ch) for _ in range(num_block)])
        self.conv_body = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        # upsampling 2× + 2× = 4×
        self.conv_up1 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_hr = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_last = nn.Conv2d(num_feat, num_out_ch, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.conv_first(x)
        body_feat = self.conv_body(self.body(feat))
        feat = feat + body_feat
        feat = self.lrelu(self.conv_up1(F.interpolate(feat, scale_factor=2, mode="nearest")))
        feat = self.lrelu(self.conv_up2(F.interpolate(feat, scale_factor=2, mode="nearest")))
        return self.conv_last(self.lrelu(self.conv_hr(feat)))


# ──────────────────────── pobieranie wag ────────────────────────


def _download_weights(dst) -> None:  # noqa: ANN001
    """Pobiera wagi RealESRGAN_x4plus.pth z GitHub releases (verify=False — Windows cert)."""
    import requests
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    dst.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Pobieranie wag Real-ESRGAN z %s …", _WEIGHTS_URL)

    with requests.get(_WEIGHTS_URL, stream=True, verify=False, timeout=120) as r:
        r.raise_for_status()
        tmp = dst.with_suffix(dst.suffix + ".part")
        with tmp.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)
        tmp.replace(dst)
    logger.info("Wagi zapisane: %s (%.1f MB)", dst, dst.stat().st_size / 1e6)


# ──────────────────────── singleton wrapper ────────────────────────


class RealESRGAN:
    """Wrapper Real-ESRGAN z lazy loading — model ładowany przy pierwszym upscale()."""

    def __init__(self) -> None:
        self._model: _RRDBNet | None = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        """Buduje RRDBNet, ładuje wagi (pobiera jeśli brak), przenosi na CUDA FP16."""
        if self._model is not None:
            return

        weights_path = get_config().data_dir / _WEIGHTS_REL
        if not weights_path.exists():
            _download_weights(weights_path)

        logger.info("Ładowanie Real-ESRGAN (RRDBNet x4)…")
        model = _RRDBNet()
        state = torch.load(weights_path, map_location="cpu", weights_only=True)
        # RealESRGAN_x4plus przechowuje wagi pod 'params_ema' (fallback: 'params' / surowy dict)
        if isinstance(state, dict):
            state = state.get("params_ema") or state.get("params") or state
        model.load_state_dict(state, strict=True)

        self._model = model.half().cuda().eval()
        logger.info("Real-ESRGAN gotowy. VRAM: %.0f MB", torch.cuda.memory_allocated() / 1e6)

    def unload(self) -> None:
        """Zwalnia model z GPU i opróżnia cache VRAM."""
        if self._model is None:
            return
        del self._model
        self._model = None
        torch.cuda.empty_cache()
        gc.collect()
        logger.info("Real-ESRGAN zwolniony. VRAM: %.0f MB", torch.cuda.memory_allocated() / 1e6)

    def upscale(self, tile: np.ndarray) -> np.ndarray:
        """Upscale kafelka 4× przez Real-ESRGAN.

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


_instance: RealESRGAN | None = None


def get_esrgan() -> RealESRGAN:
    """Zwraca singleton RealESRGAN (lazy init klasy, nie modelu)."""
    global _instance
    if _instance is None:
        _instance = RealESRGAN()
    return _instance


def reset_esrgan() -> None:
    """Resetuje singleton (zwalnia model jeśli załadowany) — głównie do testów."""
    global _instance
    if _instance is not None:
        _instance.unload()
    _instance = None
