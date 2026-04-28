"""T5.3 — Deploy PMTiles na Hugging Face Datasets jako CDN."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import HfApi

load_dotenv()

_HF_PUBLIC_BASE = "https://huggingface.co/datasets/{repo_id}/resolve/main"


def _load_hf_config() -> tuple[str, str, str]:
    """Czyta HF_TOKEN, HF_REPO_ID z .env.

    Returns: (token, repo_id, public_url_base)
    Raises: EnvironmentError gdy brakuje wymaganych zmiennych.
    """
    token = os.getenv("HF_TOKEN", "")
    repo_id = os.getenv("HF_REPO_ID", "")
    if not token:
        raise OSError("HF_TOKEN nie ustawiony w .env")
    if not repo_id:
        raise OSError("HF_REPO_ID nie ustawiony w .env")
    public_url = os.getenv(
        "HF_PUBLIC_URL",
        _HF_PUBLIC_BASE.format(repo_id=repo_id),
    )
    return token, repo_id, public_url


def collect_deploy_files(export_dir: Path, region: str) -> list[Path]:
    """Zbiera pliki do deploy: PMTiles dla regionu + manifest.json.

    PMTiles posortowane chronologicznie (v{timestamp}), manifest na końcu.
    """
    pmtiles = sorted(export_dir.glob(f"{region}_v*.pmtiles"))
    manifest = export_dir / "manifest.json"
    files: list[Path] = list(pmtiles)
    if manifest.exists():
        files.append(manifest)
    return files


def deploy_files(
    files: list[Path],
    *,
    token: str,
    repo_id: str,
    public_url_base: str,
    dry_run: bool = False,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, str]:
    """Uploaduje pliki do HF Datasets. Zwraca {filename: public_url}.

    Args:
        files:           Pliki do upload.
        token:           HF write token.
        repo_id:         HF repo ID (np. "Piotr1686/terralens-data").
        public_url_base: Bazowy URL bez trailing slash.
        dry_run:         True → brak uploadu, tylko buduje słownik URLs.
        on_progress:     Callable(filename) wywoływany po każdym pliku.
    """
    api = HfApi(token=token) if not dry_run else None
    result: dict[str, str] = {}

    for path in files:
        filename = path.name
        result[filename] = f"{public_url_base}/{filename}"
        if not dry_run and api is not None:
            api.upload_file(
                path_or_fileobj=path,
                path_in_repo=filename,
                repo_id=repo_id,
                repo_type="dataset",
            )
        if on_progress:
            on_progress(filename)

    return result
