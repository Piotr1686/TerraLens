"""Smoke-test T5.3: tworzy minimalny PMTiles + manifest, uploaduje na HF, weryfikuje URL."""

import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image
from terralens.export.deploy import _load_hf_config, collect_deploy_files, deploy_files
from terralens.export.pmtiles import build_pmtiles

load_dotenv()

ROOT = Path(__file__).parent.parent
EXPORT_DIR = ROOT / "data" / "export"
TILE_DIR = ROOT / "data" / "tiles" / "_smoke_test" / "0" / "0"
TILE_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# --- 1. Jeden tile 1×1 WebP w strukturze z/x/y ---
img = Image.new("RGB", (1, 1), color=(34, 139, 34))
buf = io.BytesIO()
img.save(buf, format="WEBP", quality=85)
(TILE_DIR / "0.webp").write_bytes(buf.getvalue())
print("Tile: data/tiles/_smoke_test/0/0/0.webp")

# --- 2. PMTiles przez build_pmtiles ---
timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
pmtiles_path = EXPORT_DIR / f"amazonia_v{timestamp}.pmtiles"
metadata = {
    "type": "overlay",
    "name": "TerraLens smoke-test",
    "bounds": [-73.99, -9.24, -44.5, 5.27],
}
build_pmtiles(TILE_DIR.parent.parent, pmtiles_path, metadata)
print(f"PMTiles: {pmtiles_path.name} ({pmtiles_path.stat().st_size} B)")

# --- 3. Manifest ---
manifest = {
    "version": "1.0",
    "generated": datetime.now(tz=timezone.utc).isoformat(),
    "regions": {
        "amazonia": {
            "latest": pmtiles_path.name,
            "all_versions": [pmtiles_path.name],
            "timeline": [],
            "changes": None,
            "tour": {"lat": -5.0, "lon": -60.0, "altitude": 2_000_000, "duration_s": 3.5},
        }
    },
}
manifest_path = EXPORT_DIR / "manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"Manifest: {manifest_path.name}")

# --- 4. Deploy ---
token, repo_id, public_url_base = _load_hf_config()
files = collect_deploy_files(EXPORT_DIR, "amazonia")
print(f"\nUpload → {repo_id} ({len(files)} pliki):")
for f in files:
    print(f"  • {f.name}")

result = deploy_files(
    files,
    token=token,
    repo_id=repo_id,
    public_url_base=public_url_base,
    on_progress=lambda name: print(f"  ✓ {name}"),
)

# --- 5. Weryfikacja Range Request na manifest ---
manifest_url = result.get("manifest.json", "")
print(f"\nWeryfikacja Range Request: {manifest_url}")
req = urllib.request.Request(manifest_url, headers={"Range": "bytes=0-63"})
try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        status = resp.status
        content_range = resp.headers.get("Content-Range", "brak")
        body = resp.read()
        print(f"  HTTP {status} | Content-Range: {content_range} | bytes: {len(body)}")
        print(f"  Range Requests: {'OK ✓' if status == 206 else f'UWAGA — status {status}'}")
except Exception as exc:
    print(f"  Błąd weryfikacji: {exc}")

print(f"\nPublic URL PMTiles:\n  {result.get(pmtiles_path.name, '?')}")
print(f"Public URL Manifest:\n  {manifest_url}")
