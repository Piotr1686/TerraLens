"""NASA GIBS WMTS tile fetcher — HLS RGB + MODIS NDVI."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import requests

from terralens.config import get_config
from terralens.db.queries import get_tile_status, init_db, insert_tile, is_expired

logger = logging.getLogger(__name__)

GIBS_BASE = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best"

# Mapowanie skróconych nazw warstw → parametry WMTS
# Warstwy zweryfikowane jako działające w GIBS EPSG:4326 250m TMS
LAYERS: dict[str, dict] = {
    "HLS_RGB": {
        "layer_id": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "tilematrixset": "250m",
        "fmt": "jpg",
    },
    "MODIS_NDVI": {
        "layer_id": "MODIS_Terra_NDVI_8Day",
        "tilematrixset": "250m",
        "fmt": "png",
    },
}


def tile_url(layer: str, date: str, z: int, row: int, col: int) -> str:
    """Buduje URL GIBS WMTS. row = TileRow (y), col = TileCol (x)."""
    meta = LAYERS[layer]
    return (
        f"{GIBS_BASE}/{meta['layer_id']}/default/{date}"
        f"/{meta['tilematrixset']}/{z}/{row}/{col}.{meta['fmt']}"
    )


def fetch_tile(
    layer: str,
    date: str,
    z: int,
    x: int,
    y: int,
    session: requests.Session | None = None,
    force: bool = False,
) -> Path:
    """Pobiera tile z NASA GIBS. Sprawdza cache SQLite przed HTTP.

    Args:
        layer:   Klucz z LAYERS (np. "MODIS_NDVI").
        date:    Data w formacie YYYY-MM-DD lub YYYY-MM.
        z:       Poziom zoomu (TileMatrix).
        x:       Kolumna tile'a (TileCol).
        y:       Wiersz tile'a (TileRow).
        session: Opcjonalna sesja requests (reużywana w batch fetch).
        force:   Wymuś pobranie mimo ważnego cache.

    Returns: Path do zapisanego pliku PNG.
    """
    if layer not in LAYERS:
        raise ValueError(f"Nieznana warstwa: {layer!r}. Dostępne: {list(LAYERS)}")

    cfg = get_config()
    ext = LAYERS[layer]["fmt"]
    output_path = cfg.data_dir / "tiles" / layer / date / str(z) / str(x) / f"{y}.{ext}"

    db = init_db(cfg.cache_db, cfg.cache_ttl_days)
    try:
        if not force:
            cached = get_tile_status(db, layer, date, z, x, y)
            if cached and not is_expired(cached) and Path(cached["filepath"]).exists():
                logger.debug("Cache hit: %s/%s z=%d x=%d y=%d", layer, date, z, x, y)
                return Path(cached["filepath"])

        url = tile_url(layer, date, z, y, x)
        sess = session or requests.Session()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        _download_with_retry(sess, url, output_path)

        insert_tile(db, layer, date, z, x, y, str(output_path), ttl_days=cfg.cache_ttl_days)
        logger.info("Pobrano: %s", output_path)
        return output_path
    finally:
        db.close()


def _download_with_retry(
    session: requests.Session,
    url: str,
    dest: Path,
    max_retries: int = 3,
    rate_sleep: float = 0.1,
) -> None:
    """HTTP GET z rate limitem i exponential backoff przy błędach."""
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        if attempt > 0:
            backoff = 2 ** (attempt - 1)
            logger.warning("Retry %d/%d (backoff %ds): %s", attempt, max_retries, backoff, url)
            time.sleep(backoff)
        time.sleep(rate_sleep)
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code == 404:
                resp.raise_for_status()  # 404 → nie retry
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            return
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                raise
            last_exc = exc
        except requests.RequestException as exc:
            last_exc = exc

    raise last_exc or RuntimeError(f"Nie udało się pobrać {url} po {max_retries} próbach")
