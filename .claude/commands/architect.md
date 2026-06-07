---
description: Architektura, projektowanie modułów, refactor obejmujący wiele plików (HIGH).
argument-hint: <opis zadania architektonicznego>
model: claude-opus-4-8
---

# /architect — tryb architektoniczny (wymuszone HIGH)

Zadanie: `$ARGUMENTS`

**Tryb pracy:**

1. **Analizuj, zanim zaczniesz kodować.** Przeczytaj odpowiednie pliki projektu
   (zwykle: `config.py`, `engines/` lub `services/`, `processors/`, `models/`,
   `gui/` lub `api/` — zależnie od architektury). Jeśli czegoś nie jesteś pewny —
   zapytaj, nie zgaduj.

2. **Przedstaw ≥ 2 warianty** rozwiązania z trade-offami:
   - Wariant A: <nazwa> — plusy, minusy, koszt wdrożenia, ryzyko.
   - Wariant B: <nazwa> — plusy, minusy, koszt wdrożenia, ryzyko.
   - (Opcjonalnie) Wariant C.

3. **Wskaż rekomendację** z uzasadnieniem odwołującym się do:
   - architectural law tego projektu (Singleton, `@vram_safe`, Pydantic Settings,
     `asyncio.to_thread`, model path validation at load time),
   - ograniczeń sprzętowych (RTX 3050 4GB VRAM, Windows 11, Python 3.10),
   - konwencji projektu z `CLAUDE.md`.

4. **Poczekaj na decyzję użytkownika** przed implementacją.

5. Po akceptacji — zaproponuj **de-eskalację** (`/sonnet`) na etapie implementacji,
   jeśli sama implementacja jest już rutynowa (np. wygenerowanie boilerplate
   wg zaakceptowanej architektury).

**Anti-patterny:**
- ❌ Od razu skakać do kodu bez wariantów.
- ❌ Proponować rozwiązanie naruszające architectural law bez jawnego flagowania.
- ❌ Trzymać się HIGH przez całą sesję, jeśli po akceptacji architektury reszta to
   typowy templating.
