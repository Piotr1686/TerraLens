# MEMORY.md — Długoterminowa pamięć projektu TerraLens

> Ten plik kumuluje wiedzę o projekcie. Nigdy nie usuwaj wpisów — tylko dopisuj.
> Każdy wpis oznaczaj datą w formacie [YYYY-MM-DD].

---

## Architektura

<!-- Claude dopisuje tutaj decyzje architektoniczne wraz z uzasadnieniem -->

### [2026-06-04] Realne heatmapy SSIM — raw PNG (4326) + multi-BitmapLayer, NIE TileLayer

- **Problem:** `useHeatmapLayer.ts` serwował heatmapy jako proxy GIBS (LST jako „SSIM") przez deck.gl `TileLayer`. Realne mapy SSIM z change detection były niepodłączone (flaga `pmtilesAvailable` nigdy true). Produkcyjny URL `{region}_{metric}_heatmap/{z}/{x}/{y}.png` w `TileLayer` i tak by nie zadziałał — TileLayer używa siatki Web Mercator, a pipeline produkuje indeksy GIBS EPSG:4326 (mismatch, patrz wpis [2026-05-12] PMTiles overlay).
- **Decyzja:** Render realnych map `1 - SSIM` (colormap inferno, NaN→alpha 0) per tile dla pary first-vs-last, serwowanych jako **raw PNG** z HF i renderowanych **manualnie multi-BitmapLayer w natywnych bounds 4326** — ten sam wzorzec co `usePMTilesLayer` (iteracja (x,y) z bbox regionu, macierz 160×80 przy z=7). NIE `TileLayer` (Web Mercator). Raw PNG zamiast PMTiles: pełny mały kafel nie potrzebuje Range/redirect-fix, prostszy deploy (`upload_folder`).
- **Implementacja:** render `scripts/build_heatmaps.py` (reużywa helperów `run_change_detection.py` + `export_heatmap()` z `ssim.py`); deploy `terralens deploy-heatmaps` → `deploy_folder()` (`export/deploy.py`, `HfApi.upload_folder`) jako `{region}_ssim_heatmap/{z}/{x}/{y}.png`; front `useHeatmapLayer.ts` (`metric=ssim` → realne PNG, zwraca `Layer[]`). Commit `6991cd9`.
- **Semantyka:** zmiana strukturalna = jasny/gorący piksel; brak zmiany (SSIM≈1) = ciemny; chmury/brak danych = przezroczyste. Arctic ~pusty (HLS gap, [[project_arctic_hls_gap]]) — uczciwie, bo brak realnej zmiany.
- **Zakres:** Dotyczy tylko SSIM. NDVI/CVA pozostają demo GIBS (brak realnych map w pipeline). Domyka kolejny kawałek [2026-05-29] luki AI/ML (heatmapy przestają być proxy).
- **Niezweryfikowane wizualnie:** kod wiernie odwzorowuje sprawdzony `usePMTilesLayer`, typecheck+build zielone, dane live na HF (200), ale render na globie nie był obejrzany w przeglądarce — pierwszy smoke po Vercel auto-deploy.

### [2026-05-30] Pivot silnika SR: Satlas (martwy) → Real-ESRGAN RRDBNet x4 (zwendorowany)

- **Problem:** `engines/satlas_esrgan.py` (SwinB backbone + dekoder) był **martwy** — dekoder miał losowe wagi (brak wytrenowanego `satlas_esrgan_x4.pt`), więc `upscale()` produkował **czarne kafle**. Próba naprawy (dodanie SSL-patch dla pobierania wag SwinB z HF) nie rozwiązywała sedna — brak wytrenowanego dekodera SR.
- **Decyzja:** Zastąpienie silnikiem **Real-ESRGAN RRDBNet x4** (`engines/realesrgan.py`). Architektura RRDBNet **zwendorowana ręcznie** (RDB → RRDB → RRDBNet) — celowo BEZ zależności od `basicsr`, bo `basicsr` importuje usunięte `torchvision.transforms.functional_tensor` → crash na `torchvision>=0.17`.
- **Wagi:** `data/models/RealESRGAN_x4plus.pth` (~64 MB), auto-download z GitHub releases (`xinntao/Real-ESRGAN/v0.1.0`) przy pierwszym `load()`, `verify=False` (Windows cert, patrz [[feedback_windows_ssl]]). Wagi pod kluczem `params_ema` (fallback `params` → surowy dict).
- **Interfejs zachowany 1:1:** `load/unload/is_loaded/upscale` + `get_esrgan/reset_esrgan` — `process` w `__main__.py` wymagał tylko zmiany importu. `satlas_esrgan.py` ZOSTAJE w repo wyłącznie jako źródło stałej `SCALE` dla `processors/tiled.py` (nie jest już instancjonowany w produkcie).
- **Regresja zabezpieczona:** `test_upscale_not_black` (`tests/test_realesrgan.py`) — asercja `result.max() > 0.05`, pilnuje że silnik nie wróci do produkcji czarnych kafli. 10/10 testów zielone (integracyjne CUDA potwierdziły realny, nie-czarny output).
- **Produkt:** split-slider raw↔SR ożywia tę funkcję w UI — `SuperResPanel.tsx` (clip-path before/after), pokazany przy `arrivedRegion` z gotowymi parami demo w `public/sr-demo/` (dubai 512→2048). Częściowo domyka [[project_intelligence_layer_gap]] (warstwa AI/ML wreszcie widoczna w produkcie).

### [2026-05-12] Decyzja projektowa: target high-resolution + search dowolnego obszaru

- **Zmiana skali wizji:** TerraLens nie ogranicza się do 3 predefiniowanych regionów (Amazonia/Dubai/Arctic). Docelowo user może **przybliżyć dowolny punkt globu do dobrej rozdzielczości** (street-level / sub-100m) oraz **wyszukać interesujący go obszar** (search bar / klik na globusie).
- **Konsekwencje priorytetyzacji:** Sprint S0 T0.1 **Satlas ESRGAN** awansuje na high-priority (był blokujący per MASTER_PLAN, ale jego brak nie blokował MVP). 4× upscaling MODIS 250m → ~60m efektywne jest niezbędny do "wow" przy zoom-in. Wyższy priorytet niż `changes.json` upload, niż cleanup demo plików.
- **Multi-zoom pipeline:** `__main__.py` `zoom` parameter musi obsługiwać listę (z6+z7+z8 minimum, ideal: z6-z8). Archiwa rosną z 10 MB → ~50 MB per region — user akceptuje.
- **Multi-zoom frontend:** `usePMTilesLayer` musi przestać hardcodować `GIBS_ZOOM=6` — wybierać zoom poziom na podstawie viewport zoom kamery. Per [[2026-05-12 PMTiles overlay]] wpis poniżej.
- **Search architektura:** Dla dowolnego bbox (nieznany z góry) PMTiles może być nieaplikable — bbox nie istnieje jako pre-built archive. Opcje: (a) bezpośredni GIBS fetch on-demand, (b) globalny PMTiles z lazy tile load, (c) osobny tile server. Decyzja deferred — odkryje się przy implementacji.
- **Anti-pattern:** Rezygnacja z głębokości zoomu "bo MVP wystarczy". MVP może być na 3 regionach, ale jakość per region docelowo street-level.

### [2026-05-12] PMTiles overlay — coordinate system bridge GIBS EPSG:4326 ↔ deck.gl WebMercator

- **Problem fundamentalny:** Pipeline Python (`gibs.py`) fetchuje tile'y z GIBS endpoint `epsg4326/best` z tilematrixsetem `250m` — **niestandardowa siatka 80×40 przy z=6** (per [[2026-05-03 GIBS EPSG:4326 — niestandardowe TileMatrix dimensions]]). Frontend deck.gl `TileLayer` natomiast wysyła zapytania w **WebMercator OSM scheme 64×64 przy z=6**. (z,x,y) indices się NIE odpowiadają — sąsiedni `archive.getZxy(z,x,y)` z błędnymi indeksami zwracał null lub tile z innego obszaru geograficznego.
- **Próby fix które NIE działały:**
  1. Translacja WebMercator center → najbliższy GIBS tile + render przy GIBS bounds: tile'y MIAŁY się renderować, ale rozmiary 4.5° (GIBS) vs 5.625° (Mercator) różne → wizualne luki/overlap/przesunięcia
  2. `minZoom: 6, maxZoom: 6` na TileLayer: deck.gl prosił dobry zoom level ale nadal w schemacie WebMercator — niedopasowanie x/y dalej istniało
- **Co działa (fix):** Pominięcie `TileLayer` w ogóle. Hook bezpośrednio iteruje `(x, y)` w GIBS 4326 indices dla bbox regionu, fetch wszystkich tile'ów równolegle przez `archive.getZxy(6, x, y)`, returns `Layer[]` of `BitmapLayer` — każdy renderowany przy swoich natywnych bounds 4.5°×4.5° z `COORDINATE_SYSTEM.LNGLAT`. ~15 tile'ów per region (Amazonia 5×3), 1 fetch przy `arrivedRegion` change, cached w `archiveCache`.
- **Implementacja:** `frontend/src/hooks/usePMTilesLayer.ts` (commit `7f04504`).
- **Reguła:** Dla PMTiles z pipeline EPSG:4326 — **nie używać deck.gl `TileLayer`**. Iterować ręcznie + multi-BitmapLayer. To anty-wzorzec vs [[2026-05-08 deck.gl TileLayer + GIBS]] który dotyczył **live GIBS endpoint** (tam epsg3857 jest dostępne); PMTiles archiwum ma już zaszyte 4326 indices i nie da się tego "naprawić" frontend-side.
- **TODO architektoniczne:** Aby uprościć w przyszłości, można:
  - Przepisać pipeline na GIBS `epsg3857` endpoint (cleaner, ale wymaga re-fetch wszystkich tile'ów NASA)
  - Lub zostawić current bridge i traktować go jako stałe rozwiązanie

### [2026-05-12] HF CDN — 302 redirect gubi Range headers, HEAD resolveRedirect workaround

- **Objaw:** `pmtiles.js` używa HTTP Range requests do pobierania kawałków archiwum (cała idea formatu). HuggingFace `/datasets/{user}/{repo}/resolve/main/{file}.pmtiles` URL zwraca **302 redirect do `cas-bridge.xethub.hf.co`** (CDN LFS). Przeglądarka po redirect **dropuje nagłówek `Range`** — finalny request idzie bez Range, CDN zwraca pełny plik (lub failuje).
- **Fix:** Hook `usePMTilesLayer` przed użyciem URL wywołuje `resolveRedirect(url)` — HEAD request z `redirect: 'follow'`, capture `response.url` (final CDN URL po redirect). Następnie `new PMTiles(resolvedUrl)` z bezpośrednim CDN URL — bez kolejnego redirect, Range headers przechodzą.
- **Cache:** `redirectCache: Map<string, string>` — resolveRedirect wywoływane raz per URL (signed AWS params w CDN URL nie odświeżamy w obrębie sesji; po expiration usera trzeba przeładować).
- **Scope:** Dotyczy każdego fetch'a do HF `/resolve/main/` z biblioteki która polega na Range requests. PMTiles tak, ale też np. własne IndexedDB fragmentowane fetche. Zwykłe `fetch(url).json()` bez Range — nie dotyczy (przeglądarka obsługuje redirect transparentnie).
- **Implementacja:** `frontend/src/hooks/usePMTilesLayer.ts` `resolveRedirect()` (commit `7f04504`).

### [2026-05-08] deck.gl TileLayer + GIBS: używać TYLKO epsg3857 (GoogleMapsCompatible)

- **Przyczyna błędu "kafelki w złym miejscu":** `deck.gl TileLayer` używa **OSM/Web Mercator tile scheme** (z=0 → 1 kafelka, z=4 → 16×16 kafelki) nawet w `_GlobeView`. Tymczasem GIBS `epsg4326` używa **własnych tile dimensions** (z=4 → 20×10 kafelki). Mismatched indices → GIBS serwuje kafelkę z innego obszaru geograficznego, deck.gl renderuje ją w złym miejscu.
- **Fix:** Używać zawsze `epsg3857/best` z tilematrixset `GoogleMapsCompatible_Level{N}`:
  - 250m layers (NDVI, TrueColor, Bands721) → `GoogleMapsCompatible_Level9`, ext `.png`/`.jpg`
  - 500m layers (Blue Marble) → `GoogleMapsCompatible_Level8`, ext `.jpg`
  - 1km layers (LST) → `GoogleMapsCompatible_Level7`, ext `.png`
- **Znane ograniczenie:** GIBS epsg3857 zwraca **blank tile przy zoom=0** (known GIBS bug). Ustawić `minZoom: 1` w TileLayer.
- **Distorsja:** Web Mercator tiles mają zniekształcenia przy wysokich szerokościach (Arctic 72°N = 3-4× stretch). Geograficznie poprawne, wizualnie akceptowalne dla demo.
- **NIE używać:** `epsg4326` z deck.gl TileLayer — zawsze błędne tile placement przy zoom ≥ 3.

### [2026-05-06] GlobeView BitmapLayer seam fix — _imageCoordinateSystem: COORDINATE_SYSTEM.LNGLAT

- **Problem:** `TileLayer` + `BitmapLayer` w `_GlobeView` bez `_imageCoordinateSystem` → czarne kliny/szwy między kafelkami, glob wygląda jak rozcięta pomarańcza.
- **Fix:** Dodać `_imageCoordinateSystem: COORDINATE_SYSTEM.LNGLAT` do każdego `BitmapLayer` wewnątrz `renderSubLayers` zarówno w `Globe.tsx` jak i `useHeatmapLayer.ts`.
- **Import:** `import { COORDINATE_SYSTEM } from '@deck.gl/core'`
- **Scope:** Dotyczy KAŻDEGO `TileLayer+BitmapLayer` w GlobeView — bez tego sfera wygląda jak kopuła z pasami.

### [2026-05-06] GlobeView ScatterplotLayer/TextLayer — bug pozycjonowania w deck.gl 9.3.1

- **Problem:** `ScatterplotLayer` i `TextLayer` renderują punkty w ZŁYCH geograficznych pozycjach w `_GlobeView`. Markery "przebijają" sferę lub lądują w zupełnie innym miejscu niż [longitude, latitude]. Bug pre-existing — nie do naprawienia przez `coordinateSystem: COORDINATE_SYSTEM.LNGLAT`, `farZMultiplier`, zoom, ani hemisphere culling filter.
- **Próby:** explicit `coordinateSystem`, `visibleRegions` dot-product filter, zoom revert — żadna nie poprawia pozycji.
- **Rozwiązanie:** Używać `GeoJsonLayer` zamiast `ScatterplotLayer`/`TextLayer` dla markerów geograficznych w GlobeView. GeoJsonLayer ma natywną, certyfikowaną obsługę `_GlobeView`.
- **Alternatywa:** HTML overlay — `<div>` pozycjonowane przez `viewport.project([lon, lat])` (deck.gl viewport API).
- **Nie używać:** `ScatterplotLayer`, `TextLayer`, `IconLayer` bez weryfikacji w `_GlobeView` — mogą mieć ten sam bug.
- **UPDATE 2026-05-07:** Patrz wpis poniżej — bug okazuje się fundamentalny, NAWET `GeoJsonLayer` i `viewport.project()` zawodzą.

### [2026-05-07] GlobeView marker bug deck.gl 9.3.1 — FUNDAMENTALNY (zaktualizowane)

- **Skala problemu:** Bug pozycjonowania `_GlobeView` w deck.gl 9.3.1 afektuje WSZYSTKIE warstwy markerowe ORAZ API projekcji. Spędzona ~3h debugowania.
- **Co NIE działa (zweryfikowane):**
  1. `ScatterplotLayer` — markery w złych miejscach
  2. `TextLayer` — j.w.
  3. `GeoJsonLayer` (z `pointType: 'circle+text'`) — j.w. (NIE jest workaroundem mimo wcześniejszej rekomendacji deck.gl docs)
  4. HTML overlay z `viewport.project([lon, lat])` przez `deckRef.current.getViewports()[0]` w `onAfterRender` — RAF timing lag, markery "pływają" po globie
  5. HTML overlay z manualną projekcją perspektywiczną wyprowadzoną z `globe-viewport.ts` source (`lookAt([0,-alt,0]) * RX(lat) * RZ(-lon) * Scale(s/h)`, `f = 2*alt = 3`, `fh = alt*height`) — numerycznie zweryfikowana, user nadal "źle"
  6. HTML overlay z `_GlobeViewport.project()` instancjonowanym w `useMemo([viewState, canvasSize])` — używa **identycznego kodu** co deck.gl wewnętrznie, user nadal "źle"
- **Decyzja architektoniczna:** Zero markerów geograficznych na globie. Pivot na:
  - **Bottom button bar** + GuidedTour jako jedyna nawigacja regionów
  - **`<ArrivalRing />`** — animowany pierścień na środku ekranu po przylocie kamery (pozycja zawsze idealna, bo środek ekranu = miejsce lądowania kamery)
  - **`<RegionHUD />`** — overlay w prawym górnym rogu z label + coords aktywnego regionu
  - **Real chart w StatsPanel** (recharts/visx) — time-series NDVI/SST/NDBI; więcej "ambitności" niż statyczne kropki na globie
- **Reguła:** Nie próbować markerów na `_GlobeView` w deck.gl 9.3.1 — zmarnowany czas. Jeśli przyszłość wymusi markery → R3F z prawdziwymi 3D obiektami na sferze (custom three.js) lub upgrade deck.gl gdy fix.

### [2026-05-06] Vite Fast Refresh — nie mieszać eksportów komponent + dane w jednym pliku

- **Problem:** Plik React z eksportem komponentu (`Globe`) ORAZ non-komponentu (`REGIONS`) triggeruje `hmr invalidate` z komunikatem "Could not Fast Refresh". Vite wykonuje full page reload zamiast hot swap.
- **Fix:** Przenieść dane/stałe do osobnego pliku (np. `src/data/regions.ts`). Komponent importuje z tego pliku. Fast Refresh działa poprawnie.
- **Scope:** Każdy plik `*.tsx` który eksportuje zarówno komponent jak i stałe/typy powinien mieć stałe/typy w osobnym `.ts`.

### [2026-05-02] T9.2 DONE — Vercel deploy: vercel.json w frontend/, nie w root

- **Gotcha monorepo:** Vercel auto-wykrywa `frontend/` jako Root Directory (bo tam jest `package.json` + `vite.config.ts`). `vercel.json` w root z `buildCommand: "cd frontend && ..."` failuje — `cd frontend` nie istnieje gdy CWD = `frontend/`.
- **Fix:** `vercel.json` musi być w `frontend/` z `buildCommand: "npm run build"` i `outputDirectory: "dist"` (ścieżki relatywne do Root Directory).
- **Deploy URL:** https://terra-lens-zeta.vercel.app/ · Repo: https://github.com/Piotr1686/TerraLens

### [2026-05-02] T9.2 DONE — HeatmapLayer demo pattern: DEMO_DATE + distinct GIBS layers

- **Problem:** GIBS może nie mieć danych dla dat 2025/2026 (NDVI 8-day composite laga, false-color też). Użycie `currentDate` z timeline (= bieżący miesiąc) → puste kafelki → heatmapa niewidoczna.
- **Fix:** `DEMO_DATE = '2023-07-01'` hardcoded w `useHeatmapLayer.ts` dla trybu demo. Produkcja używa PMTiles z HF CDN (nie zależy od daty).
- **Distinct layers per metric:** SSIM→`MODIS_Terra_CorrectedReflectance_TrueColor` (.jpg), NDVI→`MODIS_Terra_NDVI_8Day` (.png), CVA→`MODIS_Terra_CorrectedReflectance_Bands721` (.jpg). Wszystkie EPSG:4326, 250m, zoom 0–9.
- **UX wzorzec:** `HeatmapControls` renderuje się tylko gdy `arrivedRegion !== null` (App.tsx). Kliknięcie metryki przed lądowaniem kamery = brak efektu — dlatego kontrolki są ukryte do momentu lądowania.

### [2026-05-03] GIBS EPSG:4326 — niestandardowe TileMatrix dimensions + poprawne layer IDs

- **Wymiary TileMatrixSet:** GIBS EPSG:4326 używa własnego podziału (nie standardowego 2^(z+1) × 2^z). Zoom 6 = **80 × 40** (nie 128 × 64). Dotyczy WSZYSTKICH tilematrixsetów (250m, 500m, 1km, 31.25m). Pełna tabela: zoom 0=2×1, 3=10×5, 4=20×10, 5=40×20, 6=80×40, 7=160×80, 8=320×160. Wzór: `col = int((lon+180)/360 * matrix_width)`, `row = int((90-lat)/180 * matrix_height)`.
- **Poprawne layer IDs dla pipeline:** `HLS_RGB` → `MODIS_Terra_CorrectedReflectance_TrueColor` (format: jpg, TMS: 250m). `MODIS_NDVI` → `MODIS_Terra_NDVI_8Day` (format: png, TMS: 250m). Stare: `HLS_L30_Nadir_BRDF_Adjusted_Reflectance`/31.25m→400, `MODIS_Terra_L3_NDVI_Monthly_9km`/2km→400. Correct layers zweryfikowane przez GIBS GetCapabilities.
- **Fix w kodzie:** `gibs.py LAYERS` naprawione. `regions.py bbox_to_tiles` — sygnatury `lon_to_col(lon, matrix_width)` i `lat_to_row(lat, matrix_height)` z lookup-table `GIBS_MATRIX_WIDTHS/HEIGHTS` zamiast `2**(z+1)`.

### [2026-05-03] GIBS MODIS_Terra_NDVI_8Day — dostępność tylko od 2025-02-12

- **Odkrycie przez GetCapabilities:** `MODIS_Terra_NDVI_8Day` (250m, PNG) ma w GIBS dane wyłącznie od **2025-02-12** do ~bieżącej daty. Daty 2023/2024 zwracają HTTP 404.
- **Konsekwencja dla pipeline:** T9.1 fetch MODIS_NDVI musi używać `--start-date 2025-03-01` lub późniejszej. Historyczne dane NDVI (pre-2025) niedostępne w GIBS dla tej warstwy.
- **Konsekwencja dla frontendu:** `DEMO_DATE` w `useHeatmapLayer.ts` zmieniony z `'2023-07-01'` na `'2025-07-15'` — działa dla wszystkich 3 warstw demo (TrueColor/NDVI_8Day/Bands721).
- **TrueColor i Bands721:** Nie mają tego ograniczenia — mają wieloletnią historię w GIBS.

### [2026-05-03] Windows cp1250 — znaki Unicode w Rich console output CLI

- **Problem:** Znak `→` (U+2192) w `console.print()` crashuje na Windows z kodowaniem cp1250: `UnicodeEncodeError: 'charmap' codec can't encode character '→'`.
- **Fix:** Zastąp `→` przez `->` w każdym `console.print()` w `__main__.py`. Dotyczy też innych znaków spoza cp1250 (np. `←`, `↑`, emoji).
- **Alternatywa:** `PYTHONIOENCODING=utf-8` przed wywołaniem — ale stała zamiana w kodzie jest pewniejsza.

### [2026-04-25] S2 DONE — Data fetchers: GIBS WMTS + EPSG:4326 tile math + SRTM Earthdata

- **GIBS tile URL:** `{base}/{layer_id}/default/{date}/{tilematrixset}/{z}/{row}/{col}.png` — uwaga: kolejność row/col (nie x/y jak w TMS), row = TileRow (latitude direction).
- **EPSG:4326 tile math:** `col = (lon+180)/360 × 2^(z+1)`, `row = (90-lat)/180 × 2^z`. Różni się od Web Mercator — GIBS używa EPSG:4326, nie EPSG:3857.
- **LAYERS dict:** Klucze skrócone (`HLS_RGB`, `MODIS_NDVI`) → layer_id + tilematrixset + fmt. Rozszerzać przy dodawaniu warstw w S3+.
- **SRTM1 tile naming:** Pliki z LP DAAC mają format `{N/S}{dd}{E/W}{ddd}.SRTMGL1.hgt.zip` (SW corner). Ręcznie zdefiniowane per region w `REGION_SRTM_TILES`.
- **Ctrl+C safety:** SIGINT → flaga `_INTERRUPTED`, pętla fetch kończy bieżący tile i wychodzi. SQLite WAL mode + commit per tile = brak ryzyka korupcji.

### [2026-04-25] S1 DONE — CLI skeleton: Typer + dataclass Config + SQLite bez ORM

- **Stack CLI:** Typer 0.24 (`__main__.py`) + Rich console — 4 komendy (fetch/process/export/deploy) z docstringami. Pakiet zainstalowany editable (`pip install -e .`).
- **Config:** `src/terralens/config.py` — singleton `@dataclass Config` z `get_config()`. Wartości z Hardware Execution Policy: `tile_size=512`, `tile_overlap=64`, `vram_budget_mb=2500`, `batch_size=1`, `precision="fp16"`.
- **Cache:** `src/terralens/db/queries.py` — czyste SQL (bez ORM), WAL mode, UPSERT `ON CONFLICT`, TTL przez `expires_at` ISO8601 UTC. `cleanup_expired()` zwraca liczbę usuniętych wierszy.
- **Uzasadnienie:** Brief v3.2 wymaga SQLite bez ORM dla prostoty. Typer wybrany nad Click ze względu na automatyczne `--help` z type hints.

### [2026-05-02] T8.4 — FPS throttle: fps w CinematicFlightConfig, fpsRef przez useEffect

- **Wzorzec fps throttle:** `fps` jako pole `CinematicFlightConfig` (nie parametr hooka) — brak refa w hooku, brak render-time write. Globe.tsx przekazuje `fps` z propsa do każdego wywołania `fly()`.
- **fpsRef w useRevealOpacity:** `useEffect(() => { fpsRef.current = fps }, [fps])` — aktualizacja refa poza renderem. React Compiler `react-hooks/refs` zabrania `fpsRef.current = fps` bezpośrednio w ciele funkcji komponentu/hooka.
- **Throttle logika:** `minFrameMs = 1000 / fps`. Tick pomija `onFrame/setViewState` gdy `now - lastFrameTime < minFrameMs` — nadal wywołuje RAF aby nie stracić czasu animacji. Finalna klatka (`t >= 1`) zawsze przechodzi (bez throttle) gwarantując dokładne wylądowanie.
- **Mobile breakpoint:** `useMediaQuery('(max-width: 768px)')` → `fps = 30`. Zmienia się tylko przy rotacji urządzenia — akceptowalny koszt re-tworzenia callbacków.

### [2026-05-02] T8.3 — Heatmap reveal: arrivedRegion + onRegionArrival pattern

- **Wzorzec:** `arrivedRegion` (oddzielny state od `selectedRegion`) jako trigger dla `useRevealOpacity` i jako `region` dla `useHeatmapLayer`. Heatmap ukryta podczas lotu (region=null → layer=null), ujawnia się dopiero po wylądowaniu.
- **Przepływ:** `selectedRegion` zmienia się na starcie lotu → `useEffect([selectedRegion])` czyści `arrivedRegion=null` → brak heatmapy. Po wylądowaniu `onRegionArrival(id)` → `arrivedRegion=id` → reveal animacja.
- **onComplete w fly():** Opcjonalny callback `onComplete?: () => void` w `useCinematicFlight.fly()` — wywoływany po ostatniej klatce RAF. Globe.tsx: `() => onRegionArrival?.(region.id)`.
- **Dlaczego arrivedRegion ≠ selectedRegion:** selectedRegion zmienia się natychmiast (steruje UI markera, tourem). arrivedRegion zmienia się z opóźnieniem (po locie) — steruje tylko heatmapą.

### [2026-05-02] T8.2 — Cinematic camera: RAF + Bezier zoom arc (bez FlyToInterpolator)

- **Architektura:** `useCinematicFlight()` — hook z wewnętrznym `posRef` (pozycja kamery). Nie przyjmuje `setViewState` jako parametru — zamiast tego `fly(to, config, onFrame)` przyjmuje callback na każdą klatkę. `setPosition(vs)` synchronizuje pozycję po interakcji usera.
- **Dlaczego posRef wewnętrznie:** ESLint `react-hooks/refs` flaga dostęp do `ref.current` w domknięciach tworzonych podczas renderu (np. w `flyToRegion` → `markerLayer.onClick`). Przeniesienie odczytu `ref.current` do wnętrza hooka (wywoływanego z event handlera, nie z renderu) eliminuje błąd.
- **Bezier zoom arc:** Kwadratowy Bezier P0=z_start, P1=min(z0,z1)-zoomDip, P2=z_end. `zoomDip=1.5` dla lotu do regionu, `0.8` dla resetu do globu. Floor P1 na 0.5 (nie znikamy poniżej horyzontu).
- **Easing:** `easeInOutCubic(t)` — standardowa formuła, wolny start, przyspieszenie, wolne lądowanie.
- **Cancel on interaction:** `onViewStateChange` sprawdza `interactionState.isDragging/isZooming/isPanning/isRotating` → `cancelFlight()`. Lot płynnie przerywany, user przejmuje kontrolę.
- **Kolejność deklaracji:** `flyToRegion` i `handleReset` muszą być zadeklarowane PRZED `useEffect([flyTarget])` który ich używa (hoisting nie działa dla `const`).

### [2026-05-01] T8.1 — Preloader gate + manifest ownership

- **Wzorzec gate:** `useTour({ enabled: isReady })` — `useEffect([enabled])` odpala `start()` gdy `enabled` zmienia się `false→true`. Bezpieczne: przy re-render z tym samym `true` nie startuje ponownie (timer już biegnie).
- **Manifest ownership:** manifest.json fetchuje `usePreload` (jeden fetch, jeden owner). Globe.tsx nie fetchuje go samodzielnie — prop `onManifestLoaded` usunięty. App.tsx przekazuje wynik do `manifestTimeline` via `useEffect([manifest])`.
- **MIN_DISPLAY_MS:** `usePreload` trzyma `startTime = Date.now()` i opóźnia `setIsReady(true)` o `max(0, MIN_DISPLAY_MS - elapsed)`. Preloader nie mignie przy szybkim połączeniu.
- **amazonia_preview.jpg:** `/public/amazonia_preview.jpg` — plik nie istnieje → CSS gradient fallback. `preloadImage` rozwiązuje nawet przy 404 (graceful degrade). Dodać prawdziwy plik przed deploy S9.

### [2026-05-01] T7.5 — Guided Tour: flyTarget prop + timer-based kroki

- **Sterowanie globem z zewnątrz:** `Globe.flyTarget?: string | null` — gdy zmienia się na string → FlyToInterpolator do regionu; gdy null → handleReset. `undefined` = brak sterowania (user mode).
- **useTour wzorzec:** `runStep(idx)` → `setTimeout(runStep(idx+1), duration)` — ta sama strategia co T6.2. Rekursja przez `timerRef`, brak deps w useCallback (zamknięcie przez ref).
- **Interrupt:** kliknięcie markera + ESC → `stop()` → `isRunning=false` → `flyTarget=undefined` → Globe wraca pod kontrolę usera. Animacja FlyTo dokończa się (smooth, nie jump-cut).
- **Replay:** `clearTimer` + `requestAnimationFrame(() => runStep(0))` — RAF gwarantuje że React zaktualizuje stan przed startem nowej sekwencji.
- **T8.2:** `useTour.ts` będzie rozbudowany o krzywe Beziera — zachować `TOUR_STEPS` jako publiczne stałe.

### [2026-04-30] T7.3 — Heatmap overlay: TileLayer raster (nie MVTLayer), GIBS jako demo

- **Format:** Heatmapy SSIM/NDVI/CVA są raster PNG → `TileLayer + BitmapLayer`. `MVTLayer` tylko dla vector tiles — nie używać dla raster heatmap.
- **Demo fallback:** GIBS `MODIS_Terra_NDVI_8Day` (brak auth, date-parameterized) jako placeholder gdy PMTiles niedostępne. URL: `.../MODIS_Terra_NDVI_8Day/default/{date}/250m/{z}/{y}/{x}.png`
- **Architektura:** `useHeatmapLayer(config)` → zwraca `Layer | null`. `Globe.extraLayers` prop przyjmuje tablicę dodatkowych warstw wstawianych między tile'ami a markerami.
- **Aktywacja:** Heatmap pojawia się tylko gdy `region !== null` i `opacity > 0`. Bez wybranego regionu — brak requestów.

### [2026-04-30] T7.2 — Cross-fade między tile layers: RAF + dwa TileLayer z opacity

- **Wzorzec:** Dwa `TileLayer` równolegle: `tile-prev` (opacity = 1 - progress) + `tile-current` (opacity = progress). Przejście 600ms via `requestAnimationFrame`.
- **Dlaczego nie CSS:** DeckGL renderuje do canvas — CSS transitions na warstwie nie działają. Jedyna opcja to `opacity` prop w DeckGL layer + RAF.
- **Hook:** `useTimeline(manifestTimeline?)` — zwraca `{ dates, dateIndex, tileUrl, setDateIndex }`. Demo: MODIS daty historyczne, Blue Marble dla ostatniej daty ("teraz").
- **Scope:** `Globe.tsx` zarządza cross-fade wewnętrznie (prop `tileUrl`), `App.tsx` koordynuje z `Timeline.tsx` i `useTimeline`.

### [2026-04-30] S6 DONE — Frontend engine: Deck.gl GlobeView (ADR-001)

- **Decyzja:** Deck.gl `_GlobeView` jako silnik 3D globu. R3F PoC pominięty — Deck.gl spełnia wymagania MVP.
- **Uzasadnienie:** TileLayer + PMTiles natywne, EPSG:4326 działa z GIBS, performance OK, zero custom shaderów na start.
- **Tour gotcha:** `FlyToInterpolator` nie wyzwalał `onTransitionEnd` reliably → zastąpiony timer-based (setTimeout per stop). Cinematic quality oceniana w T7.5.
- **Blue Marble source:** `BlueMarble_NextGeneration` — brak daty w URL (time-invariant), ext `.jpeg`, zoom 0–7. Poprawny URL: `.../BlueMarble_NextGeneration/default/500m/{z}/{y}/{x}.jpeg`
- **ADR:** `docs/ADR-001-frontend-engine.md`

### [2026-04-28] T6.1 DONE — Frontend scaffold: Tailwind v4 + shadcn/ui + TS alias gotcha

- **Tailwind v4:** Brak `tailwind.config.js` — tylko `@import "tailwindcss"` w CSS + plugin `@tailwindcss/vite` w `vite.config.ts`. Nie używaj starego `tailwind.config.ts`.
- **shadcn/ui init:** Wymaga aliasu `@/*` w `tsconfig.json` (root), nie tylko w `tsconfig.app.json`. Dodaj `compilerOptions.paths` do obu plików.
- **TS baseUrl deprecated:** TypeScript 7.0 deprecuje `baseUrl`. Fix: `"ignoreDeprecations": "6.0"` w tsconfig.app.json (nie "5.0").
- **ESLint shadcn:** `react-refresh/only-export-components` błędnie flaguje `button.tsx` (eksportuje `buttonVariants`). Override: `{ files: ['src/components/ui/**'], rules: { 'react-refresh/only-export-components': 'off' } }` — musi być PO głównym configu w tablicy (flat config, kolejność decyduje).
- **pre-commit check-json:** `tsconfig*.json` używają JSONC (komentarze `//`) — dodaj `exclude: ^frontend/tsconfig.*\.json$` do hooka `check-json`.

### [2026-04-28] T5.3 DONE — Deploy HF Datasets: Range Requests HTTP 206 potwierdzone

- **API deploy:** `collect_deploy_files(export_dir, region)` → PMTiles (posortowane) + manifest.json na końcu. `deploy_files(files, *, token, repo_id, public_url_base, dry_run, on_progress)` → `{filename: public_url}`.
- **HF CDN Range Requests:** Zweryfikowane empirycznie HTTP 206 (`bytes 0-63/433`) — pmtiles.js zadziała z URL `https://huggingface.co/datasets/Piotr1686/terralens-data/resolve/main/{file}`.
- **Ruff gotcha:** `EnvironmentError` → `OSError` (aliasy Python 3, ruff wymusza OSError). `Callable` → `collections.abc.Callable`. Oba zmiany automatyczne przez ruff hook.
- **Writer.write_tile API:** `writer.write_tile(tile_id, data)` — tile_id z `zxy_to_tileid(z,x,y)`, NIE `write_tile(z, x, y, data)`.

### [2026-04-27] T5.1 DONE — PMTiles raster export: WebP obsługiwane, regex scan

- **pmtiles lib WebP:** `TileType.WEBP = 4` — lib w pełni obsługuje raster WebP. Nie trzeba tippecanoe.
- **scan_tiles regex:** `r"(?P<z>\d+)[/\\](?P<x>\d+)[/\\](?P<y>\d+)\.(png|jpg|jpeg|webp)$"` z `re.search()` + kotwicą `$` — kotwica sprawia że pattern zawsze dopasowuje ostatni segment `z/x/y.ext` w ścieżce. Działa zarówno dla płaskich ścieżek jak i zagnieżdżonych GIBS (`{layer}/{date}/{z}/{x}/{y}.png`).
- **Header PMTiles:** Bounds w formacie `min/max_lon/lat_e7` (lon/lat × 10^7, int32). `center_zoom` = mediana zoom levels. `finalize()` auto-ustawia `min_zoom`, `max_zoom` z tile entries.
- **WebP pass-through:** Tile'y już w WebP są przepisywane bez re-kompresji (sprawdzanie `path.suffix`). PNG/JPEG → `_to_webp()` przez Pillow.

### [2026-04-26] S4 DONE — Change detection pipeline: SSIM + NDVI + CVA

- **Moduły:** `cloud_mask.py` (T4.1), `histogram_match.py` (T4.2), `ssim.py` (T4.3), `ndvi.py` (T4.4), `cva.py` (T4.5).
- **Wzorzec NaN:** Wszystkie procesory obsługują NaN (z cloud masking) przez fill-with-zero przed obliczeniami i restore-NaN po. Zachowany w każdym wyjściu.
- **CVA threshold:** Domyślny próg ΔE = 10.0 wg CIE (wartość JND — just noticeable difference). Zmiana koloru bez zmiany struktury = unikalny sygnał CVA pominięty przez SSIM.
- **NDVI threshold:** Domyślny spadek 0.2 dla deforestacji (scale [0,1]). Plik JSON: `data/processed/{region}/changes.json`.

### [2026-04-26] T4.3 DONE — skimage SSIM multichannel: full=True zwraca (H,W,C), nie (H,W)

- **Odkrycie:** `structural_similarity(a, b, channel_axis=-1, full=True)` zwraca `ssim_image` o kształcie `(H, W, C)` — po jednej mapie na kanał. Nie (H,W) jak mogłoby sugerować dokumentacja.
- **Fix:** Po wywołaniu: `if ssim_image.ndim == 3: ssim_image = ssim_image.mean(axis=-1)` → (H, W).
- **Scope:** `processors/ssim.py → compute_ssim_map()`. Dotyczy każdego miejsca gdzie używa się `full=True` + `channel_axis=-1`.

### [2026-04-26] T3.3 DONE — Cosine window blending: midpoint +0.5 obowiązkowy

- **Problem:** Standardowe okno cosinusowe `0.5*(1 - cos(2π*x/N))` przy `x=0` daje dokładnie 0. Piksele na krawędzi obrazu pokryte tylko jednym tile'em dostają weight=0 → canvas też 0 → po normalizacji output = 0 (czarna ramka).
- **Fix:** Przesunięcie midpoint: `x = arange(N) + 0.5` → brak dokładnych zer. Dla N=512: wartość na krawędzi ≈ 9.6e-6 — pomijalna wizualnie, ale numerycznie stabilna w normalizacji.
- **Weryfikacja:** `test_uniform_input_produces_uniform_output` + `test_no_seams_variance` — oba PASS po fixie.
- **Scope:** `processors/tiled.py` → `_cosine_window()`. Dotyczy każdego procesorka używającego tiled blending w S4+.

### [2026-04-26] T3.1 DONE — Satlas FPN output scale: full-res (1/1), nie 1/4

- **Kluczowe odkrycie:** `weights.get_pretrained_model("Sentinel2_SwinB_SI_RGB", fpn=True)` zwraca listę feature map, gdzie indeks 0 (najwyższa rozdzielczość) = **pełna rozdzielczość wejścia** (1/1 scale), nie 1/4 jak w standardowym SwinB.
- **Konsekwencja dla SR dekodera:** Potrzeba tylko 2× PixelShuffle(2) = 4× total dla 4× SR (nie 4× PixelShuffle). Zweryfikowane empirycznie: 256×256 input → FPN[0] shape = (B, C, 256, 256) → dekoder → (B, 3, 1024, 1024).
- **Wrapper:** `SatlasESRGAN` (`engines/satlas_esrgan.py`) — singleton, `load()`/`unload()`/`upscale()`, FP16 CUDA. Wagi dekodera w `data/models/satlas_esrgan_x4.pt` (opcjonalne). `get_esrgan()` + `reset_esrgan()` dla testów.
- **VRAM:** Po load ~266 MB backbone + ~50 MB dekoder. Delta 10 iter = 0.0 MB. Po unload < 200 MB. PASS.

### [2026-04-25] T0.1 PASS — Satlas SwinB VRAM: 266 MB peak, 0.0 MB delta, ~3.5 GB headroom

- **Wyniki PoC:** Peak allocated 266 MB (PyTorch), 551 MB (nvidia-smi z CUDA ctx), delta 0.0 MB — idealnie stabilny.
- **Wniosek:** Satlas SwinB backbone jest bardzo lekki. Nawet pełna architektura ESRGAN z dekoderem (~1.5 GB wg briefu) mieści się z dużym zapasem.
- **Strategia VRAM potwierdzona:** tiled 512×512, FP16, singleton, `empty_cache` co 2 tile'y — wystarczająca bez modyfikacji.
- **Skrypt:** `scripts/poc_satlas.py`, output `scripts/poc_results.txt`. Można używać jako VRAM benchmark po każdej zmianie modelu w S3.

### [2026-04-20] Stack runtime zwalidowany — PyTorch 2.6.0+cu124 na RTX 3050 Laptop 4GB

- **Driver NVIDIA:** 566.36 → CUDA runtime 12.7 (`nvidia-smi`)
- **PyTorch wheel:** `cu124` (nie `cu121` z pierwotnego planu) — stable wheele dla cu128 tylko w nightly, cu124 działa forward-compatible na 12.7
- **Satlas:** `satlaspretrain-models==0.3.1` z PyPI (maj 2024) — import jako `satlaspretrain_models`, załadował się bez błędu na Python 3.10
- **Weryfikator:** `scripts/verify_t02.py` zwraca exit 0/1 + tekstowy raport (torch/CUDA/GPU/satlas). Przeszedł `[OK]` 2026-04-20.
- **VRAM w trybie idle (sam torch import):** ~200MB. Pomiar Satlas SwinB SR z batch_size=1, tile 512×512, FP16 — dopiero w T0.1.
- **Konsekwencja:** environment.yml zamrożony (`conda env export --no-builds`). Reproducible na drugiej maszynie przez `conda env create -f environment.yml`.

---

## Rozwiązane problemy

<!-- Gotowe rozwiązania trudnych problemów — żeby nie szukać ich ponownie -->

### [2026-06-04] Vercel stale-deploy 31 dni — `.gitignore data/` łykał frontend/src/data/regions.ts

- **Objaw:** produkcja terra-lens-zeta.vercel.app serwowała bundle sprzed 31+ dni mimo regularnych `git push` na master. Wizualnie: glob rozpadał się na czarne kliny południkowe + martwe klikanie regionów. Stary bundle żądał kafli bazowych w `epsg4326/250m` (niekompatybilnym z deck.gl) → lawina HTTP 400 → brak kafli (to samo co [[2026-05-06]] seam, ale z innej przyczyny — brak danych, nie brak `_imageCoordinateSystem`).
- **Root cause:** root `.gitignore` miał **niezakotwiczony** wzorzec `data/`, który łapał też `frontend/src/data/` → `regions.ts` (definicje Amazonia/Dubai/Arctic) **nigdy nie trafił do gita**. Na Linuxie (Vercel) klon repo nie miał pliku → `tsc -b` rzucał `TS2307 Cannot find module '@/data/regions'` → exit 2 → build **Error** (~11s). Lokalnie (Windows) i `vercel build` z working tree działały, bo miały plik na dysku — bug niewidoczny lokalnie. Każdy auto-build od ~31 dni padał (seria ● Error w `vercel ls`), więc alias produkcyjny stał na ostatnim udanym (prastarym).
- **Diagnoza (dowodami):** grep bundla prod (`ssim_heatmap=0`, `epsg4326=1`) → stary build; `vercel ls terra-lens` → seria ● Error 11s; `vercel inspect --logs <error-deploy>` → dokładny `TS2307`. NIE zgadywanie.
- **Fix:** `.gitignore` `data/` → `/data/` (zakotwiczone do korzenia, tylko pipeline Python), zacommitowany `frontend/src/data/regions.ts`. Commit `c19e052`. Po pushu auto-build przeszedł (● Ready, 14s) — pipeline `git push → deploy` znów działa.
- **Naprawa natychmiastowa (zanim znaleziono root cause):** vercel CLI prebuilt deploy (`vercel build` + `vercel deploy --prebuilt --prod`) + `vercel alias set` — ominęło padający auto-build, bo budowało z lokalnego working tree.
- **Gotcha TLS:** vercel CLI na tej maszynie wymaga `NODE_EXTRA_CA_CERTS` = bundle certów z magazynu Root Windows (maszyna przechwytuje TLS). Czyste rozwiązanie, BEZ `NODE_TLS_REJECT_UNAUTHORIZED=0`. Patrz [[feedback_windows_ssl]]. Bundle: `%TEMP%\win-ca-bundle.pem` (regenerowalny z `Get-ChildItem Cert:\LocalMachine\Root`).
- **Reguła:** Po istotnym pushu **weryfikuj hash bundla produkcji** (`curl prod | grep index-*.js`), nie ufaj samemu „push przeszedł". `git push` ≠ „wdrożone" — build może cicho padać na case-sensitivity / brakujący-bo-gitignored plik (Linux ≠ Windows). Powiązane z anty-wzorcem z [[2026-05-02]] (Vercel monorepo) — dashboard `buildCommand` ma zbędne `cd frontend`, ale `frontend/vercel.json` to nadpisuje.

### [2026-05-30] [ROZWIĄZANY 2026-06-04] SSIM pipeline: cloud-masked reference (NaN) korumpuje histogram matching

- **Bug (code review Sprintu 1):** `_ssim_pair` (`scripts/run_change_detection.py`) zawsze podaje `reference_qa` do `compute_change_map`, więc `apply_cloud_mask` zamienia chmury w referencji na `NaN`. Potem `compute_change_map` woła `match_to_reference(target, reference)` — a `match_to_reference` (`processors/histogram_match.py`) odtwarzał/wypełniał NaN **tylko dla `target`**, nigdy dla `reference` (stary docstring mówił wprost „reference: bez NaN").
- **Skutek:** `skimage.exposure.match_histograms` dostawał template z NaN → CDF referencji skażone (NaN na końcu kwantyli) → jasne piksele target mapowane na NaN/śmieci. `ssim_mean` zaniżone, `change_fraction` zawyżone. Stary kod wołał `compute_change_map(a, b)` BEZ QA (referencja bez NaN), więc problem był **regresją wprowadzoną w tamtej sesji**.
- **Fix (zastosowany):** `match_to_reference` przepisane na **maskowane dopasowanie histogramu kanał po kanale** — nowy helper `_match_cumulative_cdf_masked(source_vals, template_vals)` operuje na 1-D wektorach **tylko ważnych** (nie-NaN) pikseli; maski liczone osobno dla target i reference (`~any(isnan, axis=-1)`). Usunięta zależność od `skimage.exposure.match_histograms`. Naprawia oba defekty naraz: NaN w reference psujący template CDF **oraz** wcześniejsze wypełnianie target zerami zaszumiające rozkład źródła.
- **Weryfikacja:** re-run `run_change_detection.py` + `build_stats.py` → **Dubaj surface change 86% → 55%** (bug zawyżał o ~31 pkt proc., podejrzenie potwierdzone). Amazonia −16% NDVI bez zmian (ścieżka NDVI nietknięta), Arctic SSIM nadal poprawnie odrzucony jako data-gap. Frontend `tsc --noEmit` zielony.
- **Powiązane drobiazgi z review (zrobione):** (1) `run_ssim_detection` — przy 2 datach `overall` reużywa `series[0]` zamiast liczyć `_ssim_pair(dates[0], dates[-1])` drugi raz; (2) martwy prop `currentDate` usunięty z `StatsPanel.Props`, z `App.tsx:143` oraz z nieużywanej destrukturyzacji `useTimeline` w `App.tsx:72`.
- **Latentny follow-up (osobny ticket):** Arctic summary first-vs-last bierze Sty→Lip (oba śnieg → SSIM≈1.0 → odrzut), choć środek serii ma realną zmianę sezonową — detekcja data-gap działa, ale summary dla Arctic jest mało informatywne. Patrz [[project_arctic_hls_gap]].

### [2026-04-26] VRAM fragmentation na RTX 3050 — empty_cache co 2 tile'y, nie per-tile

- **Strategia:** `torch.cuda.empty_cache() + gc.collect()` co `cfg.empty_cache_every_n_tiles=2` iteracje, nie po każdym tile'u.
- **Uzasadnienie:** Per-tile cleanup kosztuje ~5–15ms każdorazowo (CUDA kernel sync). Przy 20 tile'ach na obraz daje 100–300ms narzutu. Co 2 tile'y = połowa kosztu, ta sama stabilność VRAM (zweryfikowane: delta 0.0 MB po 10 iteracjach w T3.1).
- **Konfiguracja:** `Config.empty_cache_every_n_tiles = 2` (src/terralens/config.py). Zwiększ do 4–8 jeśli tile'y są małe (256 px), zmniejsz do 1 jeśli OOM.

### [2026-04-25] SRTM Earthdata: rate limiting 429 + redirect auth

- **Objaw:** LP DAAC Earthdata zwraca 429 z nagłówkiem `Retry-After`. Bez obsługi → crash lub utknięcie.
- **Fix:** `_download_dem_with_retry()` czyta `Retry-After` z nagłówka (domyślnie 30s) i śpi przed retry. Pętla max 3 próby.
- **Dodatkowy gotcha:** Earthdata używa OAuth redirect przy pierwszym logowaniu — `requests.Session` z `.auth=(user, pass)` + `allow_redirects=True` obsługuje automatycznie. Jeśli 401 po redirect → invalid credentials (nie retry).
- **Scope:** Dotyczy T2.4 `srtm.py`. GIBS (T2.1) NIE wymaga auth.

### [2026-04-25] `conda run` + Rich na Windows = UnicodeEncodeError (cp1250)

- **Objaw:** `conda run -n terralens terralens --help` → `UnicodeEncodeError: 'charmap' codec can't encode character '�'` — conda przechwytuje stdout i re-koduje przez cp1250, co psuje znaki ramek Rich.
- **Fix:** `PYTHONIOENCODING=utf-8 conda run -n terralens python -m terralens --help` — wymuś UTF-8 przed wywołaniem. Lub: aktywuj env normalnie (`conda activate terralens`) i wywołaj `terralens` bezpośrednio.
- **Scope:** Dotyczy tylko `conda run` w nieinteraktywnym shellu (bash w Claude Code, CI). W aktywowanym terminalu Windows Terminal z UTF-8 problem nie wystąpi.

### [2026-04-20] pre-commit `run --all-files` na pustym git indexie = wszystko `Skipped`

- **Objaw:** Po `git init` (bez `git add`) `pre-commit run --all-files` pokazuje `(no files to check) Skipped` dla każdego hooka.
- **Przyczyna:** `--all-files` operuje na plikach w git indexie, nie w filesystemie. Pusty index → zero plików → nic do sprawdzenia.
- **Fix:** `git add .` przed `pre-commit run --all-files`. Wtedy hooki przelecą po staged files. Jeśli `trailing-whitespace` lub `mixed-line-ending` autofixują → re-stage (`git add .`) i uruchom ponownie.
- **Windows gotcha:** `pre-commit run --all-files` na świeżym env kompiluje ruff i ruff-format przy pierwszym użyciu — może wyglądać na zawieszony ~30–60s na pierwszym hooku bez outputu. Cache hook envs ląduje w `~\.cache\pre-commit\`, kolejne przebiegi 5–15s.

---

## Aktywne TODO (długoterminowe)

<!-- Zadania rozlewające się przez wiele sesji. Krótkoterminowe są w last_session.md -->

_Brak wpisów._

---

## Odrzucone podejścia

<!-- Co nie działało i dlaczego — unikamy powtarzania błędów -->

_Brak wpisów._

---

## Słownik projektu

<!-- Specyficzne terminy używane w TerraLens -->

_Brak wpisów._

---

## Zewnętrzne zależności i integracje

<!-- Klucze API, serwisy zewnętrzne, specyficzne biblioteki -->

### [2026-04-20] NASA Earthdata Login — `piotr1686`

- **Authorized Apps:** LP DAAC Data Pool, LP DAAC Cumulus PROD, ORNL DAAC Daymet imagery for GIBS (+ 5 standardowych auto-authorized)
- **Credentials:** `.env` (gitignored), zmienne `NASA_EARTHDATA_USER` + `NASA_EARTHDATA_PASS`. Template w `.env.example`.
- **Użycie:** wymagane tylko dla SRTM DEM w T2.4. GIBS (primary source) NIE wymaga auth.
- **Auth flow:** HTTP Basic + cookie jar przez `requests` + `.netrc` lub programatycznie z `python-dotenv`.

### [2026-04-20] NASA api.nasa.gov key — zapisany profilaktycznie

- **Zmienna:** `NASA_API_KEY` w `.env`
- **Użycie:** OPCJONALNE, tylko gdyby Faza 2 wymagała Earth Imagery API. GIBS (MVP source) nie używa tego klucza.
- **Limity:** 1000 req/h (własny klucz) vs 50 req/dzień (DEMO_KEY) — dla TerraLens irrelewantne.

### [2026-04-27] CDN dla PMTiles — Hugging Face Datasets zamiast R2/B2

- **Decyzja:** Cloudflare R2 i Backblaze B2 odrzucone — oba wymagają karty kredytowej dla publicznych bucketów. Wybrano **Hugging Face Datasets** jako CDN dla plików PMTiles.
- **Repo:** `Piotr1686/terralens-data` (dataset, public) — do utworzenia przez `huggingface_hub.create_repo()`
- **Upload:** `hf_api.upload_file(path_or_fileobj, path_in_repo, repo_id, repo_type="dataset")`
- **Public URL:** `https://huggingface.co/datasets/Piotr1686/terralens-data/resolve/main/{filename}`
- **Range Requests:** obsługiwane przez HF CDN (Cloudflare) — wymagane przez pmtiles.js ✓
- **Auth:** token HF write (`HF_TOKEN` w `.env`), generowany na `huggingface.co/settings/tokens`
- **Zmienne .env:** `HF_TOKEN`, `HF_REPO_ID=Piotr1686/terralens-data`, `HF_PUBLIC_URL=https://huggingface.co/datasets/Piotr1686/terralens-data/resolve/main`
- **Uwaga:** Stare zmienne `R2_*` pozostają w `.env.example` jako fallback, ale dla MVP używamy HF.
