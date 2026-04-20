# CLAUDE.md — TerraLens

## Kontekst projektu
- Projekt: **TerraLens** — interaktywny 3D eksplorator zmian powierzchni Ziemi. Pipeline CLI pobiera dane NASA (GIBS HLS RGB, MODIS NDVI, SRTM DEM), przetwarza je (Satlas ESRGAN super-resolution, SSIM change detection z cloud masking + histogram matching) i eksportuje do PMTiles. Web dashboard (React 3D globe) serwuje pre-computed wyniki z cinematic 10-second hook (Amazonia → Dubai → Arktyka).
- Stack: **Python 3.10** (CLI pipeline, PyTorch FP16, GDAL, rasterio, scikit-image, Satlas ESRGAN) + **React + TypeScript + Tailwind + shadcn/ui** (frontend). Renderer 3D: React Three Fiber lub Deck.gl GlobeView (decyzja po PoC w tygodniu 3). Dane: Cloudflare R2 + PMTiles. Deploy frontu: Vercel / GitHub Pages.
- Środowisko: Windows 11, Miniconda (Python 3.10), VS Code
- Cel bieżący: **Sprint S0 — Pre-flight:** T0.1 PoC Satlas ESRGAN na RTX 3050 (blokujący) · T0.2 conda env `terralens` · T0.3 git init + pre-commit · T0.4 smoke test · T0.5 credentials (NASA Earthdata + Cloudflare R2). Kod projektu jeszcze nie napisany — faza planowania (PROJECT_BRIEF.md v3.2 + MASTER_PLAN.md). Wybór renderera 3D (R3F vs Deck.gl) to Sprint S6.

## Zasady pracy
- Zawsze sprawdzaj MEMORY.md przed podjęciem decyzji architektonicznej
- Nie duplikuj rozwiązań już opisanych w MEMORY.md
- Przy każdej nowej sesji: zacznij od /start
- Przy zakończeniu sesji: zawsze wywołaj /end
- W trakcie dłuższej pracy rób checkpointy przez /save
- Po każdym ukończonym tasku z MASTER_PLAN.md zaktualizuj jego status (✓ DONE / ⟳ IN PROGRESS / ✗ BLOCKED) i zrób /save
- Nie przeskakuj Dependencies w MASTER_PLAN.md — jeśli T2.3 wymaga T2.1, sprawdź najpierw

## Konwencje projektu
- Nazewnictwo plików: snake_case (Python), kebab-case (komponenty React)
- Język komentarzy w kodzie: polski
- Styl commitów: conventional commits z ID taska — `feat(T1.2): ...`, `fix(T2.3): ...`, `refactor(T4.1): ...`, `docs(S5): ...`, `test(T3.2): ...`
- Po ukończonym sprincie: git commit z `feat(S<n>): <sprint goal>` + aktualizacja MEMORY.md
- Przetwarzanie obrazów: tiled 512×512 z overlap 64px, FP16, batch-size-1

## Pliki stanu sesji
- MEMORY.md       — długoterminowa pamięć projektu (czytaj na /start)
- last_session.md — stan ostatniej sesji (czytaj na /start, pisz na /end)
- MASTER_PLAN.md  — mapa wykonawcza (sprinty S0–S9, taski z DoD); czytaj po /start przed nowym zadaniem
- PROJECT_BRIEF.md — wizja, stack, uzasadnienia decyzji AI/ML (referencja)

## Komendy dostępne w tym projekcie
- /start   — inicjalizacja sesji (czyta MEMORY.md + last_session.md)
- /save    — checkpoint w trakcie sesji (aktualizuje last_session.md)
- /end     — zamknięcie sesji (nadpisuje last_session.md, aktualizuje MEMORY.md)
- /status  — szybki podgląd aktualnego stanu (tylko odczyt)

## Sprzęt / Ograniczenia
- GPU: RTX 3050 Laptop 4GB VRAM — nie ładuj modeli >3.5GB w pełnym FP16
- CPU: i5-12500H
- RAM: 32GB DDR4
- Preferuj kwantyzację GGUF Q4_K_M dla modeli LLM
- Rozważ CPU offload dla warstw które nie mieszczą się w VRAM
- Peak VRAM pipeline: ~1.5GB (Satlas ESRGAN FP16 singleton, tiled 512×512). Stosuj `torch.cuda.empty_cache()` + `gc.collect()` co 2 tile'y, `@vram_safe` decorator.
