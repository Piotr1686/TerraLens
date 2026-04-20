"""Weryfikacja T0.2: torch + CUDA + satlas na RTX 3050 Laptop 4GB."""

import sys


def main() -> int:
    # Importy wewnątrz funkcji — chcemy raportować konkretny błąd,
    # a nie crashować cały skrypt gdy brakuje któregoś pakietu.
    errors: list[str] = []

    try:
        import torch
    except ImportError as e:
        print(f"[FAIL] torch import: {e}")
        return 1

    try:
        import satlaspretrain_models  # noqa: F401

        satlas_ok = True
    except ImportError as e:
        errors.append(f"satlaspretrain_models import: {e}")
        satlas_ok = False

    cuda_ok = torch.cuda.is_available()
    gpu = torch.cuda.get_device_name(0) if cuda_ok else "?"

    print(f"torch     : {torch.__version__} (CUDA runtime {torch.version.cuda})")
    print(f"CUDA avail: {cuda_ok}")
    print(f"GPU       : {gpu}")
    print(f"satlas    : {'ok' if satlas_ok else 'FAIL'}")

    if not cuda_ok:
        errors.append("torch.cuda.is_available() == False")

    if errors:
        print("\n[FAIL]")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("\n[OK] T0.2 verification passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
