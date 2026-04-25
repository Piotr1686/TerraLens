---
description: Sklasyfikuj zadanie wg MODEL_ROUTING.md i zarekomenduj model (bez wykonywania).
argument-hint: <opis zadania>
model: claude-haiku-4-5-20251001
---

# /route — analiza zadania, rekomendacja modelu

Użytkownik chce zdecydować świadomie — **nie wykonuj zadania**, tylko je sklasyfikuj.
Używamy tu Haiku (najtańszy model), bo sama klasyfikacja jest trywialna —
dzięki temu `/route` kosztuje grosze i można go używać bez oporów.

**Opis zadania od użytkownika:** `$ARGUMENTS`

**Twój krok — w dokładnie takim formacie (krótko, bez lania wody):**

```
📋 KLASYFIKACJA

Zadanie: <1-zdaniowe streszczenie wejścia>

Kryteria trafione:
- [HIGH] <kryterium z MODEL_ROUTING.md> — <krótkie uzasadnienie dla tego zadania>
- [LOW]  <kryterium z MODEL_ROUTING.md> — <krótkie uzasadnienie>
(...jedno lub więcej, oznaczone etykietą HIGH albo LOW)

Bilans: <X> kryteriów HIGH vs <Y> kryteriów LOW.

Rekomendacja: **<HIGH | LOW>** (<claude-opus-4-7 | claude-sonnet-4-6>)
Komenda: `/<opus|sonnet>` lub `/<architect|quick|deep-debug|review|explain>`

Powód rozstrzygający (jeśli bilans był niejednoznaczny):
<który punkt z "Kryteria rozstrzygające" zadecydował — ireversibility,
publiczność, niejawne założenia, albo default LOW>

Szacunek kosztu:
- na HIGH: ~<przybliżony rząd wielkości — "kilka k tokenów" / "kilkanaście k" / "dużo">
- na LOW:  ~<j.w., o rząd mniej>
```

**Zasady:**
- Jeśli `$ARGUMENTS` jest puste → zapytaj: "Jakie zadanie oceniamy?" i zakończ.
- Nie wykonuj zadania, nawet jeśli wydaje się banalne.
- Nie sugeruj rozwiązania — tylko klasyfikacja i rekomendacja modelu.
- Maksymalnie 15 linii wyjścia. To jest narzędzie decyzyjne, nie rozprawka.
