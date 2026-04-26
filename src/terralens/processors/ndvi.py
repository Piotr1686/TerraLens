"""T4.4 — NDVI diff dla MODIS.

MODIS NDVI z GIBS to gotowy produkt uint8 [0, 255] → skalowany do [0, 1].
compute_ndvi_diff(): diff = after - before, ujemne wartości = utrata roślinności.
save_changes_json(): statystyki do data/processed/{region}/changes.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def normalize_ndvi(raw: np.ndarray) -> np.ndarray:
    """Normalizuje NDVI do float32 [0, 1].

    uint8 [0, 255] → dzielenie przez 255.
    float32 / float64 → zwraca jako float32 bez zmian (zakłada [0, 1]).
    NaN piksele są zachowane.
    """
    if raw.dtype == np.uint8:
        return raw.astype(np.float32) / 255.0
    return raw.astype(np.float32)


def compute_ndvi_diff(
    ndvi_before: np.ndarray,
    ndvi_after: np.ndarray,
    deforestation_threshold: float = 0.2,
) -> tuple[np.ndarray, dict]:
    """Oblicza mapę różnicy NDVI i statystyki zmian.

    Args:
        ndvi_before:             ndarray (H, W) — NDVI przed zmianą (uint8 lub float32).
        ndvi_after:              ndarray (H, W) — NDVI po zmianie.
        deforestation_threshold: minimalny spadek NDVI uznany za deforestację (default 0.2).

    Returns:
        diff_map: ndarray (H, W) float32, wartości ∈ [-1, 1]; NaN gdzie brak danych.
                  Ujemne = utrata roślinności, dodatnie = wzrost.
        stats:    dict ze statystykami zmian.
    """
    before = normalize_ndvi(ndvi_before)
    after = normalize_ndvi(ndvi_after)

    valid_mask = ~np.isnan(before) & ~np.isnan(after)
    diff_map = np.where(valid_mask, after - before, np.nan).astype(np.float32)

    valid_diff = diff_map[valid_mask]
    n_total = int(valid_mask.sum())
    n_decrease = int((valid_diff < -deforestation_threshold).sum())

    stats: dict = {
        "ndvi_mean_before": float(np.nanmean(before)),
        "ndvi_mean_after": float(np.nanmean(after)),
        "ndvi_mean_diff": float(np.nanmean(diff_map)),
        "ndvi_std_diff": float(np.nanstd(diff_map)),
        "deforestation_threshold": float(deforestation_threshold),
        "pixels_total": n_total,
        "pixels_decrease_gt_threshold": n_decrease,
        "deforestation_fraction": n_decrease / n_total if n_total > 0 else 0.0,
    }

    return diff_map, stats


def save_changes_json(stats: dict, output_path: str | Path) -> None:
    """Zapisuje statystyki zmian do pliku JSON.

    Tworzy katalogi nadrzędne jeśli nie istnieją.

    Args:
        stats:       słownik statystyk (z compute_ndvi_diff).
        output_path: ścieżka docelowa, np. data/processed/amazonia/changes.json.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
