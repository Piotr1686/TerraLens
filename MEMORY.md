# MEMORY.md — Długoterminowa pamięć projektu TerraLens

> Ten plik kumuluje wiedzę o projekcie. Nigdy nie usuwaj wpisów — tylko dopisuj.
> Każdy wpis oznaczaj datą w formacie [YYYY-MM-DD].

---

## Architektura

<!-- Claude dopisuje tutaj decyzje architektoniczne wraz z uzasadnieniem -->

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

### [⧗ TODO] Cloudflare R2 — bucket `terralens-data`

- Nie skonfigurowany (T0.5 cz.B). Wymagany dopiero przy T5.3 (deploy).
- Placeholdery w `.env`: `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ENDPOINT`, `R2_BUCKET=terralens-data`, `R2_PUBLIC_URL`.
- Plan: free tier (10GB storage, 10M Class A/B ops/mies). CORS policy dla Vercel domains.
