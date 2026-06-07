---
description: Przełącz na HIGH (Opus 4.7) z uzasadnieniem wg MODEL_ROUTING.md
argument-hint: [opcjonalny powód]
model: claude-opus-4-8
---

# /opus — eskalacja na HIGH

Użytkownik jawnie prosi o przełączenie na model wysokiej klasy (`claude-opus-4-8`).

**Twój krok:**

1. Potwierdź przełączenie jedną linią w formacie:
   `🔁 ROUTING: → HIGH (Opus 4.7) — <powód podany przez użytkownika lub wywnioskowany z kontekstu>`

2. Jeśli użytkownik podał argument `$ARGUMENTS` — użyj go jako uzasadnienia.
   Jeśli nie — wywnioskuj powód z ostatnich 3 wiadomości w sesji
   (np. „druga dopytka o ten sam problem", „zmiana dotyka architectural law").

3. Jeśli nie widzisz realnego powodu eskalacji zgodnego z `MODEL_ROUTING.md`,
   **zapytaj** użytkownika: "Na ten moment zadanie wydaje się mieścić w LOW
   (jeden plik, < 50 LOC). Czy jest powód, którego nie widzę?"
   Nie wykonuj eskalacji w milczeniu, jeśli jest nieuzasadniona.

4. Po potwierdzeniu — od następnej tury pracuj na HIGH zgodnie z pełną macierzą
   decyzyjną w `MODEL_ROUTING.md`.
