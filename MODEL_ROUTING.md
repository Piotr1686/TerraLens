# MODEL_ROUTING.md

> **Cel:** Oszczędność tokenów przez świadomy wybór modelu pod skalę zadania.
> Ten plik jest ładowany przez `CLAUDE.md` i obowiązuje w każdej sesji
> Claude Code w tym projekcie.

---

## Modele używane w tym projekcie

| Alias w tym dokumencie | Model ID                | Rola                                     |
|------------------------|-------------------------|------------------------------------------|
| **HIGH**               | `claude-opus-4-8`       | Adaptive thinking — trudne, kreatywne    |
| **LOW**                | `claude-sonnet-4-6`     | Rutyna, tłumaczenia, proste edycje       |

Domyślny model sesji: **LOW** (`claude-sonnet-4-6`).
Eskalacja do HIGH następuje tylko wtedy, gdy zadanie spełnia kryteria niżej.

---

## Reguła nadrzędna (dla Claude'a)

**Zanim zaczniesz wykonywać zadanie, wykonaj dwa kroki:**

1. **Klasyfikuj zadanie** według macierzy poniżej (sekcja "Macierz decyzyjna").
2. Jeśli aktualny model nie pasuje do klasyfikacji:
   - **Nie wykonuj zadania jeszcze.**
   - Wypisz jedną linię: `🔁 ROUTING: [LOW → HIGH | HIGH → LOW] — powód: <jedno zdanie>`
   - Zasugeruj użytkownikowi komendę: `/model opus` lub `/model sonnet`.
   - Poczekaj na potwierdzenie **lub** na wyraźne "jedź dalej bez zmiany".

Wyjątki od tej procedury:
- Jeśli zadanie zajmuje < 5 linii odpowiedzi → pomijasz routing, działasz na bieżącym modelu.
- Jeśli użytkownik wywołał komendę z jawnym modelem w frontmatter
  (np. `/architect`, `/quick`) → model jest już narzucony, routing pomijasz.
- Jeśli delegujesz zadanie do subagenta (`Task`) → wybierasz model dla subagenta
  według tej samej macierzy, **niezależnie** od modelu głównej sesji.

---

## Macierz decyzyjna

### 🟥 Eskaluj do HIGH (`claude-opus-4-8`)

Zadanie trafia na HIGH, jeśli spełnia **co najmniej jeden** z poniższych:

#### Złożoność kodu
- Refactor obejmujący **≥ 3 pliki** lub **≥ 150 LOC netto**.
- Zmiany w **architectural law** projektu. Poniższe to **przykłady dla projektów
  AI/Python z GPU**: `config.py` (Singleton, Pydantic Settings), `@vram_safe`
  decorator, `OOMStrategy`, ładowanie modeli, FastAPI `asyncio.to_thread()`.
  > W projekcie **nie-AI / CPU-only / innym stacku** (np. DriftScope: framework
  > naukowy CPU-only — brak `@vram_safe`/`OOMStrategy`) podstaw własne „prawa":
  > rdzeń metodologii, kontrakty determinizmu/seedów, schematy danych, publiczne
  > API. Zasada jest stała: dotknięcie rdzenia → HIGH.
- Projektowanie nowego silnika/modułu (nowy `engine_*.py`, nowy processor,
  nowy serwis).
- Algorytmy domenowe i ML: feature extraction, embedding/color matching
  w wysokich wymiarach, tilings geometryczne, graph search, kwantyzacja modeli,
  niestandardowe CUDA ops, custom loss / training loops.
- Regex/SQL, w którym jeden błąd zmienia semantykę nieodwracalnie.
- Operacje na **AST**, generowanie kodu, metaprogramming.

#### Debug i niezawodność
- Debug problemu, który **przeżył ≥ 2 próby** naprawy (na LOW lub wcześniejszego HIGH).
- Deadlock, race condition, memory leak, fragmentacja VRAM, non-deterministic fail.
- "Kod wygląda dobrze, ale nie działa" — klasyczny sygnał, że trzeba głębiej.
- Błąd, który pojawia się tylko w CI/produkcji, ale nie lokalnie.

#### Kreatywność i otwartość problemu
- Generowanie wariantów architektury (≥ 2 alternatywy z trade-offami).
- Projektowanie API lub kontraktu między modułami.
- Review architektoniczne, pre-publish audit, RFC.
- Zadania z luźnym opisem wymagające dopytania ("zrób coś z X, żeby było lepiej").

#### Kontekst i stawka
- Zużycie context window **> 60%** — na LOW jakość syntezy spada szybciej.
- Zadanie ma konsekwencje ireversible (migracja DB, edycja `.git`, publikacja na GitHub,
  zmiana `pyproject.toml` wersji).
- Fragment kodu będzie **publiczny** (GitHub, portfolio, dokumentacja).
- Eksportowany artefakt dla innych narzędzi/modeli (PROJECT_BRIEF, DECISION_PROMPT).

#### Sygnał eskalacji w rozmowie
- Użytkownik dopytuje **po raz drugi o to samo** (pierwsza odpowiedź LOW okazała się
  niewystarczająca). Regresja z odpowiedzi LOW → natychmiastowa eskalacja do HIGH.
  Pierwsza dopytka o **inny aspekt** tego samego tematu — pozostajemy na LOW,
  ale traktujemy to jako sygnał ostrzegawczy. Druga dopytka → HIGH.
- Użytkownik używa słów: "wciąż nie działa", "to nie to", "głębiej", "nie rozumiem
  dlaczego to ma sens", "spróbuj inaczej", "weź to poważniej".

---

### 🟩 Pozostań na LOW (`claude-sonnet-4-6`)

- Pojedyncza edycja w **jednym pliku**, zmiana **< 50 LOC**.
- Renaming, linting, formatowanie, dodanie docstring, type hints.
- Tłumaczenia prostych pojęć (EN ↔ PL), definicje, "co to jest X".
- Streszczenia logów, diff'ów, release notes.
- Pisanie testów jednostkowych dla już zaprojektowanych funkcji
  (ale **nie** projektowanie strategii testowej — to HIGH).
- Formatowanie CLAUDE.md, MEMORY.md, aktualizacja `last_session.md`.
- Generowanie boilerplate (CustomTkinter widgets layout, pytest fixtures,
  `argparse` skeleton).
- Odpowiedzi na pytania typu yes/no o stan systemu lub oczywiste fakty.
- Polecenia git rutynowe (`git status`, `git log`, analiza uncommitted).
- Regex i SQL o jednoznacznej specyfikacji, pod nadzorem testu.
- Odpalenie istniejącego skryptu PowerShell/bash i zreferowanie wyniku.
- Analiza pojedynczego traceback'a Pythonowego bez głębokiego kontekstu.

---

## Ciche eskalacje (bez pytania użytkownika)

W poniższych sytuacjach możesz **natychmiast** użyć HIGH bez proszenia o `/model opus`
(w raporcie końcowym wspomnij krótko `[routing: HIGH — powód]`):

1. **Tryb subagenta z `context: fork`** — w tamtym kontekście koszt jest izolowany,
   więc jeśli klasyfikacja zadania to HIGH, spawnujesz subagent na Opus.
2. **Pre-commit self-review** — po zakończeniu dużej edycji, ostatnie sprawdzenie
   spójności (≤ 30 sekund myślenia) zawsze na HIGH.
3. **Korekta po błędzie ujawnionym w ostatnich 3 turach** — jeśli sam siebie złapałeś
   na błędzie lub użytkownik wskazał pomyłkę, kolejna próba idzie na HIGH.

---

## Ciche de-eskalacje (bez pytania użytkownika)

Odwrotnie — jeśli siedzisz na HIGH, a zadanie w rzeczywistości jest banalne, nie marnuj
tokenów. Zasygnalizuj w jednej linii: `🔁 ROUTING: HIGH → LOW — <powód>`
i **poproś o potwierdzenie** `/model sonnet` przed kontynuacją.

Typowe sytuacje:
- Trudny blok został rozwiązany, teraz trzeba tylko przepisać komentarze/docstringi.
- Użytkownik przełączył temat na coś rutynowego ("a teraz dopisz mi test do tej funkcji").
- Sesja dochodzi do 80% context window, a pozostałe zadania są małe —
  LOW pozwoli domknąć sesję bez przekroczenia.

---

## Protokół komunikatu routingowego

Zawsze ten sam format, jedna linia, prefiks emoji dla szybkiego wychwycenia wzrokiem:

```
🔁 ROUTING: LOW → HIGH — zmiana dotyka @vram_safe i OOMStrategy (architectural law).
🔁 ROUTING: HIGH → LOW — pozostał tylko opis zmian w CHANGELOG.md.
🔁 ROUTING: pozostaję na LOW — zadanie mieści się w <50 LOC, jeden plik.
🔁 ROUTING: pozostaję na HIGH — druga dopytka użytkownika o ten sam problem.
```

Nigdy nie rozwlekaj. Nigdy nie używaj > 2 zdań. Ten komunikat to sygnał, nie esej.

---

## Kryteria rozstrzygające w razie wątpliwości

Jeśli po klasyfikacji nie jesteś pewien (3 kryteria LOW vs 1 HIGH, albo odwrotnie):

1. **Ireversibility bije taniość.** Jeśli zadanie zmienia coś, co trudno cofnąć
   (git history, migracja, zmiana kontraktu publicznego) → HIGH.
2. **Publiczność bije prywatność.** Kod/tekst, który zobaczą inni → HIGH.
3. **Niejawne założenia biją jawne.** Jeśli użytkownik nie doprecyzował wymagań,
   a Ty musisz "wyczuć intencję" — HIGH (bo LOW zgadnie gorzej).
4. **W pozostałych przypadkach — LOW.** Taniej i wystarczy.

---

## Jak używać tego pliku

**W CLAUDE.md** (root projektu) dodaj jedną linię odwołania:

```markdown
## Model routing
Zobacz [`MODEL_ROUTING.md`](./MODEL_ROUTING.md). Reguły obowiązują bezwyjątkowo.
```

**W sesji** masz do dyspozycji komendy slash (opisane w `.claude/commands/`):

- `/opus` — przełącz na HIGH z uzasadnieniem.
- `/sonnet` — przełącz na LOW z uzasadnieniem.
- `/route <opis zadania>` — analiza tekstowa bez wykonywania; rekomendacja modelu.
- `/architect` — komenda z wymuszonym HIGH (architektura/złożony refactor).
- `/quick` — komenda z wymuszonym LOW (edycja rutynowa).
- `/explain` — LOW; proste wyjaśnienie pojęcia.
- `/deep-debug` — HIGH; trudny debug wieloetapowy.
- `/code-audit` — HIGH; code review przed commitem/publikacją.

---

## Anti-patterny, których unikamy

- ❌ Eskalacja „na wszelki wypadek". Każde HIGH musi mieć konkretny powód z listy.
- ❌ Zostawanie na HIGH po wykonaniu trudnej części. Po zamknięciu problemu — /sonnet.
- ❌ Używanie HIGH do formatowania, przenoszenia plików, odpowiedzi yes/no.
- ❌ Wywoływanie `/route` na zadaniu, które już wiesz jak zaklasyfikować
  (marnowanie tokenów na meta-analizę).
- ❌ Ciche przełączanie HIGH → LOW bez komunikatu — użytkownik traci kontrolę.
