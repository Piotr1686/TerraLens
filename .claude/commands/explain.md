---
description: Proste wyjaśnienie pojęcia lub fragmentu kodu (LOW, Sonnet 4.6).
argument-hint: <co mam wyjaśnić>
model: claude-sonnet-4-6
---

# /explain — wyjaśnienie (LOW)

Temat: `$ARGUMENTS`

**Styl:**
- Zwięźle, konkretnie, bez lania wody.
- Jedno wyjaśnienie na poziomie „jak to działa", jedno na poziomie
  „dlaczego akurat tak" — jeśli oba są potrzebne.
- Analogia tylko jeśli ewidentnie pomaga. Bez wymuszonych metafor.
- Jeśli to fragment kodu — pokaż go raz, potem omawiaj.
- Max 150 słów, chyba że użytkownik sam poprosi o więcej.

**Eskalacja:**
- Jeśli tematu nie da się rzetelnie wyjaśnić w tej długości (np. „wytłumacz mi
  adaptive thinking w kontekście long-horizon tasks") → wypisz:

  ```
  🔁 ROUTING: LOW → HIGH — temat wymaga głębszego kontekstu niż mieści się w LOW.
  ```

- Jeśli użytkownik **po wyjaśnieniu** dopytuje o ten sam temat **drugi raz** —
  to sygnał z MODEL_ROUTING.md: eskalacja obowiązkowa, pytasz o `/model opus`.

**Cel:** proste rzeczy tłumaczyć prosto i tanio. Pułapką jest zadanie
przebrane za proste — wtedy w porę eskaluj.
