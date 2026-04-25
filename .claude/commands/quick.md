---
description: Szybka, rutynowa edycja w jednym pliku (LOW, Sonnet 4.6).
argument-hint: <krótki opis zmiany>
model: claude-sonnet-4-6
---

# /quick — tryb szybki (wymuszone LOW)

Zadanie: `$ARGUMENTS`

**Tryb pracy:**

1. Wykonaj zmianę **minimalnym kosztem**. Nie rozszerzaj zakresu.
   Nie proponuj „przy okazji" refactoringu sąsiednich fragmentów.

2. Oczekiwane cechy zadania (jeśli nie pasuje — zatrzymaj się i spytaj):
   - dotyczy **jednego pliku**,
   - zmiana **< 50 LOC**,
   - brak ingerencji w `config.py`, `@vram_safe`, `engines/`, ładowanie modeli,
   - test jednostkowy jest opcjonalny lub już istnieje.

3. Format odpowiedzi:
   - Pokaż **diff** lub zmienione fragmenty (nie cały plik, chyba że < 80 linii).
   - Jedna krótka linia co zrobione.
   - Brak meta-komentarza o alternatywach — nie jest tu potrzebny.

4. **Eskalacja wyjściowa:** jeśli w trakcie zauważysz, że zadanie nie mieści się
   w definicji quick (np. trzeba zmienić kontrakt funkcji, albo dotknąć
   architectural law), **przerwij** i wypisz:

   ```
   🔁 ROUTING: LOW → HIGH — <powód>
   Sugeruję `/model opus` lub `/architect`. Czekam na potwierdzenie.
   ```

**Cel:** większość rutynowych edycji w tym projekcie ma kosztować grosze.
