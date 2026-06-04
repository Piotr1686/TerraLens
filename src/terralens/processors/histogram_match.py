"""T4.2 — Histogram matching między target a reference.

match_to_reference(): dopasowuje rozkład jasności target do reference
z pominięciem pikseli NaN (cloud mask) PO OBU STRONACH. NaN piksele są
zachowane w output. Dopasowanie liczone kanał po kanale tylko na ważnych
pikselach — NaN w reference NIE trafia do kwantyli szablonu (kontrakt
skimage.match_histograms zakłada template bez NaN; naruszenie psuło CDF).
"""

from __future__ import annotations

import numpy as np


def _match_cumulative_cdf_masked(
    source_vals: np.ndarray,
    template_vals: np.ndarray,
) -> np.ndarray:
    """Dopasowuje CDF jednego kanału na płaskich tablicach ważnych pikseli.

    Odpowiednik skimage._match_cumulative_cdf, ale operuje na 1-D wektorach
    samych ważnych (nie-NaN) wartości, dzięki czemu ani źródło, ani szablon
    nie są zaszumione wypełniaczami NaN.

    Args:
        source_vals:   1-D ndarray — ważne wartości pikseli target (jeden kanał).
        template_vals: 1-D ndarray — ważne wartości pikseli reference (jeden kanał).

    Returns:
        1-D ndarray tej samej długości co source_vals — wartości po dopasowaniu.
    """
    src_values, src_inverse, src_counts = np.unique(
        source_vals, return_inverse=True, return_counts=True
    )
    tmpl_values, tmpl_counts = np.unique(template_vals, return_counts=True)

    src_quantiles = np.cumsum(src_counts) / source_vals.size
    tmpl_quantiles = np.cumsum(tmpl_counts) / template_vals.size

    interp_values = np.interp(src_quantiles, tmpl_quantiles, tmpl_values)
    return interp_values[src_inverse]


def match_to_reference(
    target: np.ndarray,
    reference: np.ndarray,
    mask: np.ndarray | None = None,
) -> np.ndarray:
    """Dopasowuje histogram target do reference, zachowując NaN.

    Dopasowanie liczone kanał po kanale na pikselach ważnych po obu stronach:
    rozkład źródła z ważnych pikseli target, rozkład szablonu z ważnych
    pikseli reference. Piksele NaN (chmury) w którymkolwiek obrazie nie
    wchodzą do kwantyli, więc nie zniekształcają mapowania.

    Args:
        target:    ndarray (H, W, C) float32 — obraz do korekcji, może zawierać NaN.
        reference: ndarray (H, W, C) float32 — obraz referencyjny, może zawierać NaN.
        mask:      opcjonalny ndarray (H, W) bool — True = piksel ważny (nie chmura).
                   Jeśli None, maska target jest wyprowadzana z pozycji NaN.

    Returns:
        ndarray (H, W, C) float32 — target po korekcji histogramu; NaN zachowane.
    """
    target = target.astype(np.float32)
    reference = reference.astype(np.float32)

    # Maski ważnych pikseli (True = ważny). Piksel chmury ma NaN we wszystkich kanałach.
    target_nan = np.any(np.isnan(target), axis=-1)  # (H, W)
    reference_nan = np.any(np.isnan(reference), axis=-1)  # (H, W)

    src_valid = ~target_nan if mask is None else (mask & ~target_nan)
    tmpl_valid = ~reference_nan

    # Bez ważnych pikseli po którejś stronie nie da się policzyć dopasowania.
    if not src_valid.any() or not tmpl_valid.any():
        return target

    # Start z kopii — masked-out i NaN piksele zachowują oryginalną wartość/NaN.
    matched = target.copy()

    n_channels = target.shape[-1]
    for c in range(n_channels):
        source_vals = target[..., c][src_valid]
        template_vals = reference[..., c][tmpl_valid]
        mapped = _match_cumulative_cdf_masked(source_vals, template_vals)
        matched[..., c][src_valid] = mapped.astype(np.float32)

    # NaN target pozostaje NaN (matched startował z kopii target).
    return matched
