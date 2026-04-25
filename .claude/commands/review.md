---
description: Code review przed commitem lub publikacją na GitHub (HIGH).
argument-hint: [opcjonalnie: ścieżka do pliku lub @path]
model: claude-opus-4-7
---

# /review — code review (HIGH)

Zakres: `$ARGUMENTS` (jeśli puste — uncommitted changes; uruchom w myśli
odpowiednik `git diff HEAD` i zreferuj).

**Checklist (w tej kolejności):**

1. **Architectural law tego projektu.** Zweryfikuj:
   - `config.py` — thread-safe Singleton, Pydantic Settings jako jedyne źródło konfiguracji.
   - `@vram_safe` decorator + `OOMStrategy` — czy jest tam, gdzie powinien.
   - Ścieżki do modeli — walidacja at load time, nie later.
   - FastAPI inference (jeśli dotyczy) — `asyncio.to_thread()`, nie blokowanie event loop.
   - Brak Loguru (niekompatybilny z torch/transformers — standard tego projektu).
   - Brak Repository pattern (odrzucone jako over-engineering dla solo dev).

2. **Bezpieczeństwo i niezawodność.**
   - Sekrety w `.env`, nigdy w kodzie.
   - Walidacja inputu użytkownika w `gui/`.
   - Brak `print()` — logging przez konfigurację z `config.py`.
   - Testowalność: funkcje czyste, efekty uboczne izolowane.

3. **Styl i konwencje.**
   - `pathlib.Path` zamiast `os.path` na Windows 11.
   - Type hints pełne (signatures funkcji publicznych).
   - Docstringi na klasach i funkcjach publicznych.
   - Nazewnictwo zgodne z istniejącym wzorcem w module.

4. **Portfolio quality** (jeśli to kod pre-GitHub).
   - README wskazuje, jak odpalić krokami — działa świeżo po clone?
   - `requirements.txt` / `environment.yml` spójne z faktycznym importami.
   - Brak „dead code" — zakomentowanych TODO, nieużywanych importów.
   - LICENSE, `.gitignore`, struktura zgodna z konwencją `D:\Programming_Projects\`.

5. **Bilans i werdykt:**
   ```
   ✅ PASS — gotowe do commita.
   ⚠️  PASS WITH WARNINGS — commit OK, ale odnotuj te TODO: <...>.
   ❌ FAIL — nie commituj. Konieczne zmiany: <...>.
   ```

6. **Po review:**
   - Jeśli PASS / PASS WITH WARNINGS → zaproponuj `/sonnet` i komendę `git commit`.
   - Jeśli FAIL → pozostań na HIGH, zaproponuj plan naprawy (bez wykonywania go).

**Anti-patterny:**
- ❌ Lista 40 drobnych uwag stylistycznych bez bilansu. Review ma dać werdykt.
- ❌ Akceptacja kodu naruszającego architectural law „bo poza tym jest OK".
- ❌ Naprawianie od razu — to jest review, nie fix.
