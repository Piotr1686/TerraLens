# 🌍 TerraLens — PROJECT BRIEF
# v3.2 — pointer do Session Setup (standalone dokument)

---

## 🎯 Wizja projektu

**Nazwa:** TerraLens
**Elevator pitch:** Interaktywny 3D eksplorator zmian powierzchni Ziemi — łączy dane satelitarne NASA z AI upscalingiem (model trenowany na satellite imagery) i inteligentną detekcją zmian, prezentując cinematic timelapse, heatmapy i statystyki na obracalnym globie.
**Wow-factor:** Otwierasz stronę → progress bar ładuje tekstury 3 regionów → kamera leci na Amazonię → widzisz timelapse deforestacji z heatmapą → panel pokazuje "-34% zieleni, 2015–2024" → przelot do Dubaju → rozrost miasta. Cinematic guided tour z preloadem assetów.

---

## 🎬 10-Second Hook

Konkretny scenariusz pierwszych 10 sekund — co użytkownik widzi i odczuwa, sekunda po sekundzie. To jest umowa między wizją a implementacją: frontend musi dostarczyć tę sekwencję, pipeline musi mieć dane do jej wyrenderowania.

| Czas | Scena | Co się dzieje technicznie |
|------|-------|--------------------------|
| **0-2s** | Czarne tło z subtelnym grid. Centralnie: progress bar z miniaturą Amazonii. Tekst "Ładowanie Amazonii... 30%" | `Promise.all([amazonia, dubai, arctic])` — preload tekstur + DEM + JSONów |
| **3-4s** | Fade-in globu. Widoczna Ziemia obraca się powoli wokół osi Y. Podświetlenie z lewej (symulacja słońca). SRTM DEM daje widoczny relief | Pierwszy render sceny, kamera na zoom "planetarnym" (r=3.5) |
| **5-7s** | Kamera zaczyna cinematic lot — krzywa Beziera z easing, nie linia prosta. Cel: Amazonia. Glob obraca się synchronicznie, żeby region był w centrum przy arrival | `FlyToInterpolator` (Deck.gl) lub TWEEN (R3F) z `easeInOutCubic` |
| **8-9s** | Arrival nad Amazonią. Tekstura timelapse startuje automatycznie (rok 2015 → 2024). Heatmapa SSIM pojawia się jako overlay z gradientem opacity 0→0.7 | Texture swap z cross-fade; heatmap layer fade-in |
| **10s** | Panel boczny slide-in z prawej. Wielki liczbowy highlight: **"-34% zieleni"**. Pod spodem: "Amazonia • 2015–2024 • MODIS NDVI". Użytkownik może przerwać tour klikiem | shadcn/ui Card z `transform: translateX()` animation |

### Kryteria sukcesu 10-Second Hook
- **Mobile-safe:** sekwencja działa płynnie na mid-range Android (Snapdragon 7-gen). Jeśli nie — fallback do static preview PNG w sekundach 0-4.
- **Skip-safe:** użytkownik może przerwać tour w dowolnym momencie bez crasha. Tour jest delightful, nie przeszkadzający.
- **Replay-safe:** kliknięcie "Restart Tour" w panelu bocznym → powrót do sekundy 0 bez reloadu strony.

---

## 🧩 Typ projektu

**Hybrid: CLI Pipeline + Web Dashboard**

- **CLI (Python):** Pobieranie danych NASA (GIBS tiles + MODIS NDVI), AI upscaling (Satlas ESRGAN), detekcja zmian (SSIM z cloud masking + histogram matching), eksport do PMTiles — offline, na lokalnym GPU.
- **Web Dashboard (React):** Statyczny 3D globe serwujący pre-computed wyniki. Deploy: frontend na Vercel/GitHub Pages, dane na Cloudflare R2.

**Frontend stack:**
- React + TypeScript
- MVP: React Three Fiber lub Deck.gl GlobeView (decyzja po obowiązkowym PoC w tygodniu 3)
- Faza 2: Deck.gl GlobeView "Explore Mode" (jeśli MVP na R3F)
- Tailwind CSS + shadcn/ui

---

## 🤖 Technologie AI / Modele

### MVP Pipeline (Faza 1)

| Krok | Narzędzie | VRAM | Typ |
|------|-----------|------|-----|
| Wizualizacja | NASA GIBS — warstwy **HLS RGB** (True Color, 30m/px) | 0 | API tiles |
| Detekcja zmian (primary) | NASA GIBS — **MODIS NDVI** (gotowy produkt, 250m, seria od 2000) | 0 | API tiles |
| Super-resolution | **Satlas ESRGAN** lub **DSen2** FP16, tiled 512×512 z overlap 64px | ~1.5GB | AI model (satellite-trained) |
| Teren 3D | NASA SRTM DEM (prawdziwe dane wysokościowe) | 0 | Dane publiczne |
| Detekcja zmian (strukturalna) | **SSIM** z preprocessing: cloud masking (QA band) + histogram matching + gaussian blur | 0 | Algorytm |
| Statystyki | Change Vector Analysis w przestrzeni LAB (histogramy, % pokrycia) | 0 | Algorytm |

**Peak VRAM:** ~1.5GB (jeden model, ładowany na czas procesowania)

**Strategia VRAM:** Tiled processing 512×512 z overlap 64px, FP16, singleton lazy loading, batch-size-1, `torch.cuda.empty_cache()` + `gc.collect()` co 2 tile'y, `@vram_safe` decorator.

### Kluczowe zmiany vs v2.0 — uzasadnienia

**Dlaczego Satlas ESRGAN zamiast Real-ESRGAN?**
Real-ESRGAN trenowany na zdjęciach naturalnych i anime — na danych satelitarnych halucynuje tekstury (tworzy budynki z drzew, rzeki z dróg). Satlas ESRGAN (Allen AI) trenowany specyficznie na Sentinel-2 / Landsat — rozumie semantykę terenu, preservuje NDVI-relevant features. Swap na 1 dzień.

**Dlaczego MODIS NDVI jako primary change detection?**
NASA GIBS serwuje HLS jako wizualizacje RGB, NIE surowe pasma spektralne. Nie da się policzyć NDVI z GIBS HLS tiles. MODIS NDVI to gotowy, przetworzony produkt w GIBS — seria od 2000, cloud-free composite, zero dodatkowej obróbki. HLS RGB zostaje do wizualizacji ("ładne obrazki" na globie).

**Dlaczego cloud masking + histogram matching przed SSIM?**
Bez cloud masking: SSIM traktuje chmury jako "zmianę struktury" → fałszywe pozytywy. Bez histogram matching: zmiana pory roku (lato→zima) daje 30% "zmiany" mimo braku realnych zmian terenu. Pipeline: (1) cloud mask z QA band → NaN, (2) histogram matching do daty referencyjnej, (3) gaussian blur σ=1.5, (4) SSIM na zamaskowanych, wyrównanych danych. ~15 linii kodu, redukcja false positives ~60%.

**Dlaczego overlap 64px przy tiled processing?**
Bez overlap: widoczne szwy na granicach tile'ów w heatmapach i upscalowanych obrazach. 64px overlap z blendingiem eliminuje artefakty.

### Full Pipeline (Faza 2–3)

| Krok | Narzędzie | VRAM | Faza |
|------|-----------|------|------|
| Surowe pasma HLS | pystac-client + NASA Earthdata (NIR+Red → true NDVI) | 0 | Faza 2 |
| Interpolacja (tylko eksport wideo) | RIFE 4.x FP16 | ~1GB | Faza 2 |
| Segmentacja | SegFormer-B2 (land cover) | ~1.5GB | Faza 2 |
| CPU inference | OpenVINO dla lżejszych modeli | 0 VRAM | Faza 2 |
| Opisy AI | Llama-3.2 3B GGUF Q4_K_M lub Phi-3.5 (CPU, nowsze niż Mistral 7B) | 0 (3GB RAM) | Faza 3 |

**Modele ładowane sekwencyjnie** — nigdy więcej niż jeden w VRAM.

**Nota o RIFE:** Interpolacja klatek między zdjęciami satelitarnymi nie ma sensu wizualnego — zmiany terenu są nieciągłe (deforestacja = skok, nie gradient). RIFE dodaje "motion blur" bez wartości informacyjnej. Na globie: cross-fade (opacity blend) realizowany we frontendzie. RIFE wyłącznie do eksportu raportów wideo (MP4) w Fazie 2.

### Fine-tuning: NIE w MVP
SegFormer land cover fine-tuning potencjalnie w Fazie 2.

---

## 🗂️ Architektura danych

### Źródła danych — ścieżki dostępu

| Dane | Źródło | Dostęp | Użycie |
|------|--------|--------|--------|
| HLS RGB (wizualizacja) | NASA GIBS WMTS | Tiles HTTP, bez autentykacji | Tekstury na globe, timelapse |
| MODIS NDVI (change detection) | NASA GIBS WMTS | Tiles HTTP, bez autentykacji | Heatmapy zmian, statystyki |
| MODIS True Color (fallback) | NASA GIBS WMTS | Tiles HTTP, bez autentykacji | Długie serie od 2000 |
| SRTM DEM (teren 3D) | NASA Earthdata | Download, wymaga login | Displacement na globie |
| Surowe HLS (Faza 2) | NASA Earthdata via pystac-client | STAC API, wymaga login | True NDVI z pasm NIR+Red |

### Przechowywanie
- **Tile'y i obrazy:** Filesystem z konwencją katalogów (processing) → **PMTiles** (eksport/deploy)
- **Metadata:** SQLite (`cache.db`) — co pobrano, processing status, daty, `expires_at` z TTL 30 dni
- **Pattern:** `db/queries.py` (bez ORM)

### Nota o PMTiles raster pipeline
Tippecanoe obsługuje tylko dane wektorowe. Dla rasteru: użyj **Python library `pmtiles`** z custom skryptem `tiles_to_pmtiles.py`. Alternatywnie: zbuduj standardową strukturę XYZ + WebP, potem bundluj do PMTiles. W Fazie 2 rozważ migrację na **COG (Cloud Optimized GeoTIFF)** — lepsze dla multi-band i time-series.

### Struktura `data/`
```
data/
├── tiles/                  # surowe tile'y NASA GIBS
│   ├── HLS_RGB/{date}/{z}/{x}/{y}.png
│   ├── MODIS_NDVI/{date}/{z}/{x}/{y}.png
│   └── MODIS_Terra/{date}/{z}/{x}/{y}.png
├── processed/              # upscaled, heatmapy SSIM/NDVI
│   └── {region}/
│       ├── {date}_upscaled.png
│       ├── {date}_ssim_heatmap.png
│       └── {date}_ndvi_diff.png
├── dem/                    # NASA SRTM elevation data
├── export/
│   ├── {region}.pmtiles    # skonsolidowane tilesety
│   ├── {region}/
│   │   ├── timeline.json   # metadata: daty, cloud cover, źródła
│   │   ├── changes.json    # wyniki SSIM/NDVI + CVA
│   │   └── tour.json       # parametry kamery guided tour
│   └── dem/
│       └── {region}_dem.png
└── cache.db                # SQLite metadata z TTL
```

### Cache strategia
1. **Tile cache** — klucz `{layer}/{date}/{z}/{x}/{y}`, plik istnieje + TTL nie wygasł → skip
2. **Processed cache** — `data/processed/`, przetworzony → skip
3. **Export cache** — `data/export/`, PMTiles + JSONy gotowe do uploadu na R2
4. **CLI flag:** `--refresh` wymusza ponowne pobranie mimo ważnego TTL

### Wersjonowanie danych
- `data/` w `.gitignore`
- Reproducible pipeline: `python -m terralens fetch && python -m terralens process && python -m terralens export`
- Eksport wersjonowany: `amazonia_v{timestamp}.pmtiles` + `manifest.json` z mapowaniem `latest → plik`
- DVC rozważane w Fazie 3

---

## 🎬 Frontend — strategia z obowiązkowym PoC

### Decyzja frontendowa: PoC w tygodniu 3

Brief v2.0 zakładał R3F jako pewnik. Po audycie 6 agentów — 4 z 6 rekomenduje Deck.gl od MVP. Argument o długu technologicznym (dwa silniki 3D) jest realny.

**Rozwiązanie:** Tydzień 3, dni 1-2 = **obowiązkowy PoC obu opcji:**

| Kryterium | Test |
|-----------|------|
| Cinematic camera tour | Czy Deck.gl `FlyToInterpolator` daje akceptowalny lot po łuku (nie po linii prostej)? |
| DEM displacement | Czy Deck.gl `TerrainLayer` lub custom shader obsługuje SRTM na globie? |
| Texture swap (timeline) | Czy opacity blend między datami działa płynnie? |
| Mobile performance | Czy globe renderuje się na mid-range Android? |

**Jeśli Deck.gl ≥ 85% jakości R3F → Deck.gl zostaje jako jedyny silnik.**
**Jeśli Deck.gl < 85% → R3F na MVP, Deck.gl "Explore Mode" w Fazie 2.**

### Niezależnie od wyniku PoC: Guided Tour z preloadem

```
Sekwencja startowa:
1. Loader z progress barem ("Ładowanie Amazonii... 30%")
2. Pre-load WSZYSTKICH tekstur dla 3 regionów (Promise.all)
3. Opcjonalnie: static preview (PNG) jako placeholder
4. Dopiero po załadowaniu → start cinematic camera tour
5. Po tourze → użytkownik przejmuje kontrolę
```

**"3 sekundy do wow" = 3 sekundy PO załadowaniu, nie od otwarcia strony.** Loader musi być estetyczny (progress + nazwa regionu + miniaturka).

### Story Mode (MVP)
- Cinematic Guided Tour: Amazonia → Dubai → Arktyka
- Timeline slider — cross-fade między datami (opacity blend, zero RIFE)
- Heatmapa zmian (SSIM/NDVI) jako warstwa na globie
- Panel boczny: statystyki + region info (shadcn/ui)

### Explore Mode (Faza 2)
- Deck.gl GlobeView + TileLayer — dowolna lokalizacja
- Dane pobierane on-demand (surowe HLS via pystac-client → processing → display)
- Wymaga lekkiego backendu (Cloudflare Workers lub Vercel Serverless)

---

## 🚀 Deployment — architektura split

```
┌─────────────────────────────────┐
│  Frontend (React bundle ~800KB) │
│  Deploy: Vercel lub GitHub Pages│
│  (statyczny HTML/JS/CSS)        │
└──────────────┬──────────────────┘
               │ HTTP Range Requests
               ▼
┌─────────────────────────────────┐
│  Data (PMTiles + DEM + JSONs)   │
│  Store: Cloudflare R2           │
│  CDN: Cloudflare (global)       │
│  Koszt: $0 (do 10GB free tier)  │
│  CORS: Enabled                  │
└─────────────────────────────────┘
               ▲
               │ Upload (CLI: terralens deploy)
┌─────────────────────────────────┐
│  CLI Pipeline (lokalne GPU)     │
│  fetch → process → export       │
│  → upload do R2                 │
└─────────────────────────────────┘
```

**Dlaczego nie GitHub Pages dla danych?** Limit 1GB na repo, 100MB na plik, 100GB bandwidth/miesiąc. 3 regiony × 10 lat to 2-5 GB. R2 daje 10GB free, zero egress fees, natywne HTTP Range Requests.

**GitHub Pages / Vercel** wystarczy dla frontendu — bundle React to ~800KB.

---

## 🔗 Inspiracje / kontekst

### Źródła danych
- NASA GIBS WMTS: https://wiki.earthdata.nasa.gov/display/GIBS
- NASA GIBS MODIS NDVI layers: https://gibs.earthdata.nasa.gov
- NASA HLS (Harmonized Landsat Sentinel): https://hls.gsfc.nasa.gov/
- NASA Earthdata (STAC access, Faza 2): https://search.earthdata.nasa.gov/
- NASA SRTM DEM: https://www.earthdata.nasa.gov/sensors/srtm

### Referencyjne technologie
- Satlas (Allen AI satellite SR): https://github.com/allenai/satlas
- React Three Fiber: https://docs.pmnd.rs/react-three-fiber
- Deck.gl GlobeView: https://deck.gl/docs/api-reference/core/globe-view
- PMTiles: https://github.com/protomaps/PMTiles
- PMTiles Python (raster): https://github.com/protomaps/PMTiles/tree/main/python
- SSIM (scikit-image): https://scikit-image.org/docs/stable/api/skimage.metrics.html
- pystac-client (Faza 2): https://github.com/stac-utils/pystac-client
- Cloudflare R2: https://developers.cloudflare.com/r2/

### Czego NIE chcę
- Kolejnego flat map viewera bez AI
- Gradio/Streamlit demo bez własnego frontendu
- Over-engineered backendu na MVP — zero FastAPI, zero Kubernetes, zero chmury
- Fine-tuningu modeli w MVP — pretrained only
- Naiwnego pixel-diff na danych satelitarnych
- Real-ESRGAN na danych satelitarnych (halucynacje)
- Milionów PNG-ów w repozytorium GitHub
- RIFE na timelapse satelitarnym (bezsensu — zmiany nieciągłe)
- CesiumJS (enterprise GIS aesthetic, nie portfolio creative)

---

## ❓ Pytania / niewiadome

| Priorytet | Pytanie |
|-----------|---------|
| 🔴 Wysoki | Które konkretne warstwy MODIS NDVI w GIBS dają cloud-free monthly composite? Layer IDs |
| 🔴 Wysoki | Satlas ESRGAN vs DSen2 — który lepiej na RTX 3050 4GB? Benchmark na 10 tile'ach |
| 🔴 Wysoki | PoC tydzień 3: Deck.gl GlobeView cinematic tour — czy `FlyToInterpolator` daje lot po łuku? |
| 🔴 Wysoki | PMTiles raster pipeline: `pmtiles` Python lib → ile pracy na custom `tiles_to_pmtiles.py`? |
| 🟡 Średni | SSIM + histogram matching: jaki threshold daje czytelną heatmapę na MODIS NDVI? |
| 🟡 Średni | Cloudflare R2: konfiguracja CORS dla HTTP Range Requests z custom domain |
| 🟡 Średni | Estymacja storage: 3 regiony × 10 lat × monthly → ile GB w PMTiles z WebP? |
| 🟢 Niski | pystac-client + NASA Earthdata Login — jak skomplikowany jest auth flow? (Faza 2) |
| 🟢 Niski | COG vs PMTiles dla Fazy 2 Explore Mode — który lepiej z Deck.gl TileLayer? |
| 🟢 Niski | LLM opisy Faza 3: Llama-3.2 3B vs Phi-3.5 — który szybszy na CPU? |

---

## 🚀 Strategia realizacji

### Faza 1 — MVP "Demo-ready" (~5 tygodni)

**Tydzień 1–2: CLI Pipeline**
- [ ] NASA GIBS tile downloader: HLS RGB (wizualizacja) + MODIS NDVI (change detection)
- [ ] SQLite cache z TTL (`expires_at`, `--refresh` flag)
- [ ] Satlas ESRGAN upscale (tiled 512×512, overlap 64px, FP16, batch-size-1)
- [ ] `@vram_safe` decorator + `torch.cuda.empty_cache()` + `gc.collect()` co 2 tile'y
- [ ] SSIM pipeline: cloud mask (QA band) → histogram matching → gaussian blur → SSIM
- [ ] NDVI diff z MODIS NDVI tiles (prosta różnica między datami)
- [ ] Change Vector Analysis w przestrzeni LAB (statystyki % pokrycia)
- [ ] Eksport do PMTiles (custom `tiles_to_pmtiles.py` z Python `pmtiles` lib)
- [ ] Wersjonowany eksport: `{region}_v{timestamp}.pmtiles` + `manifest.json`
- [ ] CLI z Rich: `terralens fetch`, `terralens process`, `terralens export`
- [ ] Rate limiting: `time.sleep(0.1)` między requestami GIBS

**Tydzień 3: Frontend PoC + decyzja**
- [ ] **Dzień 1-2: PoC Deck.gl GlobeView** — globe + 1 region + camera animation + DEM
- [ ] **Dzień 3: PoC R3F** (jeśli Deck.gl < 85%) — globe + 1 region + cinematic camera
- [ ] **Dzień 4: DECYZJA** — który silnik na MVP (na podstawie PoC, nie debaty)
- [ ] **Dzień 5: Setup wybranego stacku** — project scaffold, routing, state management

**Tydzień 4: Frontend budowa**
- [ ] 3D globe z teksturą satelitarną (wybrany silnik)
- [ ] SRTM DEM displacement mapping
- [ ] **Preload phase:** progress bar → `Promise.all(textures)` → start tour
- [ ] Cinematic Guided Tour (Amazonia → Dubai → Arktyka)
- [ ] Timeline slider — cross-fade między datami (opacity blend)
- [ ] Heatmapa zmian (SSIM/NDVI) jako warstwa na globie
- [ ] Panel boczny: statystyki + region info (shadcn/ui)

**Tydzień 5: Polish & Deploy**
- [ ] 3 pre-computed regiony: Amazonia, Dubai, Arktyka
- [ ] Upload PMTiles + DEM + JSONs do Cloudflare R2
- [ ] Frontend deploy na Vercel lub GitHub Pages
- [ ] README z GIF-ami / screencastem
- [ ] `environment.yml` (conda) dla reproducible setup

**Deliverable:** Link do działającego 3D globu z cinematic tour przez 3 regiony, dane na R2.

### Faza 2 — "Portfolio-ready" (+3–4 tygodnie)
- [ ] Deck.gl GlobeView "Explore Mode" — dowolna lokalizacja
- [ ] pystac-client + NASA Earthdata → surowe HLS pasma → true NDVI
- [ ] Rozważenie migracji PMTiles → COG (Cloud Optimized GeoTIFF)
- [ ] RIFE interpolacja → eksport wideo MP4 (nie do globe timelapse)
- [ ] OpenVINO dla RIFE na CPU
- [ ] SegFormer land cover segmentation
- [ ] Lekki backend: Cloudflare Workers lub Vercel Serverless (on-demand processing)
- [ ] Testy, CI/CD, docstringi

### Faza 3 — "Open-source-ready" (+4–6 tygodni)
- [ ] FastAPI backend → live processing
- [ ] Llama-3.2 3B GGUF lub Phi-3.5 do AI-generowanych opisów zmian (CPU)
- [ ] DVC wersjonowanie danych
- [ ] Plugin system (custom warstwy, modele)
- [ ] Dokumentacja MkDocs
- [ ] Hugging Face Space demo

---

## ⚙️ Hardware Execution Policy

```
GPU: NVIDIA RTX 3050 Laptop — 4GB VRAM (bottleneck)
RAM: 32GB DDR4 — główny zasób
CPU: Intel i5-12500H (12C/16T)

Realne VRAM available:
- System overhead: ~0.5GB
- PyTorch CUDA context: ~0.5GB
- Fragmentation: ~0.5GB
- Available for models: ~2.5GB
→ Tylko JEDEN model na raz, max ~2GB FP16

Zasady:
- Max 1 model w VRAM jednocześnie (singleton lazy loading)
- Tiled processing: 512×512 px z overlap 64px
- Batch size: 1 (zawsze)
- Precision: FP16 domyślnie
- VRAM cleanup: torch.cuda.empty_cache() + gc.collect() co 2 tile'y
- @vram_safe decorator
- Kwantyzacja LLM: GGUF Q4_K_M → Q5_K_M
- Fallback: ONNX Runtime INT8 (~300MB VRAM) jeśli OOM na FP16
- Faza 2: multiprocessing (osobny proces per model) jeśli singleton swap zawodzi
```

---

## 🏗️ Proponowana struktura projektu

```
TerraLens/
├── CLAUDE.md                   # Claude Code CLI config
├── PROJECT_BRIEF.md            # ten plik
├── Makefile                    # build, fetch, process, export, deploy
├── pyproject.toml              # Python dependencies
├── environment.yml             # Conda environment (reproducible)
├── src/
│   └── terralens/
│       ├── __init__.py
│       ├── __main__.py         # CLI entrypoint
│       ├── cli/                # Rich CLI commands
│       │   ├── fetch.py        # terralens fetch
│       │   ├── process.py      # terralens process
│       │   ├── export.py       # terralens export (→ PMTiles)
│       │   └── deploy.py       # terralens deploy (→ R2 upload)
│       ├── engines/            # AI models (Satlas ESRGAN, RIFE, SegFormer)
│       │   └── satlas_esrgan.py
│       ├── processors/         # SSIM, NDVI, CVA, tile processing
│       │   ├── ssim.py         # cloud mask + histogram match + SSIM
│       │   ├── ndvi.py         # MODIS NDVI diff
│       │   └── cva.py          # Change Vector Analysis (LAB)
│       ├── models/             # Singleton model loaders
│       ├── fetchers/           # NASA GIBS, Earth API, SRTM
│       │   ├── gibs.py         # WMTS tile fetcher (HLS RGB + MODIS NDVI)
│       │   └── srtm.py         # DEM downloader
│       ├── db/
│       │   └── queries.py      # SQLite queries (z TTL support)
│       └── export/
│           ├── pmtiles.py      # tiles_to_pmtiles.py (raster)
│           └── manifest.py     # Wersjonowany manifest.json
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── Globe.tsx       # R3F lub Deck.gl (po PoC)
│   │   │   ├── GuidedTour.tsx  # Cinematic camera animation
│   │   │   ├── Preloader.tsx   # Progress bar + texture preload
│   │   │   ├── Timeline.tsx    # Date slider (cross-fade)
│   │   │   ├── HeatmapLayer.tsx
│   │   │   ├── StatsPanel.tsx
│   │   │   └── RegionCard.tsx
│   │   ├── data/               # Pre-computed JSONs (timeline, changes, tour)
│   │   └── hooks/
│   │       ├── useTour.ts      # Camera animation logic
│   │       └── usePreload.ts   # Texture preloading
│   └── public/
│       └── fallback/           # Static preview PNGs (placeholder)
├── data/                       # .gitignore'd
│   ├── tiles/
│   ├── processed/
│   ├── dem/
│   ├── export/
│   └── cache.db
└── tests/
    ├── test_ssim.py
    ├── test_ndvi.py
    ├── test_fetchers.py
    └── test_export.py
```

---

## 🧪 PoC Results — Core Risk Validation

**Core Risk identyfikowany:** Czy **Satlas ESRGAN** w trybie FP16 mieści się w 4GB VRAM RTX 3050 przy tiled processing 512×512 z overlap 64px, i czy VRAM pozostaje stabilny przez wielokrotne iteracje (brak wycieków, fragmentacji)?

**Uzasadnienie:** Brief deklaruje ~1.5GB VRAM dla Satlas ESRGAN, ale to szacunek z dokumentacji modelu, nie pomiar na docelowym sprzęcie. Jedno uruchomienie nie wykryje akumulacji tensorów w CUDA cache. Potrzebny test z pętlą 3-iteracyjną PRZED kodowaniem właściwego pipeline'u.

### Skrypt testowy (do uruchomienia przed Fazą 6)

`scripts/poc_satlas.py`:

```python
import torch
import subprocess
import gc

def vram_mb():
    return torch.cuda.memory_allocated() / 1e6

# 1. Załaduj Satlas ESRGAN (lub DSen2 — porównaj oba)
# Dokładne API zależy od wybranego wariantu — patrz github.com/allenai/satlas
from satlas_super_resolution import load_model  # przykładowy import
model = load_model(variant="esrgan_x4").half().cuda()
print(f"Po załadowaniu modelu:      {vram_mb():.0f} MB")

# 2. Pętla 3-iteracyjna — wykrywa fragmentację i akumulację
for i in range(3):
    tile = torch.randn(1, 3, 512, 512).half().cuda()
    with torch.no_grad(), torch.inference_mode():
        output = model(tile)
    # Symulacja cleanup między tile'ami (jak w production pipeline):
    del tile
    torch.cuda.empty_cache()
    gc.collect()
    print(f"Iter {i+1} (po cleanup):       {vram_mb():.0f} MB")

# 3. Pomiar z nvidia-smi (truth source — pokazuje też CUDA context)
print("\n--- nvidia-smi truth ---")
print(subprocess.check_output(
    ["nvidia-smi", "--query-gpu=memory.used,memory.total",
     "--format=csv,noheader"]
).decode())

print(f"\nOutput shape: {output.shape}")
print("✅ PoC PASSED" if output is not None else "❌ FAILED")
```

### Szablon wyników (wypełnij po uruchomieniu skryptu)

```markdown
## PoC Results — wypełnione po uruchomieniu

**Data testu:** [YYYY-MM-DD]
**Sprzęt:** RTX 3050 Laptop 4GB, i5-12500H, 32GB RAM
**Model testowany:** [Satlas ESRGAN x4 / DSen2 — który wybrałeś]
**Precyzja:** FP16
**Rozmiar tile'a:** 512×512 (+ opcjonalnie test z 256×256)

### Pomiary VRAM (PyTorch allocator):
- Po załadowaniu modelu:           [X] MB
- Po iteracji 1 (z cleanup):       [X] MB
- Po iteracji 2 (z cleanup):       [X] MB
- Po iteracji 3 (z cleanup):       [X] MB
- Delta między iteracjami:         [X] MB (stabilny ≤ 50MB / rosnący > 50MB)

### Pomiary VRAM (nvidia-smi — z CUDA context):
- memory.used po teście:           [X] MB / 4096 MB
- Procent wykorzystania:           [X]%

### Wynik:
- [ ] ✅ PASS — VRAM stabilny, mieści się w budżecie (headroom ≥ 500MB)
- [ ] ⚠️ WARN — działa, ale VRAM rośnie lub headroom < 500MB
- [ ] ❌ FAIL — OOM lub model nie ładuje się

### Wnioski i akcje:

[Jeśli PASS:] Przechodzimy do Fazy 6 z obecnym briefem.

[Jeśli WARN:] Konkretne działania:
- Dodać fallback do ONNX INT8 jeśli headroom < 500MB
- Rozważyć zmniejszenie tile'a do 384×384 lub 256×256
- [inne wnioski]

[Jeśli FAIL:] Powrót do briefu. Opcje:
- Zamiana na DSen2 (jeśli testowałeś Satlas)
- Zamiana na ESRGAN standard (mniejszy, gorsza jakość)
- ONNX Runtime INT8 jako default (CPU lub GPU)
- [inne]
```

### Decyzja blokująca

**Bez PoC Results z wynikiem PASS lub WARN z mitigation plan — NIE rozpoczynaj Fazy 6 (setup projektu w Claude Code).** To chroni przed odkryciem w tygodniu 2, że kluczowy model nie działa na sprzęcie.

---

## 🔧 Faza 6 — Session Setup (osobny dokument)

Po otrzymaniu PASS z PoC, przed pierwszą sesją Claude Code: wykonaj `terralens-session-setup-prompt.md` — standalone dokument instalujący system zarządzania sesjami.

**Co instaluje:** `CLAUDE.md`, `MEMORY.md`, `last_session.md` + 4 komendy slash (`/start`, `/save`, `/end`, `/status`) w `.claude/commands/`.

**Dlaczego osobny dokument:** Instrukcja jest imperatywna ("utwórz plik X") i jednorazowa. Brief jest deklaratywny ("projekt używa stacku A"). Trzymanie ich osobno zapobiega podwójnemu wykonaniu przy `/init` i zachowuje czytelność briefu jako referencji w dalszej pracy.

**Procedura:**
1. Skopiuj `PROJECT_BRIEF.md` + `terralens-session-setup-prompt.md` do katalogu projektu
2. Uruchom `claude`, wklej zawartość session setup promptu
3. Claude Code utworzy strukturę plików
4. Zamknij sesję, otwórz ponownie, wpisz `/start` — weryfikacja działania
5. Uzupełnij "Cel bieżący" w wygenerowanym `CLAUDE.md`

---



| Wersja | Źródło zmian | Kluczowe zmiany |
|--------|-------------|-----------------|
| v1.0 | Sesja decyzyjna Claude | Pierwotny brief: Real-ESRGAN, pixel-diff, MODIS, R3F, GitHub Pages |
| v2.0 | Cross-review Claude × Gemini | SSIM zamiast pixel-diff, HLS primary, PMTiles, Guided Tour, strategia dwutrybowa R3F/Deck.gl |
| v3.0 | Audyt 6 agentów (Claude × Gemini × DeepSeek × Grok × Kimi × GPT) | **Satlas ESRGAN** zamiast Real-ESRGAN, **MODIS NDVI** jako primary change detection (GIBS HLS nie daje pasm NIR), **cloud masking + histogram matching** przed SSIM, **Cloudflare R2** zamiast GitHub Pages dla danych, **obowiązkowy PoC Deck.gl** w tygodniu 3, **preload phase** w frontendzie, **overlap 64px** w tiled processing, **TTL w cache**, **wersjonowany eksport**, RIFE tylko do eksportu wideo, LLM update do Llama-3.2/Phi-3.5, COG jako ścieżka Fazy 2 |
| v3.1 | Alignment z workflow v3.5 (własny self-work) | Dodano sekcję **🎬 10-Second Hook** (operacjonalizacja wow-factora na konkretny scenariusz sekunda-po-sekundzie) + szablon **🧪 PoC Results** dla walidacji Core Risk (Satlas ESRGAN na RTX 3050) przed rozpoczęciem Fazy 6. Brak zmian architektonicznych — tylko precyzja i bezpieczeństwo procesu. |
| v3.2 | Integracja z Session State Management | Dodano sekcję **🔧 Faza 6 — Session Setup** jako wskaźnik do standalone dokumentu `terralens-session-setup-prompt.md`. Świadomie bez kopiowania pełnej instrukcji — separacja warstw (brief = deklaratywny, session setup = imperatywny i jednorazowy). |

---

## 🏆 Źródła rekomendacji (dla transparentności)

| Zmiana w v3.0 | Zaproponowana przez | Zaakceptowana po weryfikacji |
|---------------|---------------------|------------------------------|
| Satlas ESRGAN | Grok, Kimi | Tak — satellite-trained > general SR |
| MODIS NDVI primary | DeepSeek, Grok | Tak — GIBS HLS nie ma pasm NIR |
| Cloud masking | Kimi, Grok, DeepSeek | Tak — QA band eliminuje cloud false positives |
| Histogram matching | DeepSeek | Tak — 10 linii kodu, -60% seasonal false positives |
| Cloudflare R2 | DeepSeek, Kimi, GPT | Tak — GH Pages limit 1GB, R2 free 10GB |
| PoC Deck.gl | DeepSeek, Grok, Kimi | Tak — decyzja po PoC, nie po debacie |
| Texture preloading | DeepSeek | Tak — "3s do wow" wymaga preloadu |
| Overlap 64px | Grok | Tak — eliminuje szwy tile'ów |
| RIFE tylko do wideo | DeepSeek | Tak — satellite changes nieciągłe |
| TTL w cache | DeepSeek | Tak — NASA aktualizuje dane |
| Wersjonowany eksport | DeepSeek | Tak — manifest.json z latest pointer |
| PMTiles raster nota | Grok | Tak — tippecanoe = vector only |
