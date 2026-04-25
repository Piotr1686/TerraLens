---
description: Przełącz na LOW (Sonnet 4.6) z uzasadnieniem wg MODEL_ROUTING.md
argument-hint: [opcjonalny powód]
model: claude-sonnet-4-6
---

# /sonnet — de-eskalacja na LOW

Użytkownik prosi o przełączenie na model niskiego kosztu (`claude-sonnet-4-6`).
Celem jest oszczędność tokenów — zadanie nie wymaga adaptive thinking.

**Twój krok:**

1. Potwierdź jedną linią:
   `🔁 ROUTING: → LOW (Sonnet 4.6) — <powód>`

2. Jeśli podany `$ARGUMENTS` — użyj jako powodu. Jeśli nie — wywnioskuj
   (np. „zostały tylko docstringi i komentarze", „user przeszedł do rutynowego pytania",
   „kontekst przekracza 80%, domykamy sesję").

3. Jeśli w ciągu ostatnich 3 wiadomości widzisz sygnał eskalacji
   (np. user dwukrotnie wrócił do tego samego problemu) —
   **ostrzeż**: „Uwaga: ostatnia tura sugerowała eskalację do HIGH
   (second retry na [temat]). Na pewno de-eskalować?"
   Nie przełączaj po cichu.

4. Po potwierdzeniu — pracuj na LOW, stosując pełną macierz decyzyjną
   z `MODEL_ROUTING.md`. Jeśli kolejne zadanie w tej sesji spełni kryteria HIGH —
   sygnalizuj eskalację jak zwykle.
