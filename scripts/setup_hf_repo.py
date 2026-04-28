"""Jednorazowy setup: tworzy publiczne repozytorium Hugging Face dla TerraLens.

Uruchom po wpisaniu HF_TOKEN do .env:
    conda run -n terralens python scripts/setup_hf_repo.py
"""

import os
import sys

from dotenv import load_dotenv
from huggingface_hub import HfApi, create_repo

load_dotenv()

token = os.getenv("HF_TOKEN", "")
repo_id = os.getenv("HF_REPO_ID", "Piotr1686/terralens-data")

if not token:
    print("BŁĄD: HF_TOKEN nie ustawiony w .env")
    sys.exit(1)

create_repo(repo_id, repo_type="dataset", private=False, token=token, exist_ok=True)

api = HfApi(token=token)
info = api.dataset_info(repo_id)

print(f"OK: https://huggingface.co/datasets/{repo_id}")
print(f"   SHA: {info.sha}")
print("Range Requests: obsługiwane przez HF CDN (Cloudflare)")
