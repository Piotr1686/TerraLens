"""T2.4 — Testy SRTM DEM fetcher (mocked HTTP + credentials)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests
from terralens.config import Config, reset_config
from terralens.fetchers.srtm import REGION_SRTM_TILES, fetch_dem


@pytest.fixture(autouse=True)
def isolated_config(tmp_path: Path):
    cfg = Config(data_dir=tmp_path / "data", cache_db=tmp_path / "data" / "cache.db")
    reset_config(cfg)
    yield cfg
    reset_config(None)


@pytest.fixture
def mock_auth():
    with patch(
        "terralens.fetchers.srtm._get_auth",
        return_value=("test_user", "test_pass"),
    ):
        yield


def _ok_session(content: bytes = b"ZIP_DATA") -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.content = content
    resp.raise_for_status = MagicMock()
    sess = MagicMock(spec=requests.Session)
    sess.get.return_value = resp
    sess.auth = None
    return sess


def test_fetch_dem_downloads_tiles(tmp_path: Path, mock_auth: None) -> None:
    sess = _ok_session()
    with patch("terralens.fetchers.srtm.requests.Session", return_value=sess):
        paths = fetch_dem("dubai")
    assert len(paths) == len(REGION_SRTM_TILES["dubai"])
    for p in paths:
        assert p.exists()


def test_fetch_dem_skips_existing_files(tmp_path: Path, mock_auth: None) -> None:
    sess = _ok_session()
    with patch("terralens.fetchers.srtm.requests.Session", return_value=sess):
        fetch_dem("dubai")
        first_count = sess.get.call_count
        fetch_dem("dubai")
        second_count = sess.get.call_count
    # Drugie wywołanie nie powinno wykonać nowych requestów
    assert second_count == first_count


def test_fetch_dem_force_redownloads(tmp_path: Path, mock_auth: None) -> None:
    sess = _ok_session()
    with patch("terralens.fetchers.srtm.requests.Session", return_value=sess):
        fetch_dem("dubai")
        first_count = sess.get.call_count
        fetch_dem("dubai", force=True)
        second_count = sess.get.call_count
    assert second_count == first_count * 2


def test_fetch_dem_bad_credentials_raises(tmp_path: Path) -> None:
    resp = MagicMock()
    resp.status_code = 401
    resp.raise_for_status = MagicMock()
    sess = MagicMock(spec=requests.Session)
    sess.get.return_value = resp

    with (
        patch("terralens.fetchers.srtm._get_auth", return_value=("bad", "creds")),
        patch("terralens.fetchers.srtm.requests.Session", return_value=sess),
        pytest.raises(PermissionError, match="401"),
    ):
        fetch_dem("dubai")


def test_fetch_dem_retries_on_429(tmp_path: Path, mock_auth: None) -> None:
    resp_429 = MagicMock()
    resp_429.status_code = 429
    resp_429.headers = {"Retry-After": "0"}
    resp_429.raise_for_status = MagicMock(side_effect=requests.HTTPError(response=resp_429))

    resp_ok = MagicMock()
    resp_ok.status_code = 200
    resp_ok.content = b"ZIP"
    resp_ok.raise_for_status = MagicMock()

    sess = MagicMock(spec=requests.Session)
    # Dla pierwszego tile'a: 429 → ok; reszta od razu ok
    tile_count = len(REGION_SRTM_TILES["dubai"])
    sess.get.side_effect = [resp_429, resp_ok] + [resp_ok] * (tile_count - 1)

    with (
        patch("terralens.fetchers.srtm.requests.Session", return_value=sess),
        patch("terralens.fetchers.srtm.time.sleep"),
    ):
        paths = fetch_dem("dubai")
    assert len(paths) == tile_count


def test_fetch_dem_unknown_region_raises() -> None:
    with pytest.raises(ValueError, match="Nieznany region"):
        fetch_dem("nieznane_miejsce")


def test_missing_credentials_raises(tmp_path: Path) -> None:
    with patch.dict("os.environ", {"NASA_EARTHDATA_USER": "", "NASA_EARTHDATA_PASS": ""}):
        with pytest.raises(ValueError, match="NASA_EARTHDATA_USER"):
            fetch_dem("dubai")
