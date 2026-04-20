# T0.2 — Conda environment setup (Anaconda Prompt)

Instrukcja dla **Anaconda Prompt** na Windows. Wklejaj sekcję po sekcji, nie wszystko naraz — chcesz widzieć output każdego kroku. Jeśli któryś krok padnie, zatrzymaj się i zgłoś output do Claude'a.

**Prerequisites:**
- Miniconda / Anaconda zainstalowana
- Terminal: **Anaconda Prompt** (NIE PowerShell, NIE Git Bash — conda wymaga swojego inita)
- Driver NVIDIA ≥ 525 (u Ciebie: 566.36 ✓, CUDA runtime 12.7)

---

## 1. Utwórz i aktywuj env

```bash
conda create -n terralens python=3.10 -y
conda activate terralens
```

Po `conda activate` prompt powinien zacząć się od `(terralens)`.

## 2. cd do projektu

```bash
cd /d D:\Programming_Projects\TerraLens
```

## 3. PyTorch (wheele cu124)

Driver 566.36 → CUDA 12.7 runtime. Stable PyTorch wheele idą do `cu124` (cu128 tylko w nightly). `cu124` działa forward-compatible na CUDA 12.7.

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

~2.5 GB download (torch + cudnn + cublas). Cierpliwości.

## 4. Satlas (super-resolution, pinned 0.3.1)

Pakiet PyPI: `satlaspretrain-models` (hyphen), import jako `satlaspretrain_models` (underscore). Wersja 0.3.1 jest stabilna od maja 2024.

```bash
pip install satlaspretrain-models==0.3.1
```

**Fallback** jeśli pip install padnie (awaria PyPI / wycofanie pakietu):

```bash
# Nie uruchamiaj od razu — tylko gdy powyższe pip install zwróci błąd.
# git clone https://github.com/allenai/satlas.git scripts/_satlas_fallback
# pip install -e scripts/_satlas_fallback
```

## 5. Core libs (geo + CLI + export)

```bash
pip install rasterio numpy scikit-image requests tqdm rich typer python-dotenv pystac-client pmtiles boto3
```

## 6. Dev tools (test + lint + type check + pre-commit)

```bash
pip install pytest pytest-cov pytest-benchmark ruff mypy pre-commit
```

## 7. Export environment.yml

```bash
conda env export --no-builds > environment.yml
```

Utworzy `D:\Programming_Projects\TerraLens\environment.yml` — ten plik idzie do pierwszego commita.

## 8. Weryfikacja (jedna komenda)

```bash
python scripts/verify_t02.py
```

Oczekiwany output:

```
torch     : 2.x.x (CUDA runtime 12.4)
CUDA avail: True
GPU       : NVIDIA GeForce RTX 3050 Laptop GPU
satlas    : ok

[OK] T0.2 verification passed
```

Jeśli `[FAIL]` na którejkolwiek linii — **NIE kontynuuj do kroku 9**. Zgłoś do Claude'a dokładny output.

## 9. Pre-commit hooks (dokończenie T0.3)

```bash
pre-commit install
pre-commit run --all-files
```

- `pre-commit install` — instaluje hook `.git/hooks/pre-commit` (będzie się odpalać przy każdym `git commit`).
- `pre-commit run --all-files` — pierwszy raz pobiera binary'ki hooków (ruff, pre-commit-hooks). Pierwsze odpalenie: 1–2 min. Sprawdza wszystkie pliki (nie tylko staged).

Jeśli któryś hook pokaże `Failed` i _modifikuje_ pliki (np. `end-of-file-fixer` doda newline na końcu CLAUDE.md) — to jest OK, autofix zadziałał. Uruchom `pre-commit run --all-files` ponownie — powinno przejść `Passed` dla wszystkich hooków.

---

## DoD T0.2 + T0.3

- [ ] `conda env list` zawiera `terralens`
- [ ] `python scripts/verify_t02.py` → `[OK] T0.2 verification passed`
- [ ] `environment.yml` istnieje w repo root (sprawdzone: `dir environment.yml`)
- [ ] `pre-commit run --all-files` → wszystkie hooki `Passed`

## Po ukończeniu

Wróć do Claude'a z krótkim statusem: `"T0.2 + T0.3 done"` (lub output `[FAIL]` jeśli coś padło).

Pierwszy commit zrób **sam**, ręcznie — po Twojej stronie finalna kontrola co wchodzi do repo:

```bash
git add .
git status    # sanity check — NIE powinno być .env ani data/ na liście
git commit -m "chore(S0): pre-flight checks passed + credentials configured"
```

Jeśli pre-commit hook odpali się na commicie i coś poprawi — zrób `git add` + `git commit` ponownie z tym samym message.

Po commicie Claude wystartuje **T0.1 (PoC Satlas ESRGAN)** — blokujący task sprintu S0.
