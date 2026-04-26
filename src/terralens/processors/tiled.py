"""T3.3 — Tiled processing z cosine-window overlap blending.

Dzieli obraz na kafelki tile_size×tile_size z overlap px zakładką,
uruchamia model per kafelek, scala wyniki ważoną sumą (cosine window),
zwalnia VRAM co empty_cache_every_n_tiles iteracji.
"""

from __future__ import annotations

import gc
import logging
from typing import Protocol

import numpy as np
import torch

from terralens.config import get_config
from terralens.engines.satlas_esrgan import SCALE

logger = logging.getLogger(__name__)


class Upscaler(Protocol):
    """Minimalny interfejs modelu SR — pozwala podstawiać mocki w testach."""

    def upscale(self, tile: np.ndarray) -> np.ndarray: ...


def _cosine_window(size: int) -> np.ndarray:
    """Zwraca kwadratowe okno cosinusowe size×size, wartości [0..1].

    Przesunięcie +0.5 (midpoint) zapewnia brak dokładnych zer na krawędziach,
    co pozwala na poprawną normalizację nawet dla pikseli pokrytych tylko jednym tile'em.
    """
    x = np.arange(size, dtype=np.float32) + 0.5
    w1d = 0.5 * (1.0 - np.cos(2.0 * np.pi * x / size))
    return np.outer(w1d, w1d)


def _extract_tile(image: np.ndarray, y: int, x: int, size: int) -> np.ndarray:
    """Wycina kafelek size×size z reflect-paddingiem gdy wychodzi poza obraz."""
    H, W = image.shape[:2]
    pad_b = max(0, y + size - H)
    pad_r = max(0, x + size - W)
    if pad_b > 0 or pad_r > 0:
        image = np.pad(image, ((0, pad_b), (0, pad_r), (0, 0)), mode="reflect")
    return image[y : y + size, x : x + size]


def process_tiled(
    image: np.ndarray,
    model: Upscaler,
    tile_size: int = 512,
    overlap: int = 64,
) -> np.ndarray:
    """Upscaluje obraz 4× przez model z tiled overlap blending.

    Args:
        image:     ndarray (H, W, 3) uint8 [0..255] lub float32 [0..1].
        model:     obiekt z metodą upscale(tile) → float32 [0..1].
        tile_size: rozmiar kafelka wejściowego (px).
        overlap:   szerokość zakładki między kafelkami (px).

    Returns:
        ndarray (H*4, W*4, 3) uint8 [0..255].
    """
    cfg = get_config()
    stride = tile_size - overlap
    if stride <= 0:
        raise ValueError(f"overlap ({overlap}) musi być mniejszy niż tile_size ({tile_size})")

    H, W = image.shape[:2]
    out_H, out_W = H * SCALE, W * SCALE

    canvas = np.zeros((out_H, out_W, 3), dtype=np.float32)
    weight_map = np.zeros((out_H, out_W, 1), dtype=np.float32)

    win_out = _cosine_window(tile_size * SCALE)[:, :, np.newaxis]  # (tile*4, tile*4, 1)

    ys = list(range(0, H, stride))
    xs = list(range(0, W, stride))
    total = len(ys) * len(xs)

    try:
        from rich.progress import (
            BarColumn,
            Progress,
            TaskProgressColumn,
            TextColumn,
            TimeRemainingColumn,
        )

        progress_ctx: object = Progress(
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
        )
        use_rich = True
    except ImportError:
        use_rich = False
        progress_ctx = None

    def _run(progress_obj=None, task_id=None):
        nonlocal canvas, weight_map
        tile_idx = 0

        for y in ys:
            for x in xs:
                tile_in = _extract_tile(image, y, x, tile_size)

                tile_out = model.upscale(tile_in)  # float32 [0..1], (tile*4, tile*4, 3)

                oy, ox = y * SCALE, x * SCALE
                valid_h = min(tile_size, H - y) * SCALE
                valid_w = min(tile_size, W - x) * SCALE

                canvas[oy : oy + valid_h, ox : ox + valid_w] += (
                    tile_out[:valid_h, :valid_w] * win_out[:valid_h, :valid_w]
                )
                weight_map[oy : oy + valid_h, ox : ox + valid_w] += win_out[:valid_h, :valid_w]

                tile_idx += 1
                if tile_idx % cfg.empty_cache_every_n_tiles == 0:
                    torch.cuda.empty_cache()
                    gc.collect()

                if progress_obj is not None:
                    progress_obj.advance(task_id)

            logger.debug("Rząd y=%d ukończony (%d/%d tile'ów)", y, tile_idx, total)

    if use_rich:
        with progress_ctx as prog:
            task = prog.add_task(f"Upscaling {H}×{W}→{out_H}×{out_W}", total=total)
            _run(prog, task)
    else:
        _run()

    # Normalizacja — unikamy dzielenia przez 0 w obszarach bez pokrycia
    weight_map = np.where(weight_map == 0, 1.0, weight_map)
    result = canvas / weight_map  # float32 [0..1]
    return np.clip(result * 255.0, 0, 255).astype(np.uint8)
