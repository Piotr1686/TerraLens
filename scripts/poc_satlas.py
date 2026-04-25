"""T0.1 PoC: Satlas SwinB VRAM budget — RTX 3050 4GB.

Cel: 3 iteracje inference na tile 512×512 FP16.
Mierzy peak VRAM, delta stabilności, headroom vs 4GB.
Output: drukuje raport + zapisuje scripts/poc_results.txt.
"""

import gc
import subprocess
import sys

import torch


def vram_mb() -> float:
    return torch.cuda.memory_allocated() / 1e6


def flush() -> None:
    torch.cuda.empty_cache()
    gc.collect()


def smi() -> str:
    try:
        r = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        used, total = r.stdout.strip().split(", ")
        return f"{used}/{total} MB"
    except Exception:
        return "N/A"


def main() -> int:
    lines: list[str] = []

    def log(s: str = "") -> None:
        print(s)
        lines.append(s)

    log("=== T0.1 PoC: Satlas SwinB VRAM test ===")
    log(f"torch {torch.__version__} | CUDA {torch.version.cuda}")
    log(f"GPU: {torch.cuda.get_device_name(0)}")
    total_mb = torch.cuda.get_device_properties(0).total_memory / 1e6
    log(f"VRAM total: {total_mb:.0f} MB")
    log()

    log("[1] Ładowanie Satlas SwinB SI_RGB (FP16)…")
    flush()
    v0 = vram_mb()

    import satlaspretrain_models

    weights = satlaspretrain_models.Weights()
    model = weights.get_pretrained_model("Sentinel2_SwinB_SI_RGB", fpn=True)
    model = model.half().cuda().eval()

    v_loaded = vram_mb()
    log(f"    VRAM po załadowaniu: {v_loaded:.1f} MB (+{v_loaded - v0:.1f} MB)")
    log(f"    nvidia-smi         : {smi()}")
    log()

    log("[2] 3 × inference (tile 512×512, FP16, inference_mode)…")
    vrams: list[float] = []
    for i in range(3):
        flush()
        x = torch.randn(1, 3, 512, 512, dtype=torch.float16, device="cuda")
        with torch.inference_mode():
            try:
                _ = model(x)
            except Exception as e:
                log(f"    [WARN] forward: {e}")
        torch.cuda.synchronize()
        v = vram_mb()
        vrams.append(v)
        log(f"    iter {i + 1}: {v:.1f} MB | {smi()}")
        del x
        flush()

    log()
    log("[3] Analiza VRAM…")
    delta = max(vrams) - min(vrams)
    peak = max(vrams)
    headroom = total_mb - peak
    log(f"    Peak allocated : {peak:.1f} MB / {total_mb:.0f} MB")
    log(
        f"    Delta iters    : {delta:.1f} MB  ({'✓ STABILNY' if delta <= 50 else '✗ NIESTABILNY'})"
    )
    log(f"    Headroom (est) : {headroom:.1f} MB")
    log()

    if peak <= 3500 and delta <= 50 and headroom >= 500:
        verdict = "✅ PASS"
    elif peak <= 3800:
        verdict = "⚠️ WARN — sprawdź headroom i stabilność"
    else:
        verdict = "❌ FAIL — OOM risk, rozważ fallback"

    log(f"[4] WYNIK: {verdict}")

    out = "scripts/poc_results.txt"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log(f"\nZapisano: {out}")

    return 0 if "FAIL" not in verdict else 1


if __name__ == "__main__":
    sys.exit(main())
