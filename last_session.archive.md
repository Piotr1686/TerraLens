## ═══ Sesja zarchiwizowana [2026-06-18 22:22] ═══

# last_session.md

Sesja: 2026-06-17 · 22:00-23:18
Status: ✓ Zakończona poprawnie
Punkt odniesienia (git): 2d05d6f @ master

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**T10.5 — paginacja historii S2 w trybie Explore.** Oś czasu sięga wstecz tylko ~2025
(objaw zgłoszony przez Piotra), bo `listScenes()` w `frontend/src/lib/mpc.ts` ma `limit:250`,
co przy ~2 orbitach na punkt daje <2 lata. Dodać paginację STAC (`token`/`next` link z
odpowiedzi `/search`) ALBO strategię „best-per-month" dla głębszej historii do 2015 bez
pobierania tysięcy scen. Potem smoke wizualny: przejazd suwakiem przez wiele lat.

Kontekst: tryb Explore (kaskada NAIP→S2 + oś czasu + przełącznik źródła) wdrożony i zweryfikowany
e2e dziś; to jedyne znane ograniczenie funkcjonalne. MPC search wrócił do działania po przejściowym
outage (504). Reszta T10.5 (cap kamery per-strefa, ESRGAN-dopał) niżej w backlogu.

---

## Co zrobiono w tej sesji

- ✓ **S10 WS3 — Explore Mode wdrożony** (commit `ccea853`) — `lib/mpc.ts` (scene-pick, port z PoC),
  `lib/geocode.ts` (Nominatim), `useExploreLayer.ts`, `SearchBox.tsx`, prop `flyToCoords`+cap zoomu w
  `Globe.tsx`, tryb addytywny w `App.tsx`. tsc+build czyste; STAC POST + tile endpoint zweryfikowane na żywo.
- ✓ **Kaskada źródeł NAIP→S2** (commit `f9d8fd2`) — `resolveScene` (potem `listScenes`): NAIP 0.6 m (USA, z18,
  `assets=image asset_bidx=image|1,2,3`) → fallback S2 10 m (z14, `assets=visual`). Kafle `@2x` retina.
  Cap kamery per źródło. Decyzja: realne>syntetyczne, ESRGAN odłożony. NAIP @2x z18 zweryfikowany (SF, 0.6 m).
- ✓ **Odporność na awarie MPC** (commit `c4caa09`) — NAIP failure → fallback S2; `stacSearch` timeout per
  próba + retry na 504/503; relaks progu chmur; łagodny komunikat błędu. Zdiagnozowany przejściowy outage MPC
  search (504 ~30 s dla wszystkiego, health 200) — degradacja po stronie Microsoftu, nie nasz bug.
- ✓ **Oś czasu + ręczny przełącznik źródła** (commit `a478603`) — `listScenes()` (NAIP 24 + S2 250, bez
  filtra chmur), `useExploreScenes`/`useExploreLayer` (split), `useExploreSelection`, `ExploreControls.tsx`
  (suwak dat, przełącznik NAIP/S2, toggle „Clear skies only" <20% off domyślnie). Listy zweryfikowane na żywo.
- ✓ **MASTER_PLAN** — sprint S10 sformalizowany (T10.3/T10.4 DONE, T10.5 TODO), taksonomia S3 poprawiona
  (Satlas→Real-ESRGAN). MEMORY projektowy + auto-memory zaktualizowane (`project_explore_source_cascade`).

## Co zostało (backlog sesji)

- ⧗ **T10.5 paginacja S2** — patrz NASTĘPNY KROK (oś czasu tylko do ~2025).
- ⧗ **T10.5 pozostałe** — dokładniejszy cap kamery per-strefa, rozbudowane stany empty/error,
  opcjonalny ESRGAN-dopał na kaflach S2 (świadomie odłożony — `project_explore_source_cascade`).
- ⧗ **Smoke wizualny Explore** — przełączanie źródła/dat/filtra na `npm run dev` (SF/Manhattan dla NAIP,
  Dubai dla S2) — częściowo potwierdzone przez Piotra (działa; objaw daty-do-2025 zgłoszony).
- 🟡 **Push** — `master` 9 commitów przed `origin/master` (niezpushowane); Vercel auto-deploy po pushu.

## Aktywne pliki

- `frontend/src/lib/mpc.ts` — `listScenes()` (kaskada NAIP+S2), `stacSearch` (timeout+retry), `@2x`, `lonLatToTile`
- `frontend/src/hooks/useExploreLayer.ts` — `useExploreScenes` (lista) + `useExploreLayer` (warstwa z wybranej sceny)
- `frontend/src/hooks/useExploreSelection.ts` — stan: źródło/filtr chmur/index daty
- `frontend/src/components/ExploreControls.tsx` — suwak dat + przełącznik źródła + toggle chmur
- `frontend/src/components/SearchBox.tsx`, `frontend/src/lib/geocode.ts` — wyszukiwarka (Nominatim)
- `frontend/src/App.tsx`, `frontend/src/components/Globe.tsx` — wpięcie trybu Explore (addytywne)

## Otwarte pytania

- Paginacja S2 vs best-per-month dla głębi historii (>250 scen) — która strategia (T10.5)?
- ESRGAN-dopał na S2 poza USA — czy w ogóle (świadomie odłożony, real 10 m może wystarczyć)?
- Geocoder: Nominatim wystarczy na demo, czy managed przy większym ruchu?

## Do MEMORY.md (przeniesiono)

- [2026-06-17] S10 Explore FRONTEND wdrożony — kaskada NAIP→S2 + oś czasu + przełącznik źródła, zero-backend,
  `@2x` retina, odporność na 504 MPC, ograniczenie limit:250. Wpis w projektowym MEMORY.md (Architektura).
- `project_explore_source_cascade` (auto-memory) — decyzja: realne źródło per lokalizacja, ESRGAN odłożony.

## ═══ Sesja zarchiwizowana [2026-06-17 23:18] ═══

# last_session.md

Sesja: 2026-06-16 · 19:00-22:00
Status: ✓ Zakończona poprawnie
Punkt odniesienia (git): 198db31 @ master

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**S10 Workstream 3 — Frontend Explore Mode (ZERO-BACKEND).** Zacznij od `frontend/src/lib/mpc.ts`:
port logiki scene-pick z `scripts/poc_sentinel2.py` do TS — STAC `POST /api/stac/v1/search`
(`collections=[sentinel-2-l2a]`, filtr `eo:cloud_cover`, wybór min cloud + świeża) → zwróć `itemId`;
plus helper budujący URL kafla `…/api/data/v1/item/tiles/WebMercatorQuad/{z}/{x}/{y}@1x.png?collection=sentinel-2-l2a&item=<id>&assets=visual`.
Potem: `SearchBox.tsx` (Nominatim), `useSentinelLayer.ts` (deck.gl `TileLayer`, mirror `Globe.tsx:85-97`),
tryb Explore w `App.tsx`/`Globe.tsx` (addytywny, cap zoomu street-level). Kandydat na `/sonnet`.

Kontekst: PoC S2 udany (10 m street-level), CORS `*` na STAC + tile endpoint potwierdzony → backend
NIEpotrzebny (front woła MPC bezpośrednio). Architektura w planie:
`C:\Users\plazo\.claude\plans\joyful-twirling-nova.md`.

---

## Co zrobiono w tej sesji

- ✓ **ESRGAN-w-PMTiles WDROŻONY** (commit `1088c52`) — `process` (+`--date`), `export` (+`--sr`).
  Render 52 kafle 2048² SR (amazonia z6+z7, 2023-07-01) → `amazonia_v20260616_190200.pmtiles` (14 MB)
  → deploy HF. Zweryfikowane e2e: kafel z7 z HF = 2048² SR. **Domyka lukę AI/ML dla amazonii.**
- ✓ **Skan zachmurzenia** (commit `198db31`, `scripts/scan_cloud_cover.py`) — 2023-07-01 to obiektywnie
  najczystsza data amazonii (cloud_frac 0.219). Rozpoznano sufit Architektury A (z7 ≈120 m/px); „brak
  różnicy" na prod = lokalny cache przeglądarki (ścieżka HF→SR zweryfikowana jako poprawny SR).
- ✓ **/architect S10 + pivot na Sentinel-2** — architektura zatwierdzona (MPC hostowany tiler).
- ✓ **PoC Sentinel-2 UDANY** (commit `198db31`, `scripts/poc_sentinel2.py`) — scena 0.0% chmur, kafel
  pctiler `assets=visual`, ostrość 10 m (Dubai street-level). SSL: `pystac` hardkoduje `verify=True`
  → fix env `REQUESTS_CA_BUNDLE`=`win-ca-bundle.pem`.
- ✓ **Backend rozstrzygnięty = ZERO-BACKEND** — Cloudflare odpadł (brak konta), ale zbędny: tiler MPC
  publiczny + STAC/data-API `ACAO: *` → front woła MPC bezpośrednio.
- ✓ **MEMORY** zaktualizowany: wpis [2026-06-16] (SR + pivot S2 + zero-backend + niuans SSL pystac).

## Co zostało (backlog sesji)

- ⧗ **S10 WS3 frontend** — `lib/mpc.ts` + `SearchBox` + `useSentinelLayer` + tryb Explore (patrz NASTĘPNY KROK).
- ⧗ **S10 WS4 polish** — picker daty/cloud, atrybucja Sentinel-2/MPC, cap zoomu kamery, stany błędu/empty.
- ⧗ **Formalizacja S10 w MASTER_PLAN.md** — nie ma jeszcze sprintu S10; taksonomia S3 używa starej nazwy
  „Satlas" (pivot na Real-ESRGAN + S2 nieodzwierciedlony). Do uporządkowania przy starcie WS3.
- ⧗ **Follow-up SR dubai+arctic** (opcjonalnie — ten sam wzorzec; arctic = MODIS_Terra dla lat≥70).

## Aktywne pliki

- `scripts/poc_sentinel2.py` — PoC S2 (scene-pick + tile URL); **baza do portu** `frontend/src/lib/mpc.ts`
- `scripts/scan_cloud_cover.py` — ranking dat wg zachmurzenia (reuse dla dubai/arctic)
- `frontend/src/components/Globe.tsx` — `makeTileLayer` (`:85-97`, mirror dla `useSentinelLayer`); `controller` free-zoom
- `frontend/src/App.tsx` — miejsce na tryb Explore (addytywny do hooka 3-regionowego)
- (do powstania) `frontend/src/lib/mpc.ts`, `components/SearchBox.tsx`, `hooks/useSentinelLayer.ts`

## Otwarte pytania

- Geocoder: Nominatim (ToS ≤1 req/s) wystarczy na demo, czy od razu managed (Photon/Mapbox)?
- ESRGAN SR jako opcjonalny dopał na kaflach S2 — czy w ogóle potrzebny przy realnym 10 m?
- Cap zoomu kamery dla street-level — jaki maxZoom GlobeView dla S2 z14?

## Do MEMORY.md (przeniesiono)

- [2026-06-16] SR wdrożony (`1088c52`) + pivot S2/S10 (MPC, PoC udany, params `assets=visual` zapinowane,
  zero-backend bo CORS `*` + tiler publiczny) + niuans SSL `pystac` (`verify=True` → `REQUESTS_CA_BUNDLE`).
  Wpis w projektowym MEMORY.md, sekcja Architektura.

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
