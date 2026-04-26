"""T4.1 — Cloud masking na podstawie QA band.

apply_cloud_mask(): piksele z qa_band > threshold → NaN.
Jeśli zamaskowane > 50% powierzchni → InsufficientDataWarning.
"""

from __future__ import annotations

import logging
import warnings

import numpy as np

logger = logging.getLogger(__name__)

# Próg pokrycia chmurami powyżej którego dane są nieużyteczne
_COVERAGE_WARN_THRESHOLD = 0.50


class InsufficientDataWarning(UserWarning):
    """Rzucane gdy >50% pikseli zostało zamaskowanych przez chmury."""


def apply_cloud_mask(
    image: np.ndarray,
    qa_band: np.ndarray,
    threshold: float = 0.2,
) -> np.ndarray:
    """Maskuje piksele z chmurami na NaN.

    Args:
        image:     ndarray (H, W, C) uint8 lub float32.
        qa_band:   ndarray (H, W) float32 [0..1] — wartość QA, wyżej = większe zachmurzenie.
        threshold: piksele z qa_band > threshold zostają zamaskowane.

    Returns:
        ndarray (H, W, C) float32 — wartość NaN gdzie chmury.

    Raises:
        InsufficientDataWarning: jeśli zamaskowane > 50% pikseli.
    """
    if image.shape[:2] != qa_band.shape[:2]:
        raise ValueError(
            f"Niezgodne wymiary: image {image.shape[:2]} vs qa_band {qa_band.shape[:2]}"
        )

    result = image.astype(np.float32)
    cloud_mask = qa_band > threshold  # (H, W) bool

    masked_fraction = cloud_mask.mean()
    if masked_fraction > _COVERAGE_WARN_THRESHOLD:
        warnings.warn(
            f"Zbyt duże zachmurzenie: {masked_fraction:.0%} pikseli zamaskowanych "
            f"(próg: {_COVERAGE_WARN_THRESHOLD:.0%}). Pomiń SSIM dla tego tile'u.",
            InsufficientDataWarning,
            stacklevel=2,
        )
        logger.warning("Niewystarczające dane: %.0f%% pikseli z chmurami", masked_fraction * 100)

    result[cloud_mask] = np.nan
    return result


def cloud_fraction(qa_band: np.ndarray, threshold: float = 0.2) -> float:
    """Zwraca ułamek [0..1] pikseli zaklasyfikowanych jako chmury."""
    return float((qa_band > threshold).mean())
