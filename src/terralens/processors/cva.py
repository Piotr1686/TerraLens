"""T4.5 — Change Vector Analysis (CVA) w przestrzeni barw LAB.

compute_cva(): konwertuje RGB → LAB, liczy odległość euklidesową między
target a reference. Wykrywa zmiany koloru niezależnie od struktury.
classify_changes(): progowanie + kategorie (no_change / change).
"""

from __future__ import annotations

import numpy as np
from skimage.color import rgb2lab


def compute_cva(
    target: np.ndarray,
    reference: np.ndarray,
) -> np.ndarray:
    """Oblicza Change Vector Analysis w przestrzeni LAB.

    Odległość euklidesowa ΔE między target a reference w LAB.
    Wysoka wartość = duża zmiana koloru; dotyczy też zmian bez struktury
    (np. wysychanie, zmiana pokrywy, pożar) które SSIM może pominąć.

    Args:
        target:    ndarray (H, W, 3) uint8 lub float32 [0..255] — obraz nowszy.
        reference: ndarray (H, W, 3) uint8 lub float32 [0..255] — obraz bazowy.

    Returns:
        ndarray (H, W) float32 — mapa ΔE ≥ 0; NaN gdzie brak danych.
    """
    t = target.astype(np.float32)
    r = reference.astype(np.float32)

    nan_mask = np.any(np.isnan(t), axis=-1) | np.any(np.isnan(r), axis=-1)

    # rgb2lab wymaga float64 w [0, 1] lub uint8 w [0, 255]
    t_filled = np.nan_to_num(t, nan=0.0).astype(np.float64) / 255.0
    r_filled = np.nan_to_num(r, nan=0.0).astype(np.float64) / 255.0

    t_lab = rgb2lab(t_filled)
    r_lab = rgb2lab(r_filled)

    delta = t_lab - r_lab
    delta_e = np.sqrt((delta**2).sum(axis=-1)).astype(np.float32)
    delta_e[nan_mask] = np.nan

    return delta_e


def classify_changes(
    delta_e: np.ndarray,
    threshold: float = 10.0,
) -> np.ndarray:
    """Klasyfikuje piksele na podstawie ΔE.

    Args:
        delta_e:   ndarray (H, W) float32 — mapa z compute_cva().
        threshold: próg ΔE powyżej którego piksel = zmiana (default 10.0 wg CIE).

    Returns:
        ndarray (H, W) uint8 — 0 = brak zmian, 1 = zmiana, 255 = NaN (brak danych).
    """
    result = np.zeros(delta_e.shape, dtype=np.uint8)
    valid = ~np.isnan(delta_e)
    result[valid & (delta_e >= threshold)] = 1
    result[~valid] = 255
    return result


def compute_cva_stats(
    delta_e: np.ndarray,
    threshold: float = 10.0,
) -> dict:
    """Statystyki CVA: frakcja zmian, średnia ΔE, percentyle.

    Args:
        delta_e:   ndarray (H, W) float32 z compute_cva().
        threshold: próg klasyfikacji zmiany.

    Returns:
        dict ze statystykami.
    """
    valid = delta_e[~np.isnan(delta_e)]
    n_total = int(valid.size)
    n_changed = int((valid >= threshold).sum())

    return {
        "delta_e_mean": float(valid.mean()) if n_total > 0 else 0.0,
        "delta_e_std": float(valid.std()) if n_total > 0 else 0.0,
        "delta_e_p50": float(np.median(valid)) if n_total > 0 else 0.0,
        "delta_e_p95": float(np.percentile(valid, 95)) if n_total > 0 else 0.0,
        "change_threshold": float(threshold),
        "pixels_total": n_total,
        "pixels_changed": n_changed,
        "change_fraction": n_changed / n_total if n_total > 0 else 0.0,
    }
