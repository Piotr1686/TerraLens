"""Konfiguracja TerraLens — singleton dataclass zgodny z Hardware Execution Policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    # Ścieżki
    data_dir: Path = Path("data")
    cache_db: Path = Path("data/cache.db")
    export_dir: Path = Path("data/export")

    # Przetwarzanie kafelków (Hardware Execution Policy)
    tile_size: int = 512
    tile_overlap: int = 64
    batch_size: int = 1
    precision: str = "fp16"  # fp16 | fp32

    # VRAM (RTX 3050 Laptop 4GB — dostępne ~2.5GB po overhead)
    vram_budget_mb: int = 2500
    empty_cache_every_n_tiles: int = 2

    # Cache SQLite
    cache_ttl_days: int = 30

    # Regiony 3D globe (kolejność = 10-second hook: Amazonia → Dubai → Arktyka)
    regions: list[str] = field(default_factory=lambda: ["amazonia", "dubai", "arctic"])

    # Zakres dat domyślny
    year_start: int = 2015
    year_end: int = 2024

    # NASA GIBS WMTS
    gibs_base_url: str = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best"
    gibs_layers: dict[str, str] = field(
        default_factory=lambda: {
            "rgb": "HLS_L30_Nadir_BRDF_Adjusted_Reflectance",
            "ndvi": "MODIS_Terra_L3_NDVI_Monthly_9km",
        }
    )


_config: Config | None = None


def get_config() -> Config:
    """Zwraca singleton instancji Config (lazy init)."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config(new_config: Config | None = None) -> None:
    """Resetuje singleton — używane w testach."""
    global _config
    _config = new_config
