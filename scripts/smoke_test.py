"""T0.4 — Smoke test środowiska terralens."""

import sys


def main() -> None:
    checks: list[tuple[str, bool, str]] = []

    # 1. Python 3.10+
    ok = sys.version_info >= (3, 10)
    checks.append(("Python 3.10+", ok, sys.version.split()[0]))

    # 2. CUDA dostępne
    import torch

    cuda_ok = torch.cuda.is_available()
    checks.append(("CUDA available", cuda_ok, f"torch {torch.__version__}"))

    # 3. VRAM ≥ 3.5 GB
    if cuda_ok:
        props = torch.cuda.get_device_properties(0)
        vram_gb = props.total_memory / 1e9
        checks.append(
            (f"VRAM ≥ 3.5 GB ({props.name})", vram_gb >= 3.5, f"{vram_gb:.2f} GB")
        )
    else:
        checks.append(("VRAM ≥ 3.5 GB", False, "brak CUDA"))

    # 4. Kluczowe biblioteki
    try:
        import importlib.metadata

        import click  # noqa: F401
        import numpy as np
        import rasterio
        import requests
        import skimage

        libs = (
            f"numpy {np.__version__} | rasterio {rasterio.__version__}"
            f" | skimage {skimage.__version__} | requests {requests.__version__}"
            f" | click {importlib.metadata.version('click')}"
        )
        checks.append(("Core libs", True, libs))
    except ImportError as exc:
        checks.append(("Core libs", False, str(exc)))

    # 5. Wypisz wyniki
    all_ok = all(ok for _, ok, _ in checks)
    print("\nTerraLens — smoke test środowiska")
    print("=" * 50)
    for name, ok, info in checks:
        symbol = "✓" if ok else "✗"
        print(f"  {symbol} {name}")
        print(f"      {info}")
    print("=" * 50)
    print(f"  {'PASS ✓' if all_ok else 'FAIL ✗'}\n")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
