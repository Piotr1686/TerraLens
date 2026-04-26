# 🗺️ MASTER_PLAN.md — TerraLens Execution Plan
# Plan wykonawczy krok-po-kroku dla Claude Code
# Bazuje na PROJECT_BRIEF.md v3.2

---

## 📖 Jak używać tego dokumentu

**Dla Claude Code:**
- Ten plik jest **mapą wykonawczą projektu** — czytaj go po każdym `/start`, przed rozpoczęciem nowego zadania.
- Pracujemy **sprintami** (numerowane S0–S9). W jednej sesji zwykle robimy 1–3 taski, nie cały sprint.
- Każdy task ma unikalne ID (`T<sprint>.<numer>`), Definition of Done (DoD) i testy akceptacyjne.
- **Nigdy nie przeskakuj Dependencies** — jeśli T2.3 wymaga T2.1 gotowego, sprawdź najpierw.
- **Po każdym ukończonym tasku:** aktualizuj status w tym pliku (`✓ DONE` / `⟳ IN PROGRESS` / `✗ BLOCKED`), potem `/save`.
- **Po ukończonym sprincie:** git commit z message `feat(S<n>): <sprint goal>` + aktualizacja MEMORY.md.

**Dla Piotra:**
- Ten plik możesz edytować ręcznie kiedy priorytety się zmienią. Claude Code nie uważa tego za naruszenie.
- Jeśli chcesz dodać task ad-hoc — dopisz jako `T<sprint>.X` (X = litera) żeby nie łamać numeracji.

---

## 🎯 Konwencje pracy

### Kolejność operacji w każdym tasku
```
1. /start (jeśli nowa sesja)
2. Przeczytaj task w MASTER_PLAN.md
3. Sprawdź Dependencies
4. Implementuj
5. Uruchom testy z sekcji "Testing"
6. Zweryfikuj wszystkie punkty z DoD
7. Oznacz task jako ✓ DONE w tym pliku
8. /save (checkpoint)
9. git commit jeśli milestone
10. /end jeśli kończysz sesję
```

### Git message convention
- `feat(T1.2): implement GIBS tile fetcher`
- `fix(T2.3): OOM on large tiles — added empty_cache()`
- `refactor(T4.1): split SSIM pipeline into 3 stages`
- `docs(S5): update MEMORY.md with PMTiles pipeline decision`
- `test(T3.2): add VRAM regression test`

### Kiedy aktualizować MEMORY.md
Tylko gdy:
- Decyzja architektoniczna (wybór biblioteki, wzorca) → sekcja "Architektura"
- Rozwiązanie problemu > 30min debugowania → sekcja "Rozwiązane problemy"
- Odrzucone podejście z uzasadnieniem → sekcja "Odrzucone podejścia"
- Nie zapisuj codziennego postępu (to `last_session.md`)

---

## 🧭 Mapa sprintów — widok z lotu ptaka

| Sprint | Cel | Tygodnie z briefu | Status |
|--------|-----|-------------------|--------|
| **S0** | Pre-flight (PoC + środowisko) | — (przed T1) | ✓ DONE (2026-04-25) |
| **S1** | CLI skeleton + config system | T1 | ✓ DONE (2026-04-25) |
| **S2** | Data fetchers (GIBS + SRTM) | T1–T2 | ✓ DONE (2026-04-25) |
| **S3** | AI upscaling (Satlas ESRGAN) | T2 | ⧗ |
| **S4** | Change detection pipeline | T2 | ⧗ |
| **S5** | Export do PMTiles | T2 | ⧗ |
| **S6** | **Frontend PoC (DECISION GATE)** | T3 | ⧗ |
| **S7** | Frontend build (wybrany silnik) | T3–T4 | ⧗ |
| **S8** | 10-Second Hook polish + preloader | T4 | ⧗ |
| **S9** | Deploy (R2 + Vercel) + 3 regiony | T5 | ⧗ |

Legenda: ✓ DONE · ⟳ IN PROGRESS · ⧗ TODO · ✗ BLOCKED

---

## 🛠️ SPRINT 0 — Pre-flight

**Cel:** Udowodnić że kluczowe elementy techniczne działają PRZED pisaniem pipeline'u.

**Kolejność wykonania (ważna!):** T0.3 → T0.5 (start w tle) → T0.2 → T0.1 → T0.4 → T0.5 (dokończenie po Earthdata approval).

Uzasadnienie: T0.1 (PoC Satlas) wymaga torch+CUDA, które instaluje T0.2. T0.5 (credentials) ma podetap rejestracji Earthdata który może trwać godziny — startuj w tle równolegle z T0.2. T0.3 (git) jest niezależny i może być pierwszy.

### T0.2 — Conda environment setup ✓ DONE (2026-04-20, commit `14057b4`)
- **Dependencies:** brak (lub T0.3 jeśli chcesz mieć już git init)
- **Input:** Stack technologiczny z briefu (Python 3.10, torch, rasterio, scikit-image, itd.)
- **Output:** `environment.yml` + aktywne środowisko `terralens` z torch+CUDA
- **Zrealizowane:** torch 2.6.0+cu124 (CUDA runtime 12.4 na driverze 566.36 / CUDA 12.7) · satlaspretrain-models 0.3.1 · wszystkie core+dev libs · verifier `scripts/verify_t02.py` przeszedł [OK]
- **Implementation:**
  ```bash
  conda create -n terralens python=3.10
  conda activate terralens

  # Krok 1: PyTorch z CUDA (match z driverem — sprawdź `nvidia-smi`)
  # Dla CUDA 12.1:
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

  # Krok 2: Satlas + zależności
  pip install satlaspretrain-models  # lub clone z github.com/allenai/satlas

  # Krok 3: Core libs
  pip install rasterio numpy scikit-image requests tqdm rich typer python-dotenv
  pip install pystac-client pmtiles boto3

  # Krok 4: Dev tools
  pip install pytest pytest-cov pytest-benchmark ruff mypy

  # Krok 5: Export env
  conda env export --no-builds > environment.yml
  ```
- **DoD:**
  - [x] `python -c "import torch; print(torch.cuda.is_available())"` → True
  - [x] `python -c "import torch; print(torch.cuda.get_device_name(0))"` → "NVIDIA GeForce RTX 3050 Laptop GPU"
  - [x] Satlas można zaimportować bez błędu
  - [x] `environment.yml` w root projektu, commitowalny

### T0.1 — PoC Satlas ESRGAN na RTX 3050 ✓ DONE (2026-04-25)
- **Dependencies:** T0.2 (wymaga torch+CUDA+satlas z env `terralens`)
- **Input:** Sekcja `🧪 PoC Results` z PROJECT_BRIEF.md
- **Output:** Wypełniona sekcja PoC Results w briefie (PASS/WARN/FAIL)
- **Implementation:**
  1. `conda activate terralens` (upewnij się że env z T0.2 aktywny)
  2. Utwórz `scripts/poc_satlas.py` (skrypt z briefu, max 50 linii)
  3. Uruchom: `python scripts/poc_satlas.py`
  4. Zapisz output do `scripts/poc_results.txt`
  5. Wypełnij tabelę w briefie (VRAM pomiary, decyzja)
- **DoD:**
  - [x] Skrypt wykonuje 3 iteracje bez OOM
  - [x] Delta VRAM między iteracjami ≤ 50MB (stabilny) — wynik: 0.0 MB
  - [x] nvidia-smi pokazuje headroom ≥ 500MB — wynik: ~3550 MB headroom
  - [x] Sekcja PoC Results w briefie wypełniona
- **Wyniki:** Peak allocated 266 MB / 4294 MB | nvidia-smi peak 551/4096 MB | PASS z dużym zapasem.

### T0.3 — Git init + pre-commit hooks ✓ DONE (2026-04-20, commit `14057b4`)
- **Dependencies:** brak (niezależne od T0.1/T0.2, można zrobić pierwsze)
- **Input:** Standardowy pre-commit stack
- **Output:** Working `.pre-commit-config.yaml` + `.gitignore`
- **Implementation:**
  1. `git init` (jeśli nie było przy session setup) — ✓ 2026-04-19 (branch `master`)
  2. Utwórz `.gitignore` z wpisami: `data/`, `*.pyc`, `__pycache__/`, `.pytest_cache/`, `node_modules/`, `.env`, `CLAUDE.md.backup_*` — ✓ 2026-04-19 (rozszerzony o wagi modeli *.pt, *.onnx, venv, IDE, cookies.txt)
  3. Utwórz `.pre-commit-config.yaml` — ✓ 2026-04-19 (ruff + ruff-format, trailing-whitespace, end-of-file-fixer, check-added-large-files 5MB, check-yaml/toml/json, mixed-line-ending LF)
  4. `pre-commit install` — ✓ 2026-04-20 (hook zainstalowany w `.git/hooks/pre-commit`)
  5. Test: autofix na pierwszym `pre-commit run --all-files` (MASTER_PLAN.md + terralens-session-setup-prompt.md trailing-whitespace, environment.yml mixed-line-ending) → po re-stage wszystkie 10 hooków `Passed` — ✓ 2026-04-20
- **DoD:**
  - [x] `.gitignore` zawiera `data/`
  - [x] Pre-commit działa (test commit przechodzi lub blokuje poprawnie)
  - [x] Pierwszy commit: `chore(S0): pre-flight checks passed + credentials configured` (root-commit `14057b4`, 17 plików, 2630 insertions)

### T0.4 — Smoke test skrypt ✓ DONE (2026-04-25)
- **Dependencies:** T0.2, T0.3
- **Input:** Kluczowe importy z briefu
- **Output:** `scripts/smoke_test.py` (skrypt weryfikujący środowisko)
- **Implementation:**
  ```python
  # scripts/smoke_test.py
  import sys
  checks = []
  # 1. Python version
  checks.append(("Python 3.10+", sys.version_info >= (3, 10)))
  # 2. CUDA available
  import torch; checks.append(("CUDA", torch.cuda.is_available()))
  # 3. VRAM ≥ 3.5GB
  props = torch.cuda.get_device_properties(0)
  checks.append(("VRAM ≥ 3.5GB", props.total_memory / 1e9 >= 3.5))
  # 4. Kluczowe biblioteki
  import rasterio, numpy, skimage, requests, click
  checks.append(("Core libs", True))
  # 5. Wypisz wersje
  for name, ok in checks:
      print(f"{'✓' if ok else '✗'} {name}")
  sys.exit(0 if all(c[1] for c in checks) else 1)
  ```
- **DoD:**
  - [x] `python scripts/smoke_test.py` zwraca 0 — wynik: PASS ✓ (exit 0)
  - [x] Wszystkie 4 checkboxy ✓ — Python 3.10.20 | CUDA torch 2.6.0+cu124 | VRAM 4.29 GB | core libs OK

### T0.5 — Credentials setup ⟳ IN PROGRESS (cz.A ✓ done 2026-04-20, cz.B R2 ⧗ TODO)
- **Dependencies:** brak (można robić równolegle z T0.1 — Earthdata approval może zająć kilka godzin)
- **Status cz.A (Earthdata + placeholders):** ✓ Earthdata konto `piotr1686` authorized (LP DAAC Data Pool, LP DAAC Cumulus, ORNL DAAC Daymet + 5 auto-authorized). `.env.example` commitowalny, `.env` gitignored z wypełnionymi `NASA_EARTHDATA_USER/PASS` + `NASA_API_KEY`. Commit `14057b4`.
- **Status cz.B (Cloudflare R2):** ⧗ TODO — bucket `terralens-data` + API token. R2 potrzebny dopiero dla T5.3 (deploy). Placeholder w `.env` już jest. Można robić kiedykolwiek przed S5.
- **Output:** `.env.example` (commitowalny) + `.env` (gitignored) + `scripts/setup_credentials.md`
- **Rationale:** Blokuje wszystkie dalsze sprinty z network I/O. Earthdata registration + app approval trwa kilka godzin — rób to od razu na starcie.
- **Implementation:**

  **A. NASA GIBS** — NIE wymaga API key. Publiczne WMTS bez auth. Zero setup.

  **B. NASA Earthdata Login** (wymagane dla SRTM DEM w T2.4):
  1. Rejestracja: https://urs.earthdata.nasa.gov/users/new
  2. Po potwierdzeniu email → zaloguj się → Profile → Applications → Authorized Apps
  3. Approve aplikacje (search + "Authorize"):
     - `LP DAAC Data Pool` (SRTM DEM hosting)
     - `LP DAAC Cumulus` (nowsze tiered access)
     - `NASA GIBS` (opcjonalne, dla bezpieczeństwa)
  4. **Zaakceptuj EULAs** — niektóre datasety wymagają osobnej akceptacji (SRTM zwykle nie, ale sprawdź)
  5. Zapisz do `.env`:
     ```
     NASA_EARTHDATA_USER=your_username
     NASA_EARTHDATA_PASS=your_password
     ```
  6. Test: `curl -n -c cookies.txt -b cookies.txt -L https://urs.earthdata.nasa.gov/profile` zwraca 200

  **C. Cloudflare R2** (wymagane dla T5.3 deploy):
  1. Konto: https://dash.cloudflare.com → R2 → Enable (free tier: 10GB storage, 10M Class A ops, 10M Class B ops / miesiąc)
  2. Create bucket: `terralens-data`, location: automatic
  3. Settings → CORS policy (JSON):
     ```json
     [{
       "AllowedOrigins": ["https://*.vercel.app", "http://localhost:*"],
       "AllowedMethods": ["GET", "HEAD"],
       "AllowedHeaders": ["Range", "If-Match", "If-None-Match"],
       "ExposeHeaders": ["Content-Range", "Content-Length", "ETag"],
       "MaxAgeSeconds": 3600
     }]
     ```
  4. R2 → Manage R2 API Tokens → Create API Token:
     - Permissions: Object Read & Write
     - Specify bucket: `terralens-data`
     - TTL: forever (rotate manually)
  5. Zapisz do `.env`:
     ```
     R2_ACCESS_KEY_ID=...
     R2_SECRET_ACCESS_KEY=...
     R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
     R2_BUCKET=terralens-data
     R2_PUBLIC_URL=https://pub-<hash>.r2.dev  # lub custom domain
     ```
  6. Test: `aws s3 ls s3://terralens-data --endpoint-url=$R2_ENDPOINT` (z boto3 credentials) listuje bucket (pusty)

  **D. api.nasa.gov key** (OPCJONALNE, tylko Faza 2 jeśli dodasz Earth Imagery API):
  - GIBS nie używa tego klucza. Dla MVP niepotrzebny.
  - Jeśli już masz z SEED_IDEA — zapisz profilaktycznie: `NASA_API_KEY=...`
  - DEMO_KEY limit: 50 req/dzień. Własny klucz: 1000 req/h. Dla TerraLens to nierelewantne.

  **E. `.env.example`** (commitowalny template):
  ```
  # NASA Earthdata Login (required for SRTM DEM)
  NASA_EARTHDATA_USER=
  NASA_EARTHDATA_PASS=

  # Cloudflare R2 (required for deploy)
  R2_ACCESS_KEY_ID=
  R2_SECRET_ACCESS_KEY=
  R2_ENDPOINT=
  R2_BUCKET=terralens-data
  R2_PUBLIC_URL=

  # api.nasa.gov — OPTIONAL (only for Faza 2 Earth Imagery API)
  # GIBS (primary source) does NOT need this key.
  NASA_API_KEY=
  ```

  **F. `scripts/setup_credentials.md`** — dokumentacja z powyższymi krokami A-D, screenshoty gdzie pomocne, troubleshooting (EULA errors, 401 from Earthdata, CORS failures)

- **DoD:**
  - [ ] `.env.example` commitowalny, wszystkie klucze z pustymi wartościami
  - [ ] `.env` istnieje lokalnie, NIE jest w git (`git status` → not tracked)
  - [ ] Earthdata curl test zwraca 200 (auth działa)
  - [ ] R2 bucket listowanie działa z credentials
  - [ ] `scripts/setup_credentials.md` opisuje wszystkie 4 sekcje + troubleshooting
  - [ ] GIBS sanity check: `curl -o /tmp/test.png "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2023-06-01/250m/6/13/36.jpg"` → zapisuje non-empty plik (bez żadnej auth)

- **Ryzyko i mitigation:**
  - *Earthdata approval timeout* → skontaktuj support earthdata@nasa.gov
  - *R2 egress limits przekroczone* → upgrade na paid tier ($0.015/GB storage, zero egress fees = nadal korzystnie)
  - *CORS błędy w produkcji* → debug przez Network tab, sprawdź Vercel domain match w policy

**🏁 Sprint 0 complete when:** T0.1–T0.5 all ✓. Commit: `chore(S0): pre-flight checks passed + credentials configured`

**📝 MEMORY.md update po S0:** "Zewnętrzne zależności: NASA GIBS (no auth) = primary data source. NASA Earthdata Login wymagany dla SRTM DEM (urs.earthdata.nasa.gov). Cloudflare R2 dla deploy (bucket `terralens-data`). api.nasa.gov key niepotrzebny dla MVP (GIBS to osobny system)."

---

## 🏗️ SPRINT 1 — CLI Skeleton

**Cel:** Struktura katalogów + działający CLI z pustymi komendami (fetch/process/export/deploy).

### T1.1 — Struktura katalogów ✓ DONE (2026-04-25)
- **Dependencies:** S0 complete
- **Output:** Struktura z PROJECT_BRIEF.md sekcja "Proponowana struktura projektu"
- **Implementation:**
  ```bash
  mkdir -p src/terralens/{cli,engines,processors,models,fetchers,db,export}
  mkdir -p frontend/src/{components,data,hooks} frontend/public
  mkdir -p tests scripts data
  touch src/terralens/__init__.py src/terralens/__main__.py
  # __init__.py we wszystkich podkatalogach src/
  ```
- **DoD:**
  - [x] `tree src/` identyczne ze strukturą z briefu
  - [x] Każdy pakiet Python ma `__init__.py`

### T1.2 — pyproject.toml + CLI entrypoint ✓ DONE (2026-04-25)
- **Dependencies:** T1.1
- **Output:** `pyproject.toml` z `[project.scripts]` + `src/terralens/__main__.py`
- **Implementation:**
  1. Utwórz `pyproject.toml` z:
     - name, version (0.1.0), description z briefu
     - dependencies (match z environment.yml)
     - `[project.scripts]` → `terralens = "terralens.__main__:app"`
     - `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest]`
  2. `__main__.py` z Typer app + 4 puste komendy (fetch/process/export/deploy)
  3. `pip install -e .` (editable install)
  4. Test: `terralens --help` wyświetla 4 komendy
- **DoD:**
  - [x] `terralens --help` działa z poziomu dowolnego katalogu (pip install -e .; uwaga: conda run na Win11 wymaga PYTHONIOENCODING=utf-8)
  - [x] Każda z 4 komend ma `--help` z docstring
  - [x] `terralens fetch` wypisuje "Not implemented yet"

### T1.3 — Config system (dataclass) ✓ DONE (2026-04-25)
- **Dependencies:** T1.2
- **Output:** `src/terralens/config.py` z `@dataclass Config`
- **Implementation:**
  ```python
  from dataclasses import dataclass, field
  from pathlib import Path

  @dataclass
  class Config:
      data_dir: Path = Path("data")
      cache_db: Path = Path("data/cache.db")
      tile_size: int = 512
      tile_overlap: int = 64
      vram_budget_mb: int = 2500
      cache_ttl_days: int = 30
      regions: list[str] = field(default_factory=lambda: ["amazonia", "dubai", "arctic"])
      # ... reszta zgodnie z briefem
  ```
- **DoD:**
  - [x] Config singleton dostępny w `terralens.config.get_config()`
  - [x] Wartości zgodne z PROJECT_BRIEF Hardware Execution Policy (tile_size=512, vram_budget_mb=2500, batch_size=1, FP16)

### T1.4 — SQLite cache schema + queries.py ✓ DONE (2026-04-25)
- **Dependencies:** T1.3
- **Output:** `src/terralens/db/queries.py` (bez ORM, czyste SQL)
- **Implementation:**
  1. Schema z kolumnami: `layer, date, z, x, y, filepath, status, expires_at, created_at`
  2. Funkcje: `init_db()`, `insert_tile()`, `get_tile_status()`, `is_expired()`, `cleanup_expired()`
  3. `--refresh` flag obsługiwany przez query `WHERE expires_at > NOW()`
- **DoD:**
  - [x] Test: insert + query + expiry check działa w `tests/test_db.py` — 7/7 passed
  - [ ] `terralens fetch --init-db` tworzy `data/cache.db` (obsługa w T2.1 przy budowie fetchera)

**🏁 Sprint 1 complete when:** T1.1–T1.4 all ✓. Commit: `feat(S1): CLI skeleton with config and SQLite cache`

**📝 MEMORY.md update:** Dopisz decyzję "Architektura: CLI skeleton używa Typer + dataclass config + SQLite bez ORM (zgodnie z briefem v3.2, sekcja Architektura danych)"

---

## 🛰️ SPRINT 2 — Data Fetchers

**Cel:** Działające pobieranie tile'ów z NASA GIBS (HLS RGB + MODIS NDVI) i SRTM DEM.

### T2.1 — GIBS WMTS client ✓ DONE (2026-04-25)
- **Dependencies:** S1 complete
- **Output:** `src/terralens/fetchers/gibs.py`
- **Implementation:**
  1. Funkcja `fetch_tile(layer, date, z, x, y)` → bytes/Path
  2. URL template z GIBS WMTS docs
  3. Rate limiting: `time.sleep(0.1)` między requestami
  4. Retry z exponential backoff (3 próby)
  5. Zapisuje do `data/tiles/{layer}/{date}/{z}/{x}/{y}.png`
  6. Aktualizuje SQLite po sukcesie
- **DoD:**
  - [x] fetch_tile(layer, date, z, x, y) → Path; zapisuje do data/tiles/{layer}/{date}/{z}/{x}/{y}.png
  - [x] Second call → cache hit (brak HTTP request) — test_fetch_tile_cache_hit_skips_http ✓
  - [x] Test z mock HTTP w tests/test_gibs.py — 9/9 passed

### T2.2 — Region bounding boxes + tile math ✓ DONE (2026-04-25)
- **Dependencies:** T2.1
- **Output:** `src/terralens/fetchers/regions.py`
- **Implementation:**
  1. Słownik 3 regionów z bbox (lat/lon):
     - Amazonia: [-70, -10, -50, 0]
     - Dubai: [54.5, 24.8, 55.5, 25.5]
     - Arctic: [-30, 78, 30, 82] (Svalbard region)
  2. Funkcja `bbox_to_tiles(bbox, zoom)` → list[(z,x,y)]
  3. Używa `pyproj` lub prostej Web Mercator matematyki
- **DoD:**
  - [x] region_tiles(region, zoom) → list[(z,x,y)]; podłączone do CLI fetch
  - [x] Test: bbox_to_tiles dla Dubai @ z=8 zwraca < 20 tile'ów — 7/7 passed

### T2.3 — Batch fetch z progress bar (Rich) ✓ DONE (2026-04-25)
- **Dependencies:** T2.2
- **Output:** Rozbudowana komenda `terralens fetch`
- **Implementation:**
  1. CLI args: `--region`, `--start-date`, `--end-date`, `--layer`, `--frequency` (monthly)
  2. Generator dat (rok po roku, miesiąc po miesiącu)
  3. Rich Progress z ETA i % complete
  4. Logging do `data/logs/fetch_<timestamp>.log`
- **DoD:**
  - [x] terralens fetch --region X --start-date Y --end-date Z --layer L działa (Rich Progress + ETA)
  - [x] Progress bar: SpinnerColumn + BarColumn + MofNCompleteColumn + TimeRemainingColumn
  - [x] Ctrl+C → SIGINT handler ustawia _INTERRUPTED flag; pętla kończy się czysto (cache.db bezpieczny)

### T2.4 — SRTM DEM fetcher ✓ DONE (2026-04-25)
- **Dependencies:** T2.2, T0.5 (credentials z `.env`)
- **Output:** `src/terralens/fetchers/srtm.py`
- **Implementation:**
  1. Czyta credentials z `.env` (`NASA_EARTHDATA_USER`, `NASA_EARTHDATA_PASS`) przez `python-dotenv`
  2. Pobiera tile'y DEM dla każdego z 3 regionów (one-time, cachowane)
  3. Używa biblioteki `elevation` lub bezpośrednio SRTM30 GeoTIFFs z LP DAAC
  4. Retry z backoff przy 429 (dynamic rate limiting Earthdata)
  5. Zapisuje GeoTIFF do `data/dem/{region}.tif`
- **DoD:**
  - [x] fetch_dem(region) → list[Path]; pliki .hgt.zip w data/dem/{region}/
  - [x] Test: błędne credentials → PermissionError z czytelnym komunikatem — ✓
  - [x] Retry przy 429 z Retry-After header — test_fetch_dem_retries_on_429 ✓
  - [x] tests/test_srtm.py — 7/7 passed

**🏁 Sprint 2 complete when:** T2.1–T2.4 all ✓. Commit: `feat(S2): NASA data fetchers for tiles and DEM`

**📝 MEMORY.md:** "Rozwiązane problemy: SRTM fetching z Earthdata — rate limiting dynamiczne (20-60 req/min), retry z backoff przy 429."

---

## 🤖 SPRINT 3 — AI Upscaling (Satlas ESRGAN)

**Cel:** Upscale 4x tile'ów satelitarnych, stabilny VRAM.

### T3.1 — Satlas ESRGAN wrapper z singleton loading ✓ DONE (2026-04-26)
- **Dependencies:** S2 complete + T0.1 PASS
- **Output:** `src/terralens/engines/satlas_esrgan.py`
- **Implementation:**
  1. Klasa `SatlasESRGAN` z metodami `load()`, `unload()`, `upscale(tile)`
  2. Singleton pattern — model ładowany lazy przy pierwszym `upscale()`
  3. FP16, `.cuda()`, `torch.inference_mode()`
  4. Model weights cache w `data/models/satlas_esrgan_x4.pt`
- **Uwaga arch:** Satlas SwinB FPN zwraca feature mapę w pełnej rozdzielczości wejścia (1/1 scale, nie 1/4). Dekoder SR używa 2× PixelShuffle(2) = 4× całkowite SR.
- **DoD:**
  - [x] `upscale(tile_256x256)` zwraca `tile_1024x1024` — 6/6 integration tests PASS
  - [x] `torch.cuda.memory_allocated()` stabilny po 10 iteracjach (< 50MB delta) — PASS
  - [x] `.unload()` zwalnia VRAM do < 200MB — PASS

### T3.2 — @vram_safe decorator + dynamic tile sizing ✓ DONE (2026-04-26)
- **Dependencies:** T3.1
- **Output:** `src/terralens/models/vram_safe.py`
- **Implementation:**
  ```python
  def vram_safe(func):
      def wrapper(*args, **kwargs):
          import torch, gc
          torch.cuda.empty_cache()
          gc.collect()
          free, total = torch.cuda.mem_get_info()
          if free < 500 * 1024**2:  # <500MB free
              raise RuntimeError(f"Insufficient VRAM: {free/1e6:.0f}MB")
          result = func(*args, **kwargs)
          torch.cuda.synchronize()
          return result
      return wrapper
  ```
  Dodatkowo: `adaptive_tile_size()` → zwraca 512 lub 256 na podstawie wolnego VRAM
- **DoD:**
  - [x] Test: wymuszenie OOM przez duży batch → RuntimeError z czytelnym komunikatem — 11/11 PASS
  - [x] Adaptive tile sizing działa (test z mock mem_get_info) — PASS

### T3.3 — Tiled processing z overlap blending ✓ DONE (2026-04-26)
- **Dependencies:** T3.1, T3.2
- **Output:** `src/terralens/processors/tiled.py`
- **Implementation:**
  1. Funkcja `process_tiled(image, model, tile_size=512, overlap=64)`
  2. Iteracja przez grid tile'ów z 64px overlap
  3. Po upscale: blending overlap przez cosine window (alpha mask)
  4. `empty_cache() + gc.collect()` co 2 tile'y (z briefu)
  5. Rich progress bar
  - **Uwaga arch:** cosine window wymaga przesunięcia +0.5 (midpoint) — bez tego edge piksele dostają weight=0 i output jest zerowy. Z przesunięciem normalizacja jest zawsze stabilna.
- **DoD:**
  - [x] Test brak szwów: wariancja outputu przy stałym modelu < 1.0 — PASS
  - [x] VRAM cleanup co 2 tile'y — 16/16 testów PASS
  - [ ] `terralens process --region amazonia --date 2023-06-01 --upscale` działa end-to-end (wymaga S4+)

**🏁 Sprint 3 complete when:** T3.1–T3.3 all ✓. Commit: `feat(S3): Satlas ESRGAN pipeline with VRAM management`

**📝 MEMORY.md:** "Rozwiązane problemy: VRAM fragmentation na RTX 3050 — rozwiązanie `torch.cuda.empty_cache() + gc.collect()` co 2 tile'y zamiast per-tile (PoC wykazał X MB savings)"

---

## 🔍 SPRINT 4 — Change Detection Pipeline

**Cel:** SSIM z cloud masking + histogram matching + CVA w LAB.

### T4.1 — Cloud masking z QA band
- **Dependencies:** S3 complete
- **Output:** `src/terralens/processors/cloud_mask.py`
- **Implementation:**
  1. Dla MODIS NDVI: layer QA band z GIBS
  2. Funkcja `apply_cloud_mask(image, qa_band, threshold=0.2)` → NaN gdzie chmury
  3. Jeśli >50% obrazu zamaskowane → flaga "insufficient data"
- **DoD:**
  - [ ] Test na tile'u z chmurami → mask działa (visual check)
  - [ ] Edge case: 100% chmur → raise warning, skip SSIM

### T4.2 — Histogram matching
- **Dependencies:** T4.1
- **Output:** `src/terralens/processors/histogram_match.py`
- **Implementation:**
  1. `from skimage.exposure import match_histograms`
  2. Funkcja `match_to_reference(target, reference, mask=None)` — uwzględnia NaN z cloud mask
  3. Test: dwa obrazy z innych pór roku → po match struktury zgodne
- **DoD:**
  - [ ] Różnica w średniej jasności po match < 5%
  - [ ] NaN pixels preserved (nie wypełnia ich)

### T4.3 — SSIM z preprocessingiem
- **Dependencies:** T4.1, T4.2
- **Output:** `src/terralens/processors/ssim.py`
- **Implementation:**
  Pipeline z briefu:
  ```
  1. cloud_mask(target) + cloud_mask(reference)
  2. match_histograms(target, reference)
  3. gaussian_blur(sigma=1.5) na obu
  4. ssim(target_smoothed, reference_smoothed, full=True)
  5. Zwróć SSIM map jako heatmapę (niskie SSIM = zmiana)
  ```
- **DoD:**
  - [ ] Test: dwa identyczne obrazy → SSIM heatmap = 1.0 everywhere
  - [ ] Test: obraz z deforestacją → heatmap pokazuje zmiany w właściwych miejscach
  - [ ] Eksport heatmapy do kolorowego PNG (`viridis` colormap)

### T4.4 — NDVI diff dla MODIS
- **Dependencies:** T4.1
- **Output:** `src/terralens/processors/ndvi.py`
- **Implementation:**
  1. MODIS NDVI z GIBS to już gotowy produkt (range 0-255, skala 0-1)
  2. Funkcja `ndvi_diff(ndvi_before, ndvi_after)` → diff map + statystyki
  3. Statystyki: % pixels z NDVI decrease > 0.2 (deforestation threshold)
- **DoD:**
  - [ ] Test na Amazonia 2015 vs 2023 → diff pokazuje deforestation patches
  - [ ] Statystyki zapisywane do `data/processed/{region}/changes.json`

### T4.5 — Change Vector Analysis w LAB
- **Dependencies:** T4.1, T4.2
- **Output:** `src/terralens/processors/cva.py`
- **Implementation:**
  1. Konwersja RGB → LAB (`skimage.color.rgb2lab`)
  2. Euclidean distance w LAB między target/reference
  3. Thresholding + color coding
  4. Statystyki per region (% urban, % water, % vegetation estimate)
- **DoD:**
  - [ ] Test: CVA wykrywa zmiany które SSIM pomija (np. zmiana koloru bez struktury)
  - [ ] Statystyki spójne z NDVI diff (sanity check)

**🏁 Sprint 4 complete when:** T4.1–T4.5 all ✓. Commit: `feat(S4): change detection pipeline (SSIM + NDVI + CVA)`

**📝 MEMORY.md:** "Architektura: Change detection to 3 niezależne metryki (SSIM/NDVI/CVA), nie jeden 'best'. Każda wykrywa inny typ zmiany. Decyzja z PROJECT_BRIEF v3.0."

---

## 📦 SPRINT 5 — Export do PMTiles

**Cel:** Konsolidacja processed tile'ów do wersjonowanych PMTiles dla frontendu.

### T5.1 — tiles_to_pmtiles konwerter
- **Dependencies:** S4 complete
- **Output:** `src/terralens/export/pmtiles.py`
- **Implementation:**
  1. Użyj `pmtiles` Python lib (nie tippecanoe — vector only)
  2. Funkcja `build_pmtiles(tile_dir, output_path, metadata)` — raster tiles w WebP
  3. Metadata: bounds, min/max zoom, tile size, creation date, source layer
  4. WebP compression z quality=85 (balans size/quality)
- **DoD:**
  - [ ] `terralens export --region amazonia` generuje `data/export/amazonia_v{timestamp}.pmtiles`
  - [ ] Plik < 500MB dla Amazonia (3 regiony × 10 lat)
  - [ ] Otwieranie PMTiles w pmtiles CLI: `pmtiles show data/export/amazonia_*.pmtiles` pokazuje poprawne bounds

### T5.2 — Manifest JSON z wersjonowaniem
- **Dependencies:** T5.1
- **Output:** `src/terralens/export/manifest.py` + `data/export/manifest.json`
- **Implementation:**
  1. Struktura manifest:
     ```json
     {
       "version": "1.0",
       "generated": "2026-04-20T12:00:00Z",
       "regions": {
         "amazonia": {
           "latest": "amazonia_v20260420_120000.pmtiles",
           "timeline": [...],
           "changes": {...},
           "tour": {...}
         }
       }
     }
     ```
  2. Timeline: lista dat z cloud cover % (z cache.db)
  3. Changes: summary SSIM/NDVI/CVA per date
  4. Tour: camera path dla Guided Tour (z briefu)
- **DoD:**
  - [ ] Manifest walidowany JSON schemą
  - [ ] Stare wersje PMTiles zachowane (nie usuwane)
  - [ ] `terralens export --region amazonia` re-run → nowy timestamp, nowe latest

### T5.3 — Deploy do Cloudflare R2
- **Dependencies:** T5.2, T0.5 (credentials R2 z `.env`)
- **Output:** `src/terralens/cli/deploy.py`
- **Implementation:**
  1. Czyta credentials z `.env` (`R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ENDPOINT`, `R2_BUCKET`) przez `python-dotenv`
  2. CLI: `terralens deploy --region amazonia` uploaduje:
     - `{region}_v{timestamp}.pmtiles`
     - `manifest.json` (z updated `latest` pointer)
     - `{region}/timeline.json`, `changes.json`, `tour.json`
     - DEM texture (raz)
  3. Użyj `boto3` (S3-compatible API R2)
  4. Progress bar dla uploadu (Rich)
  5. Dry-run flag: `--dry-run` listuje co by się wrzuciło bez faktycznego uploadu
- **DoD:**
  - [ ] Upload `amazonia.pmtiles` działa
  - [ ] HTTP Range Request na URL R2 zwraca partial content (test curl)
  - [ ] Manifest dostępny jako static JSON pod `$R2_PUBLIC_URL/manifest.json`
  - [ ] `--dry-run` pokazuje plan bez uploadu

**🏁 Sprint 5 complete when:** T5.1–T5.3 all ✓. Commit: `feat(S5): PMTiles export pipeline with R2 deploy`

**🎉 BACKEND MVP COMPLETE** — pełny pipeline `fetch → process → export → deploy` działa end-to-end dla 1 regionu.

---

## 🌐 SPRINT 6 — Frontend PoC (DECISION GATE)

**Cel:** Udowodnić że wybrany silnik 3D obsługuje wymagania MVP. Decyzja R3F vs Deck.gl.

### T6.1 — Frontend scaffold
- **Dependencies:** S5 complete
- **Output:** `frontend/` z Vite + React + TypeScript + Tailwind + shadcn/ui
- **Implementation:**
  1. `npm create vite@latest frontend -- --template react-ts`
  2. Tailwind setup + shadcn/ui init
  3. ESLint + Prettier + pre-commit dla frontend
  4. Placeholder: pusty App.tsx z "TerraLens"
- **DoD:**
  - [ ] `npm run dev` → localhost:5173 pokazuje tytuł
  - [ ] `npm run build` bez błędów
  - [ ] ESLint pass

### T6.2 — PoC Deck.gl GlobeView (2 dni)
- **Dependencies:** T6.1
- **Output:** `frontend/src/poc/DeckGlobePoC.tsx`
- **Implementation:**
  1. Install: `@deck.gl/core @deck.gl/react @deck.gl/layers @deck.gl/geo-layers`
  2. GlobeView z TileLayer (HLS RGB z R2)
  3. Cinematic camera tour używając `FlyToInterpolator`:
     - Start: view planetarne
     - Fly to Amazonia (easing)
     - Fly to Dubai
  4. Test: DEM na globe (TerrainLayer lub custom)
  5. Mobile test (Chrome DevTools device emulation)
- **DoD (Deck.gl ocena):**
  - [ ] Globe obracany myszką, smooth
  - [ ] FlyToInterpolator daje lot po łuku (test wizualny)
  - [ ] DEM renderuje się bez szwów
  - [ ] FPS na desktop > 30
  - [ ] Mobile renderuje się (minimal FPS OK)
  - [ ] Subjective cinematic quality score: __/10

### T6.3 — PoC R3F (jeśli Deck.gl < 85%)
- **Dependencies:** T6.2 (tylko jeśli Deck.gl score < 8.5/10)
- **Output:** `frontend/src/poc/R3FGlobePoC.tsx`
- **Implementation:**
  1. Install: `three @react-three/fiber @react-three/drei`
  2. Sphere z texture mapping HLS RGB
  3. Custom camera animation z TWEEN.js (krzywe Beziera)
  4. SRTM DEM jako displacement via custom shader
  5. Mobile test
- **DoD (R3F ocena):**
  - [ ] Globe z teksturą renderuje się
  - [ ] Animacja kamery płynniejsza niż Deck.gl (subiektywnie)
  - [ ] DEM displacement bez szwów
  - [ ] FPS porównywalne z Deck.gl
  - [ ] Subjective cinematic quality score: __/10

### T6.4 — DECYZJA: Wybór silnika 🔴 BLOKUJĄCY
- **Dependencies:** T6.2 (+ opcjonalnie T6.3)
- **Output:** Decision record w `docs/ADR-001-frontend-engine.md`
- **Implementation:**
  Porównaj scores z T6.2 i T6.3. Kryteria:
  - Cinematic quality (30%)
  - Performance (30%)
  - Bundle size (15%)
  - Ease of Explore Mode Faza 2 (15%)
  - Maintenance burden (10%)

  Napisz ADR (Architecture Decision Record) z:
  - Kontekst
  - Porównanie
  - Decyzja
  - Konsekwencje (co trzeba zmienić w briefie jeśli wybór != plan)
- **DoD:**
  - [ ] ADR-001 commitowalny
  - [ ] MEMORY.md updated: "Architektura: Frontend engine = [wybór] (ADR-001)"
  - [ ] Drugi PoC usunięty z kodu (tylko wybrany zostaje)

**🏁 Sprint 6 complete when:** T6.1–T6.4 all ✓. Commit: `feat(S6): frontend scaffold + engine decision ([wybór])`

---

## 🎨 SPRINT 7 — Frontend Build

**Cel:** Pełny globe UI z timeline, heatmap layer, stats panel.

### T7.1 — Globe component (wybrany silnik)
- **Dependencies:** S6 decision
- **Output:** `frontend/src/components/Globe.tsx`
- **Implementation:**
  1. Fetch manifest.json z R2 na mount
  2. Render globe z texture layer (HLS RGB)
  3. DEM displacement
  4. Region markers (3 hardcoded)
- **DoD:**
  - [ ] Globe pokazuje Ziemię z real textures
  - [ ] Kliknięcie markera → callback z nazwą regionu

### T7.2 — Timeline slider z cross-fade
- **Dependencies:** T7.1
- **Output:** `frontend/src/components/Timeline.tsx`
- **Implementation:**
  1. Slider (shadcn/ui) z datami z manifest.timeline
  2. Opacity blend między current i next texture
  3. Hook `useTimelineTexture(region, date)` — ładowanie leniwe
  4. Preload current ± 1 klatka (z briefu)
- **DoD:**
  - [ ] Przeciąganie slider → smooth texture transition
  - [ ] Mobile touch działa
  - [ ] Brak flashów white/black podczas zmiany

### T7.3 — Heatmap layer (SSIM/NDVI)
- **Dependencies:** T7.2
- **Output:** `frontend/src/components/HeatmapLayer.tsx`
- **Implementation:**
  1. Overlay z PMTiles layer (change heatmaps)
  2. Opacity control (0-100%)
  3. Toggle SSIM vs NDVI vs CVA
- **DoD:**
  - [ ] Heatmap wyświetla się nad texture
  - [ ] Przełączanie metryk działa

### T7.4 — Stats panel (shadcn/ui Card)
- **Dependencies:** T7.3
- **Output:** `frontend/src/components/StatsPanel.tsx`
- **Implementation:**
  1. Card z shadcn/ui
  2. Duży numeric highlight ("-34% zieleni")
  3. Sekundarne stats (% urban, % water z CVA)
  4. Slide-in animation (framer-motion lub CSS transforms)
- **DoD:**
  - [ ] Panel responsive (mobile: bottom sheet, desktop: side panel)
  - [ ] Numery updates gdy user zmienia date/region

### T7.5 — Guided Tour — podstawowa wersja
- **Dependencies:** T7.1, T7.2, T7.4
- **Output:** `frontend/src/components/GuidedTour.tsx` + `useTour.ts`
- **Implementation:**
  1. Manifest.tour.json definiuje camera paths per region
  2. Sekwencja: view → Amazonia → Dubai → Arctic
  3. Przerwanie klikiem/ESC
  4. Replay button
- **DoD:**
  - [ ] Tour startuje automatycznie po załadowaniu
  - [ ] Kliknięcie przerywa smooth (nie jump-cut)
  - [ ] Replay action działa

**🏁 Sprint 7 complete when:** T7.1–T7.5 all ✓. Commit: `feat(S7): full frontend UI with timeline, heatmap, stats, guided tour`

---

## ✨ SPRINT 8 — 10-Second Hook Polish

**Cel:** Dopracowanie pierwszych 10 sekund zgodnie z sekcją `🎬 10-Second Hook` w briefie.

### T8.1 — Preloader z progress bar
- **Dependencies:** S7 complete
- **Output:** `frontend/src/components/Preloader.tsx` + `usePreload.ts`
- **Implementation:**
  1. Progress bar z miniaturą Amazonii
  2. `Promise.all(textures + dem + manifest)`
  3. Fallback: static preview PNG (amazonia_preview.jpg) podczas load
  4. Estetyczny design (Tailwind)
- **DoD:**
  - [ ] Loader pokazuje % complete
  - [ ] Tour startuje dopiero po 100% preload
  - [ ] Fallback PNG pojawia się przy slow network (test z throttling)

### T8.2 — Cinematic camera path (krzywe Beziera)
- **Dependencies:** T8.1, T7.5
- **Output:** Rozbudowany `useTour.ts`
- **Implementation:**
  1. Camera path nie linia prosta — Bezier z 2 control points
  2. Easing: `easeInOutCubic` na timeline
  3. Globe rotacja synchronizowana (region w centrum przy arrival)
  4. Subtle motion blur podczas lotu (opcjonalnie, jeśli FPS pozwala)
- **DoD:**
  - [ ] Lot Amazonia → Dubai wygląda cinematic (subjective)
  - [ ] Brak jitter na mobile

### T8.3 — Heatmap reveal z gradient opacity
- **Dependencies:** T8.2
- **Output:** Update `HeatmapLayer.tsx`
- **Implementation:**
  Po arrival nad regionem:
  1. Texture timelapse start (auto-play 2015→2024 w 3 sek)
  2. Heatmap fade-in z opacity 0 → 0.7 (animation)
  3. Stats panel slide-in z delay 1s
- **DoD:**
  - [ ] Sekwencja 10s dokładnie jak w briefie (sekunda po sekundzie)
  - [ ] Skip-safe (klik w dowolnym momencie = stop animation)

### T8.4 — Mobile optimization
- **Dependencies:** T8.3
- **Output:** Responsive rules + fallback logic
- **Implementation:**
  1. Detekcja mobile (useMediaQuery)
  2. Reduced texture resolution dla mobile (2K zamiast 4K)
  3. Fallback: jeśli FPS < 15 przez 3 sek → skip tour do static view
  4. Touch gestures dla globe rotation
- **DoD:**
  - [ ] Test na real device (Android mid-range)
  - [ ] Tour startuje lub graceful fallback
  - [ ] Globe interakcja smooth

**🏁 Sprint 8 complete when:** T8.1–T8.4 all ✓. Commit: `feat(S8): polished 10-second hook with cinematic preloader`

---

## 🚀 SPRINT 9 — Deploy Production

**Cel:** 3 regiony online, publiczny link do portfolio.

### T9.1 — Pełny pipeline dla 3 regionów
- **Dependencies:** S8 complete
- **Output:** PMTiles dla Amazonia, Dubai, Arctic w R2
- **Implementation:**
  ```bash
  for region in amazonia dubai arctic; do
    terralens fetch --region $region --start-date 2015-01-01 --end-date 2024-12-31 --layer HLS_RGB --frequency monthly
    terralens fetch --region $region --start-date 2015-01-01 --end-date 2024-12-31 --layer MODIS_NDVI --frequency monthly
    terralens fetch --region $region --dem
    terralens process --region $region
    terralens export --region $region
    terralens deploy --region $region
  done
  ```
  UWAGA: Pipeline dla 3 regionów × 10 lat × miesięczne może trwać 8-24h na twoim sprzęcie. Planuj overnight runs.
- **DoD:**
  - [ ] Każdy region ma PMTiles + manifest na R2
  - [ ] Total storage < 10GB (free tier R2)

### T9.2 — Frontend deploy na Vercel
- **Dependencies:** T9.1
- **Output:** Public URL z działającym TerraLens
- **Implementation:**
  1. `vercel.json` z custom headers (CORS dla R2)
  2. Env var `VITE_R2_BASE_URL` pointing to R2 bucket
  3. Preview deploys per PR, production na main
  4. Custom domain (opcjonalne)
- **DoD:**
  - [ ] Vercel URL pokazuje globe
  - [ ] 10-second hook działa na cold load
  - [ ] Mobile responsive

### T9.3 — README + portfolio polish
- **Dependencies:** T9.2
- **Output:** `README.md` + `docs/` z GIFami
- **Implementation:**
  1. README z:
     - Screenshot globe (1 kluczowy)
     - GIF 10-second hook (8-10 sek loop)
     - Architecture diagram (mermaid)
     - Tech stack badges
     - Live demo link
     - Quick start (dla devs)
     - License (MIT)
  2. Nagraj screencast GIF: `scripts/record_demo.md` jak to zrobić
  3. Dodaj link do NeuroMosaic w README (cross-link projektów portfolio)
- **DoD:**
  - [ ] README wygląda profesjonalnie
  - [ ] GIF < 5MB, autoplay w GitHub markdown
  - [ ] Repo publiczne na GitHubie: `github.com/Piotr1686/terralens`

**🏁 Sprint 9 complete when:** T9.1–T9.3 all ✓. Commit: `release: TerraLens v0.1.0 MVP`

Tag: `git tag v0.1.0 && git push --tags`

**🎉 MVP COMPLETE — Portfolio ready!**

---

## ⚠️ Risk Mitigation & Fallbacks

### Scenariusze awaryjne i reakcje

| Scenariusz | Trigger | Fallback |
|-----------|---------|----------|
| **PoC Satlas FAIL** | T0.1 OOM lub crash | Wróć do briefu, zmień model: Satlas → DSen2 → ESRGAN → ONNX INT8. Aktualizuj brief i MEMORY.md. |
| **GIBS API down lub rate-limited** | Timeouts, 429 errors | 1) Zwiększ `time.sleep` do 0.5s. 2) Użyj NASA Earthdata jako fallback source. 3) Plan deploy na noc (mniej ruchu). |
| **VRAM rośnie mimo empty_cache** | T3.3 — widoczny wzrost VRAM w logach | Implementuj multiprocessing (sprint 3.5): osobny proces per model. Aktualizuj MEMORY.md. |
| **R2 free tier exceeded (10GB)** | Deploy fails with quota error | 1) Kompresja WebP quality → 75. 2) Reduce zoom levels (z=6 zamiast z=8). 3) Fallback: Cloudflare Pages (100MB limit per file, ale unlimited requests). |
| **Frontend FPS < 15 na mobile** | T8.4 fails na real device | Reduce texture resolution do 1K dla mobile. Skip guided tour, auto → static view z CTA "Explore regions". |
| **PMTiles CORS issue** | T9.2 — przeglądarka blokuje Range Requests | 1) Sprawdź R2 CORS config. 2) Worker proxy na Cloudflare. 3) Eksport alternatywny: podziel na mniejsze PMTiles per region per rok. |

### Kiedy zatrzymać się i zapytać Piotra
- Każda decyzja wymagająca zmiany w briefie (np. model swap)
- Każdy sprint > 200% szacowanego czasu
- Każde ryzyko usunięcia funkcjonalności z MVP
- Każde "nie wiem jak to zrobić" po 3 próbach

---

## 📊 Progress Tracking

**Aktualny status:** (update po każdym sprincie)

```
S0  Pre-flight           [x] ✓ DONE 2026-04-25
S1  CLI Skeleton          [x] ✓ DONE 2026-04-25
S2  Data Fetchers         [x] ✓ DONE 2026-04-25
S3  AI Upscaling          [ ] ⧗
S4  Change Detection      [ ] ⧗
S5  Export PMTiles        [ ] ⧗
S6  Frontend PoC + Decision [ ] ⧗
S7  Frontend Build        [ ] ⧗
S8  10-Second Hook Polish [ ] ⧗
S9  Deploy Production     [ ] ⧗
```

**Estymaty czasowe (solo dev, part-time):**
- S0: 1-2 dni (T0.5 Earthdata approval może dodać ~pół dnia czekania, ale równolegle z T0.1)
- S1: 2 dni
- S2: 3 dni
- S3: 3 dni
- S4: 4 dni
- S5: 2 dni
- S6: 3 dni (2 dni PoC + 1 dzień decision + polish)
- S7: 5 dni
- S8: 3 dni
- S9: 3 dni (z overnight data processing)

**Total estimate:** ~30 dni roboczych = ~5-6 tygodni part-time. Match z briefem (~5 tygodni MVP).

---

## 📚 Reference Links

- PROJECT_BRIEF.md (v3.2) — pełna specyfikacja, sekcje do cytowania przy każdym tasku
- CLAUDE.md — zasady pracy z Claude Code (session system)
- MEMORY.md — długoterminowa pamięć decyzji
- last_session.md — krótkoterminowy stan sesji

**Co sesja:** `/start` → przeczytaj ten plik → znajdź najnowszy ⟳ lub pierwszy ⧗ → działaj.
