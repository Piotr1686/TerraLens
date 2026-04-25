# MEMORY.md — Długoterminowa pamięć projektu TerraLens

> Ten plik kumuluje wiedzę o projekcie. Nigdy nie usuwaj wpisów — tylko dopisuj.
> Każdy wpis oznaczaj datą w formacie [YYYY-MM-DD].

---

## Architektura

<!-- Claude dopisuje tutaj decyzje architektoniczne wraz z uzasadnieniem -->

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
