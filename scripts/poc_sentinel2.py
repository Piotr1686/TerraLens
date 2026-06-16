"""PoC S10 — Sentinel-2 L2A z Microsoft Planetary Computer: scene-pick + render kafla.

De-risk spike: dla (lat, lon) znajdź najmniej zachmurzoną świeżą scenę S2, pobierz przez hostowany
tiler MPC (pctiler) jeden kafel WebMercator i zapisz PNG. Pinuje parametry (assets=visual) i potwierdza
ostrość 10 m PRZED budową Cloudflare Workera.

Użycie:
    python scripts/poc_sentinel2.py --lat 25.08 --lon 55.14 --zoom 13   # Dubai Marina
"""

import argparse
import math
from pathlib import Path

import planetary_computer as pc
import requests
import urllib3
from pystac_client import Client

urllib3.disable_warnings()

# Windows: certifi nie ma intermediate certów MPC/Azure (patrz feedback_windows_ssl).
# pystac_client woła Session.send(prepped), który robi kwargs.setdefault("verify", self.verify)
# → decyduje atrybut sesji. Wymuszamy verify=False w __init__ każdej nowej Session
# (analogicznie do httpx-monkeypatch w export/deploy.py).
_orig_init = requests.Session.__init__


def _init_no_verify(self, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
    _orig_init(self, *args, **kwargs)
    self.verify = False


requests.Session.__init__ = _init_no_verify  # type: ignore[method-assign]

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
DATA_API = "https://planetarycomputer.microsoft.com/api/data/v1"


def lonlat_to_tile(lon: float, lat: float, z: int) -> tuple[int, int]:
    """WebMercator (XYZ) tile (x, y) dla punktu — standardowy slippy-map wzór."""
    n = 2**z
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=25.08)
    ap.add_argument("--lon", type=float, default=55.14)
    ap.add_argument("--zoom", type=int, default=13)
    ap.add_argument("--cloud", type=float, default=20.0, help="Maks. eo:cloud_cover %.")
    ap.add_argument("--out", default="data/_poc_s2_tile.png")
    args = ap.parse_args()

    # 1) STAC search — najmniej zachmurzona świeża scena nad punktem
    catalog = Client.open(STAC_URL, modifier=pc.sign_inplace)
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        intersects={"type": "Point", "coordinates": [args.lon, args.lat]},
        query={"eo:cloud_cover": {"lt": args.cloud}},
        sortby=[{"field": "properties.datetime", "direction": "desc"}],
        max_items=40,
    )
    items = list(search.items())
    if not items:
        print(f"Brak scen S2 < {args.cloud}% chmur nad ({args.lat},{args.lon})")
        return

    # min cloud, przy remisie najnowsza (lista już desc po dacie)
    best = min(items, key=lambda it: it.properties.get("eo:cloud_cover", 100.0))
    print(f"Scen znaleziono: {len(items)}")
    print(f"WYBRANA: {best.id}")
    print(f"  data: {best.properties.get('datetime')}")
    print(f"  cloud_cover: {best.properties.get('eo:cloud_cover'):.1f}%")
    print(f"  assets: 'visual' obecny: {'visual' in best.assets}")

    # 2) Pobierz kafel z hostowanego tilera MPC (assets=visual = TCI true-color 8-bit)
    x, y = lonlat_to_tile(args.lon, args.lat, args.zoom)
    tile_url = (
        f"{DATA_API}/item/tiles/WebMercatorQuad/{args.zoom}/{x}/{y}@1x.png"
        f"?collection=sentinel-2-l2a&item={best.id}&assets=visual"
    )
    print(f"\nKafel z{args.zoom}/{x}/{y}:\n  {tile_url}")

    r = requests.get(tile_url, timeout=60, verify=False)
    print(f"  HTTP {r.status_code} | {len(r.content)} B | {r.headers.get('content-type')}")
    if r.status_code == 200 and r.content:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(r.content)
        print(f"  zapisano: {out}")
    else:
        print(f"  BŁĄD treści: {r.text[:300]}")


if __name__ == "__main__":
    main()
