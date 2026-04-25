---
description: Trudny debug, problem po co najmniej jednej nieudanej próbie naprawy (HIGH).
argument-hint: <opis błędu, traceback, co już próbowaliśmy>
model: claude-opus-4-7
---

# /deep-debug — trudny debug (HIGH)

Wejście: `$ARGUMENTS`

**Procedura:**

1. **Sformułuj hipotezy.** Min. 3. Dla każdej:
   - czego by dotyczyła,
   - jaki byłby jej prosty test (≤ 1 polecenie lub ≤ 10 linii sprawdzającego kodu),
   - co odróżniłoby ją od pozostałych.

2. **Uporządkuj hipotezy** od najtańszej do zweryfikowania → do najdroższej.

3. **Jeśli masz dostęp do plików projektu** — otwórz te, które są podejrzane,
   zanim cokolwiek napiszesz. Typowe sygnały w projektach Python+AI:
   - crashe na OOM / VRAM → `@vram_safe`, `OOMStrategy`, batch size,
     kolejność loadowania modeli, fragmentacja po powtórnych loadach
   - "kod wygląda dobrze, ale nie działa" → Singleton `config.py` / race w lazy init,
     ukryty stan globalny, cache Pydantic Settings
   - błąd tylko przy powtórnym uruchomieniu → stan globalny, cache, env vars
     zamrożone przez Pydantic Settings przy pierwszym load
   - niepowtarzalny wynik → nondeterminizm torch, brak ustalonego seed,
     albo float accumulation order
   - crash tylko w CI/produkcji, nie lokalnie → różnica Python/CUDA/biblioteki,
     ścieżki Windows vs Linux, brak walidacji ścieżek at load time

4. **Nie naprawiaj w ciemno.** Zanim zaproponujesz fix, wskaż, która hipoteza
   jest potwierdzona (lub że potrzebujesz outputu konkretnego testu).

5. **Raport końcowy:**
   - potwierdzona przyczyna (jedna),
   - zaproponowany fix (minimal diff),
   - ryzyko regresji (co jeszcze może zależeć od tej zmiany),
   - rekomendowany test zabezpieczający.

6. **Po zamknięciu:** zaproponuj `/sonnet` na kolejne kroki, jeśli reszta
   to już tylko pisanie testu lub aktualizacja changeloga.

**Anti-patterny:**
- ❌ „Spróbuj tak, może zadziała" bez wskazania hipotezy.
- ❌ Naprawa symptomu zamiast przyczyny.
- ❌ Pomijanie ryzyka regresji, zwłaszcza przy zmianach w `@vram_safe` i `engines/`.
