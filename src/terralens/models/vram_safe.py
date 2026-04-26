"""T3.2 — Decorator @vram_safe i dynamic tile sizing na podstawie wolnego VRAM."""

from __future__ import annotations

import functools
import gc
from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable)

# Progi VRAM w bajtach
_MIN_FREE_BYTES = 500 * 1024**2  # 500 MB — minimum przed wywołaniem
_HIGH_FREE_BYTES = 1500 * 1024**2  # 1500 MB — próg dla tile 512 px


def vram_safe(func: F) -> F:
    """Decorator: sprawdza wolne VRAM przed wywołaniem i synchronizuje po.

    Rzuca RuntimeError jeśli wolne VRAM < 500 MB — zamiast pozwolić
    na cichy OOM w środku pipeline'u.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        import torch

        torch.cuda.empty_cache()
        gc.collect()

        free, _total = torch.cuda.mem_get_info()
        if free < _MIN_FREE_BYTES:
            raise RuntimeError(
                f"Niewystarczające VRAM: {free / 1e6:.0f} MB wolne, " f"wymagane minimum 500 MB"
            )

        result = func(*args, **kwargs)
        torch.cuda.synchronize()
        return result

    return wrapper  # type: ignore[return-value]


def adaptive_tile_size() -> int:
    """Zwraca optymalny rozmiar tile'a na podstawie aktualnie wolnego VRAM.

    512 px jeśli wolne VRAM > 1500 MB, 256 px w przeciwnym razie.
    """
    import torch

    free, _total = torch.cuda.mem_get_info()
    return 512 if free >= _HIGH_FREE_BYTES else 256
