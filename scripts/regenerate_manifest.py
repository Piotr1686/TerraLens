"""Regeneruje manifest.json z aktualnymi changes.json bez rebuildowania PMTiles."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from terralens.config import get_config
from terralens.export.manifest import generate_manifest, save_manifest
from terralens.fetchers.regions import REGIONS

cfg = get_config()
export_dir = Path("data/export")
processed_dir = cfg.data_dir / "processed"

manifest = generate_manifest(
    regions=list(REGIONS),
    export_dir=export_dir,
    db_path=cfg.cache_db,
    processed_dir=processed_dir,
)
manifest_path = export_dir / "manifest.json"
save_manifest(manifest, manifest_path)
print(f"Manifest zapisano: {manifest_path}")

# Sprawdz zmiany per region
for region in REGIONS:
    changes = manifest["regions"][region].get("changes")
    latest = manifest["regions"][region].get("latest")
    print(f"  {region}: latest={latest}, changes={'OK' if changes else 'NULL'}")
