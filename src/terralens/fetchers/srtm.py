"""SRTM DEM fetcher z NASA Earthdata (LP DAAC) — wymaga auth z .env."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from terralens.config import get_config

logger = logging.getLogger(__name__)

# Earthdata SRTM 1-arc-second (SRTMGL1) via LP DAAC
SRTM_BASE = "https://e4ftl01.cr.usgs.gov/MEASURES/SRTMGL1.003/2000.02.11"

# Mapowanie regionu → lista tile'ów SRTM (nazwa pliku = S/N + E/W w SRTM1 naming)
# SRTM1 tile = 1° × 1° z nazwą według SW narożnika, np. N01W070.SRTMGL1.hgt.zip
REGION_SRTM_TILES: dict[str, list[str]] = {
    "amazonia": [
        "S10W070",
        "S10W060",
        "S05W070",
        "S05W060",
        "S01W070",
        "S01W060",
        "N00W070",
        "N00W060",
    ],
    "dubai": ["N24E054", "N24E055", "N25E054", "N25E055"],
    "arctic": [
        "N78W030",
        "N78W020",
        "N78W010",
        "N78E000",
        "N78E010",
        "N78E020",
        "N80W030",
        "N80W020",
        "N80W010",
        "N80E000",
        "N80E010",
        "N80E020",
    ],
}


def _get_auth() -> tuple[str, str]:
    """Czyta credentials NASA Earthdata z .env. Rzuca ValueError jeśli brak."""
    load_dotenv()
    user = os.getenv("NASA_EARTHDATA_USER", "")
    passwd = os.getenv("NASA_EARTHDATA_PASS", "")
    if not user or not passwd:
        raise ValueError(
            "Brak NASA_EARTHDATA_USER / NASA_EARTHDATA_PASS w .env. "
            "Skopiuj .env.example → .env i uzupełnij dane logowania Earthdata."
        )
    return user, passwd


def _srtm_url(tile_name: str) -> str:
    return f"{SRTM_BASE}/{tile_name}.SRTMGL1.hgt.zip"


def fetch_dem(
    region: str,
    output_dir: Path | None = None,
    force: bool = False,
) -> list[Path]:
    """Pobiera tile'y SRTM DEM dla regionu. Cachuje jako .hgt.zip w data/dem/.

    Args:
        region:     Nazwa regionu (amazonia/dubai/arctic).
        output_dir: Katalog docelowy (domyślnie data/dem/).
        force:      Wymuś pobranie mimo istniejących plików.

    Returns: Lista Path do pobranych / już istniejących plików.
    """
    if region not in REGION_SRTM_TILES:
        raise ValueError(f"Nieznany region: {region!r}. Dostępne: {list(REGION_SRTM_TILES)}")

    cfg = get_config()
    dest_dir = output_dir or (cfg.data_dir / "dem" / region)
    dest_dir.mkdir(parents=True, exist_ok=True)

    user, passwd = _get_auth()
    sess = requests.Session()
    sess.auth = (user, passwd)

    results: list[Path] = []
    tiles = REGION_SRTM_TILES[region]

    for tile_name in tiles:
        dest = dest_dir / f"{tile_name}.SRTMGL1.hgt.zip"
        if dest.exists() and not force:
            logger.debug("Cache hit DEM: %s", dest)
            results.append(dest)
            continue

        url = _srtm_url(tile_name)
        _download_dem_with_retry(sess, url, dest)
        results.append(dest)

    return results


def _download_dem_with_retry(
    session: requests.Session,
    url: str,
    dest: Path,
    max_retries: int = 3,
) -> None:
    """Pobiera plik DEM z retry (exponential backoff), obsługuje 401/429."""
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        if attempt > 0:
            backoff = 2 ** (attempt - 1)
            logger.warning("DEM retry %d/%d (backoff %ds): %s", attempt, max_retries, backoff, url)
            time.sleep(backoff)
        try:
            resp = session.get(url, timeout=60, allow_redirects=True)
            if resp.status_code == 401:
                raise PermissionError(
                    "NASA Earthdata: błąd uwierzytelniania (401). "
                    "Sprawdź NASA_EARTHDATA_USER i NASA_EARTHDATA_PASS w .env."
                )
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 30))
                logger.warning("Rate limit (429) — czekam %ds", retry_after)
                time.sleep(retry_after)
                last_exc = requests.HTTPError(response=resp)
                continue
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            logger.info("Pobrano DEM: %s", dest)
            return
        except (PermissionError, requests.HTTPError) as exc:
            if isinstance(exc, PermissionError):
                raise
            last_exc = exc
        except requests.RequestException as exc:
            last_exc = exc

    raise last_exc or RuntimeError(f"Nie udało się pobrać DEM {url}")
