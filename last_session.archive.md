## ═══ Sesja zarchiwizowana [2026-06-16 22:00] ═══

# last_session.md

Sesja: 2026-06-16 · w toku (checkpoint)
Status: ⟳ W toku
Punkt odniesienia (git): eb0d3e9 @ master → teraz: 1088c52

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**S10 Workstream 3 — Frontend Explore Mode (ZERO-BACKEND, decyzja podjęta).** Backend nie jest
potrzebny: tiler MPC publiczny + STAC/data-API mają `ACAO: *` → front woła MPC bezpośrednio.
Do zrobienia:
- `frontend/src/lib/mpc.ts` — scene-pick (STAC `POST /search`, min cloud) + budowa tile URL (port z `poc_sentinel2.py`).
- `frontend/src/components/SearchBox.tsx` — Nominatim geocoding → AOI + fly.
- `frontend/src/hooks/useSentinelLayer.ts` — deck.gl `TileLayer` (mirror `Globe.tsx:85-97`).
- `App.tsx`/`Globe.tsx` — tryb Explore (addytywny), cap zoomu street-level.
Kandydat na `/sonnet` (mirror istniejących wzorców; scene-pick chwilę na HIGH przy porcie do TS).
📋 Plan: `C:\Users\plazo\.claude\plans\joyful-twirling-nova.md`

Kontekst: PoC Sentinel-2 udany (10 m street-level potwierdzone). Źródło MPC zwalidowane, parametry
zapinowane (`assets=visual`), CORS `*` potwierdzony na STAC + tile endpoint. Backend ODPADŁ — zero ops.

---

## Co zrobiono w tej sesji

- ✓ **ESRGAN-w-PMTiles WDROŻONY** (commit `1088c52`) — `process` (+`--date`), `export` (+`--sr`).
  Render 52 kafle 2048² SR (amazonia z6+z7, 2023-07-01) → `amazonia_v20260616_190200.pmtiles` (14 MB)
  → deploy HF. Zweryfikowane e2e: kafel z7 z HF = 2048² SR. **Domyka lukę AI/ML dla amazonii.**
- ✓ **Skan zachmurzenia** (`scripts/scan_cloud_cover.py`) — 2023-07-01 to obiektywnie najczystsza data
  amazonii (cloud_frac 0.219); re-render innej daty bezcelowy. Rozpoznano sufit Architektury A (z7 ≈120 m/px)
  i potwierdzono, że „brak różnicy" na prod = lokalny cache przeglądarki (ścieżka HF→SR poprawna).
- ✓ **/architect S10 — architektura ZATWIERDZONA** (Wariant A: MPC + cienki backend on-demand).
  Pivot na Sentinel-2 10 m / dowolny obszar. Front reużyje deck.gl `TileLayer` (kamera już ma free-zoom).
- ✓ **PoC Sentinel-2 UDANY** (`scripts/poc_sentinel2.py`) — STAC `sentinel-2-l2a` → scena 0.0% chmur →
  kafel pctiler `assets=visual` (TCI), ostrość 10 m potwierdzona (Dubai street-level). SSL: `pystac`
  hardkoduje `verify=True` → fix env `REQUESTS_CA_BUNDLE`=`win-ca-bundle.pem`.
- ✓ **MEMORY** projektowy zaktualizowany: wpis [2026-06-16] (SR wdrożony + pivot S2 + niuans SSL pystac).

## Co zostało (backlog sesji)

- ⛔ **S10 backend BEZ Cloudflare** (zmiana decyzji — brak konta) — Vercel Function vs front-direct-MPC.
  → patrz NASTĘPNY KROK.
- ⧗ **S10 WS3 frontend** — `SearchBox` (Nominatim) + `useSentinelLayer` (TileLayer→backend); tryb addytywny.
- ⧗ **S10 WS4 polish** — picker daty/cloud, atrybucja, cap zoomu, stany błędu.
- ⧗ **Follow-up SR dubai+arctic** (opcjonalnie — ten sam wzorzec; arctic = MODIS_Terra dla lat≥70).
- 🧹 **Pliki untracked do decyzji:** `scripts/poc_sentinel2.py`, `scripts/scan_cloud_cover.py` (commit?).

## Aktywne pliki

- `scripts/poc_sentinel2.py` — PoC S2 (MPC scene-pick + pctiler tile); baza logiki scene-pick dla WS2
- `scripts/scan_cloud_cover.py` — ranking dat wg zachmurzenia (reuse dla dubai/arctic)
- `src/terralens/__main__.py` — `process --date` + `export --sr` (DONE tej sesji, commit `1088c52`)
- `frontend/src/components/Globe.tsx` — `makeTileLayer` (`:85-97`, mirror dla `useSentinelLayer`); `controller` free-zoom
- `frontend/src/App.tsx` — miejsce na tryb Explore (addytywny do hooka 3-regionowego)
- (nowe, do powstania w WS2/WS3) backend on-demand + `SearchBox.tsx` + `useSentinelLayer.ts`

## Otwarte pytania

- ✓ ROZSTRZYGNIĘTE: S10 backend = **zero-backend** (MPC tiler publiczny + CORS `*`); front-direct.
- Geocoder: Nominatim (ToS ≤1 req/s) wystarczy na demo, czy od razu managed?
- ESRGAN SR jako opcjonalny dopał na kaflach S2 — czy w ogóle potrzebny przy realnym 10 m?

## Do MEMORY.md (przeniesiono)

- [2026-06-16] SR wdrożony (commit `1088c52`) + pivot S2/S10 (MPC, PoC udany, params zapinowane) +
  niuans SSL `pystac` (`verify=True` hardcoded → `REQUESTS_CA_BUNDLE`). Wpis dodany do projektowego MEMORY.md.

## ═══ Sesja zarchiwizowana [2026-06-15 22:40] ═══

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
