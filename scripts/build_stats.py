"""Buduje agregat data/processed/changes.json w schemacie StatsPanel.

Wejście:  data/processed/{region}/changes.json (surowe metryki z run_change_detection.py).
Wyjście:  data/processed/changes.json (per-region: primary/secondary/chart/chartMeta/period).

Zasady uczciwości (decyzje sesji 2026-05-30):
  - Pokazujemy TYLKO realny okres pomiaru (etykiety dat z danych, nie wymyślone "2015–2024").
  - Auto-wykrywanie data-gap: jeśli SSIM ~ 1.0 i change_fraction ~ 0 → źródło bezwartościowe
    (np. Arctic HLS gap, patrz project_arctic_hls_gap) → metryka pomijana, nie zmyślana.
  - Żadnych liczb spoza danych. Brak danej = brak metryki, nie placeholder.
"""

from __future__ import annotations

import json
from pathlib import Path

PROCESSED_DIR = Path("data/processed")
REGIONS = ["amazonia", "dubai", "arctic"]
OUT_PATH = PROCESSED_DIR / "changes.json"

# Sygnatura data-gap: SSIM praktycznie idealny i zero zmian → kafle statyczne/puste.
GAP_SSIM_MEAN = 0.98
GAP_CHANGE_FRACTION = 0.01

# Etykiety NDVI per region — uczciwie nazywają co realnie mierzymy.
NDVI_LABEL = {
    "amazonia": "NDVI (vegetation)",
    "dubai": "NDVI (vegetation)",
    "arctic": "NDVI (snow/ice)",  # nad Svalbardem NDVI to sezon śniegu, nie roślinność
}


def _fmt_month(date: str) -> str:
    """'2025-03-01' → '2025-03'."""
    return date[:7]


def _period(series: list[dict], date_key: str = "date") -> str:
    """Zwraca etykietę okresu 'YYYY-MM – YYYY-MM' z szeregu czasowego."""
    if not series:
        return ""
    first = _fmt_month(series[0].get(date_key) or series[0].get("date_after", ""))
    last = _fmt_month(series[-1].get(date_key) or series[-1].get("date_after", ""))
    return f"{first} – {last}" if first != last else first


def _ssim_is_gap(ssim: dict) -> bool:
    """True gdy SSIM ma sygnaturę data-gap (idealne podobieństwo, zero zmian)."""
    return (
        ssim.get("ssim_mean", 0.0) >= GAP_SSIM_MEAN
        and ssim.get("change_fraction", 1.0) <= GAP_CHANGE_FRACTION
    )


def _pct(value: float, signed: bool = False) -> str:
    """Formatuje ułamek/skalę na procent z minusem (Unicode) zamiast ASCII '-'."""
    p = round(value * 100)
    if signed:
        s = f"{p:+d}%"
    else:
        s = f"{p}%"
    return s.replace("-", "−")  # ASCII hyphen → Unicode minus (spójność z UI)


def _ndvi_chart(ndvi: dict) -> list[dict]:
    """Szereg NDVI → punkty wykresu {t, v}; duplikaty miesięcy uśrednione."""
    by_month: dict[str, list[float]] = {}
    for pt in ndvi.get("series", []):
        m = _fmt_month(pt["date"])
        by_month.setdefault(m, []).append(pt["ndvi_mean"])
    return [{"t": m, "v": round(sum(v) / len(v), 3)} for m, v in sorted(by_month.items())]


def _ssim_chart(ssim: dict) -> list[dict]:
    """Szereg SSIM → punkty wykresu {t, v} (v = change_fraction per okres)."""
    return [
        {"t": _fmt_month(p["date_after"]), "v": round(p["change_fraction"], 3)}
        for p in ssim.get("series", [])
    ]


def build_region(region: str, raw: dict) -> dict | None:
    """Mapuje surowe metryki jednego regionu na blok schematu panelu."""
    ndvi = raw.get("ndvi")
    ssim = raw.get("ssim")

    # Odrzuć SSIM gdy data-gap (np. Arctic HLS)
    ssim_ok = bool(ssim) and not _ssim_is_gap(ssim)
    if ssim and not ssim_ok:
        print(
            f"  [{region}] SSIM odrzucony — sygnatura data-gap "
            f"(mean={ssim['ssim_mean']:.3f}, change={ssim['change_fraction']:.3f})"
        )

    if not ndvi and not ssim_ok:
        print(f"  [{region}] Brak wiarygodnych metryk — pomijam")
        return None

    secondary: list[dict] = []
    chart: list[dict] = []
    chart_meta: dict = {}
    period = ""

    # NDVI istotny tylko gdy zmiana przekracza szum (±2 pkt). Inaczej (np. Dubaj,
    # pustynia) headline'em jest SSIM surface change, a NDVI ląduje w secondary.
    dmean = ndvi["ndvi_mean_diff"] if ndvi else 0.0
    ndvi_significant = bool(ndvi) and abs(dmean) >= 0.02

    ndvi_secondary = None
    if ndvi:
        ndvi_secondary = {
            "label": "veg. loss",
            "value": _pct(ndvi["deforestation_fraction"]),
            "color": "text-red-400",
        }
    ssim_secondary = None
    if ssim_ok:
        ssim_secondary = {
            "label": "surface change",
            "value": _pct(ssim["change_fraction"]),
            "color": "text-orange-400",
        }

    if ndvi_significant or (ndvi and not ssim_ok):
        # primary = NDVI
        trend = "down" if dmean < -0.02 else "up" if dmean > 0.02 else "neutral"
        primary = {
            "value": _pct(dmean, signed=True),
            "label": NDVI_LABEL.get(region, "NDVI"),
            "trend": trend,
        }
        chart = _ndvi_chart(ndvi)
        chart_meta = {"label": NDVI_LABEL.get(region, "NDVI"), "color": "#4ade80"}
        period = _period(ndvi.get("series", []), "date")
        if ssim_secondary:
            secondary.append(ssim_secondary)
    else:
        # primary = SSIM surface change (NDVI nieistotny lub brak)
        primary = {
            "value": _pct(ssim["change_fraction"]),
            "label": "surface change",
            "trend": "up",
        }
        chart = _ssim_chart(ssim)
        chart_meta = {"label": "Surface change", "color": "#fb923c"}
        period = _period(ssim.get("series", []), "date_after")
        if ndvi_secondary:
            secondary.append(ndvi_secondary)

    return {
        "primary": primary,
        "secondary": secondary,
        "chart": chart,
        "chartMeta": chart_meta,
        "period": period,
    }


def main() -> None:
    aggregate: dict = {}
    for region in REGIONS:
        raw_path = PROCESSED_DIR / region / "changes.json"
        if not raw_path.exists():
            print(f"  [{region}] Brak {raw_path} — pomijam")
            continue
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        block = build_region(region, raw)
        if block:
            aggregate[region] = block
            print(
                f"  [{region}] primary={block['primary']['value']} "
                f"{block['primary']['label']} · period={block['period']} "
                f"· chart={len(block['chart'])} pts"
            )

    OUT_PATH.write_text(json.dumps(aggregate, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nZapisano agregat: {OUT_PATH} ({len(aggregate)} regionów)")


if __name__ == "__main__":
    main()
