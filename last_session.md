# last_session.md

Sesja: 2026-06-15 · checkpoint 22:35
Status: ⟳ Zaparkowana — ESRGAN-w-PMTiles zaplanowany, NIE rozpoczęty (kod nietknięty)
Punkt odniesienia (git): f46186f @ master

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**ESRGAN-w-PMTiles — plan ZATWIERDZONY, czeka na wykonanie.**
📋 Pełny plan: `C:\Users\plazo\.claude\plans\serialized-plotting-twilight.md`

Zadanie: kafle HLS_RGB na globie to nadal surowy GIBS, nie SR. `process` liczy Real-ESRGAN 4×
do `tiles/{layer}_SR/`, ale `export` ma na sztywno `tile_dir = tiles/{layer}` (`__main__.py:249`)
i nigdy nie tyka `_SR`. **Uwaga: render SR praktycznie niezrobiony** (ostatnia data: raw z7=135
kafli, `_SR`=1 — próbka PoC) → to realny render GPU + podłączenie.

Decyzje już podjęte (w planie):
- **Architektura A** — 2048² SR w tych samych slotach z6/z7; FRONT BEZ ZMIAN (manifest-driven URL
  `App.tsx:84-89` + per-tile BitmapLayer z pełnej tekstury). Wariant B (pyramid z8/z9) = follow-up.
- **Pilot: amazonia** najpierw, potem dubai+arctic.
- Kod: tylko `__main__.py` — `process` (+`--date`, by SR-ować tylko snapshot, nie 19 dat) i
  `export` (+`--sr`, źródło `_SR`). Reszta (`build_pmtiles`, scan, deploy, manifest) bez zmian.
- Start od kroku 3 planu: `process --region amazonia --zoom 6,7 --date <najnowsza>` (env
  `terralens`, `PYTHONIOENCODING=utf-8`, RTX 3050 ~kilka min) → `export --sr` → `deploy`.

Alternatywy odłożone: **Sprint S10 Explore Mode**; **więcej historii HLS_RGB** (multi-year wykres).

⚠️ **Gotcha deploy (zaktualizowana obserwacja):** w tej sesji auto-promocja Vercela ZADZIAŁAŁA
w pełni — po pushu nowy deploy (`terra-lens-9eh9a4uis`) sam przejął WSZYSTKIE aliasy, w tym
`terra-lens-zeta` (`vercel promote` zwrócił 409 „already current production"). Czyli historyczny
problem z ręcznym `alias set` już nie blokuje. Nadal: weryfikuj hash bundla prod (nie tylko push);
`vercel`/`NODE_EXTRA_CA_CERTS` = `%TEMP%\win-ca-bundle.pem` (regenerowalny z `Cert:\LocalMachine\Root`).

---

## Co zrobiono w tej sesji

- ✓ **Sanity baseline:** rozwiązano desync po migracji session-systemu v0.2 — przejrzano 3
  niecommitowane pliki (Vercel ignore, allowlista uprawnień, ref-point), potwierdzono BRAK
  regresji `bug_vercel_stale_deploy_gitignore` (`/data/` nadal zakotwiczony). Commit `bb31059`.
- ✓ **CVA realne heatmapy** (commit `f46186f`) — domknięcie CAŁEJ warstwy heatmap:
  - `build_region_cva_heatmaps()` w `build_heatmaps.py`: ΔE w LAB (`compute_cva`) z tych samych
    tile'ów HLS_RGB co SSIM (z=7), cloud-masking (chmura→NaN), próg percepcji ΔE<10→przezroczyste,
    colormap `plasma`. Render: amazonia 49, dubai 1, arctic 81 tile.
  - `__main__.py`: `("cva_heatmap","cva_heatmap")` w `deploy-heatmaps`.
  - `useHeatmapLayer.ts`: `cva` w `REAL_METRICS` (z=7); usunięty martwy fallback demo GIBS
    (import `TileLayer`, `GIBS_*`/`DEMO_DATE`, nieosiągalna gałąź `useMemo`).
- ✓ **Weryfikacja end-to-end:** ruff + `tsc -b` czyste; CVA na HF (HEAD 200 amazonia+arctic);
  push → auto-build ● Ready 12s; prod bundle `index-Doe-l8SI.js`: `cva_heatmap=1`, `Bands721=0`.
- ✓ **MEMORY:** zaktualizowany `project_intelligence_layer_gap` (heatmap layer kompletna) + index.
- ✓ **ESRGAN-w-PMTiles — rozpoznanie + plan ZATWIERDZONY** (nie wykonany; kod nietknięty).
  Prześledzono pełny pipeline (process→export→deploy→front), zlokalizowano lukę
  (`export __main__.py:249` na sztywno na surowym GIBS), wykryto że render SR to próbka PoC
  (1/135 kafli). Decyzje: Architektura A + pilot amazonia. Plan: `serialized-plotting-twilight.md`.

## Co zostało (backlog sesji)

- ⏳ **ESRGAN-w-PMTiles** — ZAPLANOWANE, do wykonania w następnej sesji (patrz NASTĘPNY KROK + plan).
- ⧗ **Sprint S10 — Explore Mode** (search Nominatim + free-zoom + Sentinel-2) — decyzja
  architektoniczna (backend on-demand: Cloudflare Worker vs Vercel Function; źródło S2).
- ⧗ **Więcej historii HLS_RGB** (multi-year) dla głębszego wykresu SSIM/CVA.
- 🧹 **Opcjonalnie:** posprzątać sprzeczne `buildCommand`/`outputDirectory` w dashboardzie Vercela
  (nie blokuje — `frontend/vercel.json` nadpisuje).

## Aktywne pliki

- `scripts/build_heatmaps.py` — dodana `build_region_cva_heatmaps()` (CVA render)
- `src/terralens/__main__.py` — `deploy-heatmaps`: metryka cva_heatmap
- `frontend/src/hooks/useHeatmapLayer.ts` — CVA w REAL_METRICS, usunięty demo fallback
- `src/terralens/processors/cva.py` — źródło ΔE LAB (reużyte, bez zmian)

## Otwarte pytania

- ESRGAN-w-PMTiles teraz, czy najpierw S10 Explore Mode? (większy wow vs większy zasięg)
- Sprint S10: backend on-demand (Cloudflare Worker vs Vercel Function) + źródło Sentinel-2?
- Posprzątać sprzeczne ustawienia build w dashboardzie Vercela? (opcjonalne)

## Do MEMORY.md (przeniesiono)

- `project_intelligence_layer_gap` — warstwa heatmap KOMPLETNA (SSIM+CVA+NDVI realne, demo GIBS
  usunięte), [2026-06-15] wpis o CVA (commit `f46186f`); index zaktualizowany.
