"""T5.3 — Testy deploy: collect_deploy_files + deploy_files + _load_hf_config."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from terralens.export.deploy import _load_hf_config, collect_deploy_files, deploy_files

# ---------------------------------------------------------------------------
# collect_deploy_files
# ---------------------------------------------------------------------------


def test_collect_empty_dir(tmp_path):
    assert collect_deploy_files(tmp_path, "amazonia") == []


def test_collect_pmtiles_only(tmp_path):
    (tmp_path / "amazonia_v20260101_120000.pmtiles").write_bytes(b"data")
    (tmp_path / "dubai_v20260101_120000.pmtiles").write_bytes(b"data")
    files = collect_deploy_files(tmp_path, "amazonia")
    assert len(files) == 1
    assert files[0].name == "amazonia_v20260101_120000.pmtiles"


def test_collect_includes_manifest(tmp_path):
    (tmp_path / "amazonia_v20260101_120000.pmtiles").write_bytes(b"data")
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    files = collect_deploy_files(tmp_path, "amazonia")
    names = [f.name for f in files]
    assert "manifest.json" in names
    assert names[-1] == "manifest.json"


def test_collect_manifest_absent_if_missing(tmp_path):
    (tmp_path / "amazonia_v20260101_120000.pmtiles").write_bytes(b"data")
    files = collect_deploy_files(tmp_path, "amazonia")
    assert all(f.name != "manifest.json" for f in files)


def test_collect_multiple_versions_sorted(tmp_path):
    (tmp_path / "amazonia_v20260201_000000.pmtiles").write_bytes(b"x")
    (tmp_path / "amazonia_v20260101_000000.pmtiles").write_bytes(b"y")
    files = collect_deploy_files(tmp_path, "amazonia")
    assert len(files) == 2
    assert files[0].name < files[1].name


# ---------------------------------------------------------------------------
# deploy_files — dry_run (brak uploadu)
# ---------------------------------------------------------------------------


def test_deploy_dry_run_returns_correct_urls(tmp_path):
    f = tmp_path / "amazonia_v20260101_120000.pmtiles"
    f.write_bytes(b"data")
    result = deploy_files(
        [f],
        token="hf_fake",
        repo_id="User/repo",
        public_url_base="https://huggingface.co/datasets/User/repo/resolve/main",
        dry_run=True,
    )
    assert result == {
        "amazonia_v20260101_120000.pmtiles": (
            "https://huggingface.co/datasets/User/repo/resolve/main/"
            "amazonia_v20260101_120000.pmtiles"
        )
    }


def test_deploy_dry_run_does_not_call_hf_api(tmp_path):
    f = tmp_path / "test.pmtiles"
    f.write_bytes(b"x")
    with patch("terralens.export.deploy.HfApi") as mock_cls:
        deploy_files(
            [f],
            token="hf_fake",
            repo_id="U/R",
            public_url_base="https://example.com",
            dry_run=True,
        )
    mock_cls.assert_not_called()


def test_deploy_dry_run_empty_files():
    result = deploy_files(
        [],
        token="hf_fake",
        repo_id="U/R",
        public_url_base="https://example.com",
        dry_run=True,
    )
    assert result == {}


# ---------------------------------------------------------------------------
# deploy_files — live (mocked HfApi)
# ---------------------------------------------------------------------------


def test_deploy_calls_upload_file(tmp_path):
    f = tmp_path / "amazonia_v1.pmtiles"
    f.write_bytes(b"pmtiles")
    mock_api = MagicMock()
    with patch("terralens.export.deploy.HfApi", return_value=mock_api):
        result = deploy_files(
            [f],
            token="hf_tok",
            repo_id="U/R",
            public_url_base="https://hf.co/datasets/U/R/resolve/main",
        )
    mock_api.upload_file.assert_called_once_with(
        path_or_fileobj=f,
        path_in_repo="amazonia_v1.pmtiles",
        repo_id="U/R",
        repo_type="dataset",
    )
    assert "amazonia_v1.pmtiles" in result


def test_deploy_uploads_all_files(tmp_path):
    files = [tmp_path / f"f{i}.pmtiles" for i in range(3)]
    for f in files:
        f.write_bytes(b"x")
    mock_api = MagicMock()
    with patch("terralens.export.deploy.HfApi", return_value=mock_api):
        result = deploy_files(
            files,
            token="t",
            repo_id="U/R",
            public_url_base="https://example.com",
        )
    assert mock_api.upload_file.call_count == 3
    assert len(result) == 3


def test_deploy_progress_callback(tmp_path):
    files = [tmp_path / f"f{i}.pmtiles" for i in range(3)]
    for f in files:
        f.write_bytes(b"x")
    called: list[str] = []
    mock_api = MagicMock()
    with patch("terralens.export.deploy.HfApi", return_value=mock_api):
        deploy_files(
            files,
            token="t",
            repo_id="U/R",
            public_url_base="https://example.com",
            on_progress=called.append,
        )
    assert called == ["f0.pmtiles", "f1.pmtiles", "f2.pmtiles"]


def test_deploy_dry_run_progress_callback(tmp_path):
    f = tmp_path / "test.pmtiles"
    f.write_bytes(b"x")
    called: list[str] = []
    deploy_files(
        [f],
        token="t",
        repo_id="U/R",
        public_url_base="https://example.com",
        dry_run=True,
        on_progress=called.append,
    )
    assert called == ["test.pmtiles"]


# ---------------------------------------------------------------------------
# _load_hf_config
# ---------------------------------------------------------------------------


def test_load_config_missing_token(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.setenv("HF_REPO_ID", "U/R")
    with pytest.raises(EnvironmentError, match="HF_TOKEN"):
        _load_hf_config()


def test_load_config_missing_repo(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_x")
    monkeypatch.delenv("HF_REPO_ID", raising=False)
    with pytest.raises(EnvironmentError, match="HF_REPO_ID"):
        _load_hf_config()


def test_load_config_default_public_url(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_tok")
    monkeypatch.setenv("HF_REPO_ID", "Piotr1686/terralens-data")
    monkeypatch.delenv("HF_PUBLIC_URL", raising=False)
    token, repo_id, url = _load_hf_config()
    assert token == "hf_tok"
    assert repo_id == "Piotr1686/terralens-data"
    assert "Piotr1686/terralens-data" in url
    assert url.startswith("https://")


def test_load_config_custom_public_url(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_tok")
    monkeypatch.setenv("HF_REPO_ID", "U/R")
    monkeypatch.setenv("HF_PUBLIC_URL", "https://custom.cdn.example.com")
    _, _, url = _load_hf_config()
    assert url == "https://custom.cdn.example.com"
