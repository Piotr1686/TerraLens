"""T2.1 — Testy GIBS WMTS fetcher z mock HTTP."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests
from terralens.config import Config, reset_config
from terralens.fetchers.gibs import LAYERS, fetch_tile, tile_url


@pytest.fixture(autouse=True)
def isolated_config(tmp_path: Path):
    """Każdy test dostaje własny data_dir i cache.db."""
    cfg = Config(data_dir=tmp_path / "data", cache_db=tmp_path / "data" / "cache.db")
    reset_config(cfg)
    yield cfg
    reset_config(None)


def _mock_session(content: bytes = b"PNG_DATA") -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.content = content
    resp.raise_for_status = MagicMock()
    sess = MagicMock(spec=requests.Session)
    sess.get.return_value = resp
    return sess


# --- tile_url ---


def test_tile_url_modis_ndvi() -> None:
    url = tile_url("MODIS_NDVI", "2023-06-01", 6, row=32, col=64)
    assert "MODIS_Terra_L3_NDVI_Monthly_9km" in url
    assert "2023-06-01" in url
    assert "/6/32/64.png" in url
    assert "2km" in url


def test_tile_url_hls_rgb() -> None:
    url = tile_url("HLS_RGB", "2022-08-15", 8, row=10, col=20)
    assert "HLS_L30_Nadir_BRDF_Adjusted_Reflectance" in url
    assert "31.25m" in url


# --- fetch_tile ---


def test_fetch_tile_downloads_and_saves(tmp_path: Path, isolated_config: Config) -> None:
    sess = _mock_session(b"\x89PNG\r\n")
    path = fetch_tile("MODIS_NDVI", "2023-06-01", 6, x=64, y=32, session=sess)
    assert path.exists()
    assert path.read_bytes() == b"\x89PNG\r\n"
    sess.get.assert_called_once()


def test_fetch_tile_cache_hit_skips_http(tmp_path: Path, isolated_config: Config) -> None:
    sess = _mock_session()
    # Pierwsze pobranie
    fetch_tile("MODIS_NDVI", "2023-06-01", 6, x=64, y=32, session=sess)
    assert sess.get.call_count == 1
    # Drugie pobranie — cache hit
    fetch_tile("MODIS_NDVI", "2023-06-01", 6, x=64, y=32, session=sess)
    assert sess.get.call_count == 1  # nadal 1, brak dodatkowego HTTP


def test_fetch_tile_force_bypasses_cache(tmp_path: Path, isolated_config: Config) -> None:
    sess = _mock_session()
    fetch_tile("MODIS_NDVI", "2023-06-01", 6, x=64, y=32, session=sess)
    fetch_tile("MODIS_NDVI", "2023-06-01", 6, x=64, y=32, session=sess, force=True)
    assert sess.get.call_count == 2


def test_fetch_tile_404_raises_immediately(isolated_config: Config) -> None:
    resp = MagicMock()
    resp.status_code = 404
    http_err = requests.HTTPError(response=resp)
    resp.raise_for_status.side_effect = http_err
    sess = MagicMock(spec=requests.Session)
    sess.get.return_value = resp

    with pytest.raises(requests.HTTPError):
        fetch_tile("MODIS_NDVI", "2023-06-01", 6, x=64, y=32, session=sess)
    assert sess.get.call_count == 1  # brak retry dla 404


def test_fetch_tile_retries_on_server_error(isolated_config: Config) -> None:
    resp_err = MagicMock()
    resp_err.status_code = 503
    http_err = requests.HTTPError(response=resp_err)
    resp_err.raise_for_status.side_effect = http_err

    resp_ok = MagicMock()
    resp_ok.status_code = 200
    resp_ok.content = b"PNG"
    resp_ok.raise_for_status = MagicMock()

    sess = MagicMock(spec=requests.Session)
    sess.get.side_effect = [resp_err, resp_ok]

    with patch("terralens.fetchers.gibs.time.sleep"):
        path = fetch_tile("MODIS_NDVI", "2023-06-01", 6, x=1, y=1, session=sess)
    assert sess.get.call_count == 2
    assert path.exists()


def test_fetch_tile_unknown_layer_raises(isolated_config: Config) -> None:
    with pytest.raises(ValueError, match="Nieznana warstwa"):
        fetch_tile("UNKNOWN_LAYER", "2023-06-01", 6, x=0, y=0)


def test_all_known_layers_have_required_keys() -> None:
    for name, meta in LAYERS.items():
        assert "layer_id" in meta, f"{name} brak layer_id"
        assert "tilematrixset" in meta, f"{name} brak tilematrixset"
        assert "fmt" in meta, f"{name} brak fmt"
