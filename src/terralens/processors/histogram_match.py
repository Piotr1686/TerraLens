"""T4.2 — Histogram matching między target a reference.

match_to_reference(): dopasowuje rozkład jasności target do reference
z pominięciem pikseli NaN (cloud mask). NaN piksele są zachowane w output.
"""

from __future__ import annotations

import numpy as np
from skimage.exposure import match_histograms


def match_to_reference(
    target: np.ndarray,
    reference: np.ndarray,
    mask: np.ndarray | None = None,
) -> np.ndarray:
    """Dopasowuje histogram target do reference, zachowując NaN.

    Args:
        target:    ndarray (H, W, C) float32 — obraz do korekcji, może zawierać NaN.
        reference: ndarray (H, W, C) float32 — obraz referencyjny (bez NaN).
        mask:      opcjonalny ndarray (H, W) bool — True = piksel ważny (nie chmura).
                   Jeśli None, maska jest wyprowadzana automatycznie z pozycji NaN w target.

    Returns:
        ndarray (H, W, C) float32 — target po korekcji histogramu; NaN zachowane.
    """
    target = target.astype(np.float32)
    reference = reference.astype(np.float32)

    # Maska ważnych pikseli: False gdzie NaN lub gdzie mask=False
    nan_mask = np.any(np.isnan(target), axis=-1)  # (H, W) bool — True gdzie NaN
    if mask is not None:
        valid = mask & ~nan_mask
    else:
        valid = ~nan_mask

    if not valid.any():
        return target  # wszystko zamaskowane — brak danych do korekcji

    # Tymczasowo wypełnij NaN zerem (match_histograms nie obsługuje NaN)
    filled = target.copy()
    filled[nan_mask] = 0.0

    # match_histograms na pełnych tablicach (channel-wise)
    matched = match_histograms(filled, reference, channel_axis=-1).astype(np.float32)

    # Przywróć NaN w pozycjach oryginalnych chmur
    matched[nan_mask] = np.nan
    return matched
