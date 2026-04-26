"""T4.3 — SSIM change detection z pełnym preprocessingiem.

compute_ssim_map(): gaussian_blur → ssim(full=True) → mapa zmian.
export_heatmap():   SSIM map → kolorowy PNG (viridis, NaN = alpha 0).
compute_change_map(): pełny pipeline cloud_mask → match_hist → SSIM.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter
from skimage.metrics import structural_similarity

from terralens.processors.cloud_mask import apply_cloud_mask
from terralens.processors.histogram_match import match_to_reference


def compute_ssim_map(
    target: np.ndarray,
    reference: np.ndarray,
    blur_sigma: float = 1.5,
    data_range: float = 255.0,
    win_size: int | None = None,
) -> np.ndarray:
    """Oblicza pikselową mapę SSIM między target a reference po gaussian blur.

    Niskie SSIM (bliskie 0) = duże zmiany; SSIM = 1.0 = brak zmian.
    Piksele NaN w którymkolwiek obrazie → NaN w mapie wyjściowej.

    Args:
        target:     ndarray (H, W, C) lub (H, W) float32, NaN gdzie chmury.
        reference:  ndarray (H, W, C) lub (H, W) float32, te same wymiary.
        blur_sigma: sigma gaussowskiego rozmycia przed SSIM.
        data_range: zakres wartości pikseli (255.0 dla obrazów uint8-origin).
        win_size:   rozmiar okna SSIM (nieparzysty). None = min(7, min_dim).

    Returns:
        ndarray (H, W) float32 — mapa SSIM; NaN gdzie brak danych.
    """
    target = target.astype(np.float32)
    reference = reference.astype(np.float32)

    multichannel = target.ndim == 3

    if multichannel:
        nan_mask = np.any(np.isnan(target), axis=-1) | np.any(np.isnan(reference), axis=-1)
    else:
        nan_mask = np.isnan(target) | np.isnan(reference)

    t_filled = np.where(np.isnan(target), 0.0, target)
    r_filled = np.where(np.isnan(reference), 0.0, reference)

    # Rozmycie przestrzenne — sigma=0 na osi kanałów żeby nie mieszać kanałów
    if multichannel:
        sigma_3d = [blur_sigma, blur_sigma, 0.0]
        t_blur = gaussian_filter(t_filled, sigma=sigma_3d)
        r_blur = gaussian_filter(r_filled, sigma=sigma_3d)
    else:
        t_blur = gaussian_filter(t_filled, sigma=blur_sigma)
        r_blur = gaussian_filter(r_filled, sigma=blur_sigma)

    # win_size musi być nieparzysty i >= 3; dostosuj do rozmiaru obrazu
    min_dim = min(target.shape[:2])
    effective_win = win_size if win_size is not None else min(7, min_dim)
    if effective_win % 2 == 0:
        effective_win -= 1
    effective_win = max(effective_win, 3)

    kwargs: dict = {
        "data_range": data_range,
        "full": True,
        "win_size": effective_win,
    }
    if multichannel:
        kwargs["channel_axis"] = -1

    _, ssim_image = structural_similarity(t_blur, r_blur, **kwargs)

    # skimage zwraca (H, W, C) dla multichannel — uśredniamy do (H, W)
    if ssim_image.ndim == 3:
        ssim_image = ssim_image.mean(axis=-1)

    ssim_map = ssim_image.astype(np.float32)
    ssim_map[nan_mask] = np.nan
    return ssim_map


def export_heatmap(
    ssim_map: np.ndarray,
    output_path: str | Path,
    colormap: str = "viridis",
    vmin: float = 0.0,
    vmax: float = 1.0,
) -> None:
    """Eksportuje mapę SSIM jako kolorowy PNG (RGBA, NaN → alpha 0).

    Args:
        ssim_map:    ndarray (H, W) float32 — wartości SSIM.
        output_path: ścieżka do pliku PNG.
        colormap:    nazwa colormapy matplotlib (default: 'viridis').
        vmin/vmax:   zakres normalizacji przed koloryzacją.
    """
    import matplotlib.colors as mcolors
    from matplotlib import colormaps
    from PIL import Image

    cmap = colormaps[colormap]
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    nan_pixels = np.isnan(ssim_map)
    normed = norm(np.nan_to_num(ssim_map, nan=vmin))
    rgba = cmap(normed)  # (H, W, 4) float64

    # NaN → przezroczysty piksel
    rgba[nan_pixels, 3] = 0.0

    img_array = (rgba * 255).clip(0, 255).astype(np.uint8)
    Image.fromarray(img_array, mode="RGBA").save(str(output_path))


def compute_change_map(
    target: np.ndarray,
    reference: np.ndarray,
    target_qa: np.ndarray | None = None,
    reference_qa: np.ndarray | None = None,
    qa_threshold: float = 0.2,
    blur_sigma: float = 1.5,
    data_range: float = 255.0,
) -> np.ndarray:
    """Pełny pipeline change detection: cloud_mask → match_hist → SSIM.

    Args:
        target:       ndarray (H, W, C) uint8 lub float32 — obraz nowszy.
        reference:    ndarray (H, W, C) uint8 lub float32 — obraz bazowy.
        target_qa:    opcjonalny QA band (H, W) float32 dla target.
        reference_qa: opcjonalny QA band (H, W) float32 dla reference.
        qa_threshold: próg maskowania chmur (do apply_cloud_mask).
        blur_sigma:   sigma gaussowskiego rozmycia przed SSIM.
        data_range:   zakres wartości pikseli.

    Returns:
        ndarray (H, W) float32 — mapa SSIM; niskie wartości = duże zmiany.
    """
    if target_qa is not None:
        target = apply_cloud_mask(target, target_qa, qa_threshold)
    else:
        target = target.astype(np.float32)

    if reference_qa is not None:
        reference = apply_cloud_mask(reference, reference_qa, qa_threshold)
    else:
        reference = reference.astype(np.float32)

    target = match_to_reference(target, reference)

    return compute_ssim_map(target, reference, blur_sigma=blur_sigma, data_range=data_range)
