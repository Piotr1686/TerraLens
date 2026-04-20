# Prompt dla Claude Code — instalacja Session State Management w projekcie TerraLens

> **Jak użyć:** Otwórz Claude Code w katalogu `D:\Programming_Projects\TerraLens`, wklej cały poniższy prompt (od `===` do `===`) i wyślij. Claude Code wykona wszystkie kroki automatycznie.

---

```
===================================================================
PROMPT START
===================================================================

Zaimplementuj w tym projekcie (TerraLens) system zarządzania stanem sesji Claude Code. System ma zapewnić ciągłość kontekstu między sesjami przez 4 pliki (CLAUDE.md, MEMORY.md, last_session.md) oraz 4 komendy slash (/start, /save, /end, /status).

WYKONAJ KROKI W TEJ KOLEJNOŚCI:

═══════════════════════════════════════════════════════════════════
KROK 1 — Analiza projektu
═══════════════════════════════════════════════════════════════════

Przeskanuj katalog projektu TerraLens i ustal:
- Jaki jest stack technologiczny (sprawdź package.json / pyproject.toml / requirements.txt)
- Jaka jest główna struktura katalogów
- Czy istnieje już jakiś CLAUDE.md lub dokumentacja
- Jeśli istnieje CLAUDE.md — utwórz backup jako CLAUDE.md.backup_before_session_system
- Jakie jest przeznaczenie projektu (sprawdź README jeśli istnieje)

Wyświetl mi krótkie podsumowanie tego co znalazłeś PRZED tworzeniem plików.

═══════════════════════════════════════════════════════════════════
KROK 2 — Struktura katalogów
═══════════════════════════════════════════════════════════════════

Utwórz katalog `.claude/commands/` w głównym katalogu projektu.

═══════════════════════════════════════════════════════════════════
KROK 3 — Plik CLAUDE.md
═══════════════════════════════════════════════════════════════════

Utwórz plik CLAUDE.md w głównym katalogu projektu. Wypełnij sekcje
"Kontekst projektu" i "Sprzęt" na podstawie tego co wiesz o TerraLens
z KROKU 1 oraz z poniższych informacji o środowisku:

- System: Windows 11
- Python: 3.10 (Miniconda)
- Edytor: VS Code
- GPU: RTX 3050 Laptop 4GB VRAM
- CPU: i5-12500H
- RAM: 32GB DDR4

Zawartość pliku CLAUDE.md:

---
# CLAUDE.md — TerraLens

## Kontekst projektu
- Projekt: [wypełnij na podstawie analizy TerraLens]
- Stack: [wypełnij na podstawie plików konfiguracyjnych]
- Środowisko: Windows 11, Miniconda (Python 3.10), VS Code
- Cel bieżący: [wypełnij jeśli wynika z kodu/README, w przeciwnym razie: "Do ustalenia przy pierwszej sesji"]

## Zasady pracy
- Zawsze sprawdzaj MEMORY.md przed podjęciem decyzji architektonicznej
- Nie duplikuj rozwiązań już opisanych w MEMORY.md
- Przy każdej nowej sesji: zacznij od /start
- Przy zakończeniu sesji: zawsze wywołaj /end
- W trakcie dłuższej pracy rób checkpointy przez /save

## Konwencje projektu
- Nazewnictwo plików: snake_case
- Język komentarzy w kodzie: polski
- Styl commitów: conventional commits (feat:, fix:, refactor:, docs:)
- [dopisz inne konwencje jeśli wykryjesz je w kodzie]

## Pliki stanu sesji
- MEMORY.md       — długoterminowa pamięć projektu (czytaj na /start)
- last_session.md — stan ostatniej sesji (czytaj na /start, pisz na /end)

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
---

═══════════════════════════════════════════════════════════════════
KROK 4 — Plik MEMORY.md
═══════════════════════════════════════════════════════════════════

Utwórz pusty plik MEMORY.md z poniższą strukturą sekcji:

---
# MEMORY.md — Długoterminowa pamięć projektu TerraLens

> Ten plik kumuluje wiedzę o projekcie. Nigdy nie usuwaj wpisów — tylko dopisuj.
> Każdy wpis oznaczaj datą w formacie [YYYY-MM-DD].

---

## Architektura

<!-- Claude dopisuje tutaj decyzje architektoniczne wraz z uzasadnieniem -->

_Brak wpisów — zostaną dodane przy pierwszych decyzjach architektonicznych._

---

## Rozwiązane problemy

<!-- Gotowe rozwiązania trudnych problemów — żeby nie szukać ich ponownie -->

_Brak wpisów._

---

## Aktywne TODO (długoterminowe)

<!-- Zadania rozlewające się przez wiele sesji. Krótkoterminowe są w last_session.md -->

_Brak wpisów._

---

## Odrzucone podejścia

<!-- Co nie działało i dlaczego — unikamy powtarzania błędów -->

_Brak wpisów._

---

## Słownik projektu

<!-- Specyficzne terminy używane w TerraLens -->

_Brak wpisów._

---

## Zewnętrzne zależności i integracje

<!-- Klucze API, serwisy zewnętrzne, specyficzne biblioteki -->

_Brak wpisów._
---

═══════════════════════════════════════════════════════════════════
KROK 5 — Plik last_session.md
═══════════════════════════════════════════════════════════════════

Utwórz plik last_session.md z poniższą zawartością jako stan startowy:

---
# last_session.md

Sesja: [DATA_UTWORZENIA] · Setup systemu zarządzania sesjami
Status: ✓ Pierwsza sesja — system zainstalowany

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Uruchom /start aby zweryfikować że system działa poprawnie, następnie ustal z Piotrem cel bieżący projektu TerraLens i zaktualizuj sekcję "Cel bieżący" w CLAUDE.md.**

Kontekst: system Session State Management został dopiero zainstalowany. Pierwsza prawdziwa sesja pracy nie miała jeszcze miejsca.

---

## Co zrobiono w tej sesji

- ✓ Utworzono strukturę .claude/commands/
- ✓ Utworzono CLAUDE.md z kontekstem projektu
- ✓ Utworzono MEMORY.md (pusty szablon)
- ✓ Utworzono last_session.md (ten plik)
- ✓ Utworzono 4 pliki komend: start.md, save.md, end.md, status.md

## Co zostało (backlog sesji)

- ⟳ Wypełnić sekcję "Cel bieżący" w CLAUDE.md
- ⟳ Pierwsze zadanie developerskie do ustalenia

## Aktywne pliki

- CLAUDE.md
- MEMORY.md
- last_session.md

## Otwarte pytania

- Jaki jest aktualny cel/faza projektu TerraLens?
- Które pliki są teraz najważniejsze w pracy?

## Do MEMORY.md (przeniesiono)

_Brak — pierwsza sesja techniczna, nie ma jeszcze decyzji do długoterminowej pamięci._
---

Zamień [DATA_UTWORZENIA] na aktualną datę w formacie YYYY-MM-DD.

═══════════════════════════════════════════════════════════════════
KROK 6 — Pliki komend w .claude/commands/
═══════════════════════════════════════════════════════════════════

Utwórz następujące 4 pliki:

──────────────────────────────────────────
PLIK: .claude/commands/start.md
──────────────────────────────────────────

# /start — Inicjalizacja sesji

Wykonaj następujące kroki w podanej kolejności:

1. Odczytaj plik MEMORY.md i przyswój jego zawartość jako kontekst projektu.

2. Odczytaj plik last_session.md. Jeśli plik nie istnieje,
   poinformuj że to pierwsza sesja projektu.

3. Wyświetl raport startowy w formacie:
   - Projekt: [nazwa z CLAUDE.md]
   - Ostatnia sesja: [data z last_session.md]
   - Następny krok: [sekcja "NASTĘPNY KROK" z last_session.md]
   - Aktywne pliki: [lista z last_session.md]
   - Otwarte pytania: [jeśli istnieją]

4. Zapytaj: "Czy zaczynamy od następnego kroku, czy jest inne zadanie?"

──────────────────────────────────────────
PLIK: .claude/commands/save.md
──────────────────────────────────────────

# /save — Checkpoint sesji

Wykonaj następujące kroki (bez kończenia sesji):

1. Zaktualizuj sekcje "Co zrobiono" i "Co zostało" w last_session.md
   odzwierciedlając aktualny postęp. Nie zastępuj całego pliku —
   aktualizuj tylko te sekcje.

2. Jeśli w tej chwili podjęto ważną decyzję architektoniczną
   lub rozwiązano trudny problem — dopisz to do MEMORY.md
   w odpowiedniej sekcji z datą [YYYY-MM-DD].

3. Zaktualizuj "Aktywne pliki" jeśli zmienił się zestaw plików roboczych.

4. Potwierdź: "✓ Checkpoint zapisany o [HH:MM]. Kontynuujemy."

UWAGA: To NIE jest /end — sesja trwa dalej. Nie przekazuj podsumowania końcowego.

──────────────────────────────────────────
PLIK: .claude/commands/end.md
──────────────────────────────────────────

# /end — Zamknięcie sesji

Wykonaj następujące kroki:

1. Podsumuj co zostało zrobione w tej sesji (lista bullet points z ✓).

2. Zidentyfikuj JEDEN konkretny następny krok — możliwie szczegółowy
   (konkretna funkcja, plik, konkretna akcja). Unikaj ogólników typu
   "kontynuować pracę" albo "dokończyć feature X".

3. Jeśli w tej sesji podjęto decyzje architektoniczne lub znaleziono
   rozwiązanie trudnego problemu — dopisz je do MEMORY.md
   w odpowiedniej sekcji z datą [YYYY-MM-DD].

4. Nadpisz last_session.md w całości nową zawartością zgodnie
   z poniższym formatem:

   # last_session.md

   Sesja: [YYYY-MM-DD] · [HH:MM-HH:MM]
   Status: ✓ Zakończona poprawnie

   ---

   ## ▸ NASTĘPNY KROK (zacznij tutaj)

   [JEDEN konkretny następny krok z KROKU 2]

   Kontekst: [2-3 zdania dlaczego to jest następny krok]

   ---

   ## Co zrobiono w tej sesji
   [lista z KROKU 1]

   ## Co zostało (backlog sesji)
   [niedokończone zadania]

   ## Aktywne pliki
   [pliki z którymi pracowaliśmy]

   ## Otwarte pytania
   [nierozstrzygnięte kwestie]

   ## Do MEMORY.md (przeniesiono)
   [co dopisano do MEMORY.md w KROKU 3]

5. Potwierdź: "✓ Sesja zapisana. Następny krok: [następny krok z KROKU 2]"

──────────────────────────────────────────
PLIK: .claude/commands/status.md
──────────────────────────────────────────

# /status — Podgląd stanu

Odczytaj last_session.md i wyświetl:

1. Następny krok (sekcja "NASTĘPNY KROK")
2. Co zostało do zrobienia (sekcja "Co zostało")
3. Aktywne pliki
4. Otwarte pytania (jeśli są)

UWAGA: Nie modyfikuj żadnego pliku. To komenda tylko do odczytu.

═══════════════════════════════════════════════════════════════════
KROK 7 — Aktualizacja .gitignore
═══════════════════════════════════════════════════════════════════

Jeśli .gitignore istnieje — dopisz na końcu pliku sekcję:

# --- Claude Code Session System ---
# last_session.md zawiera stan sesji — jeśli nie chcesz commitować, odkomentuj:
# last_session.md
# CLAUDE.md.backup_*

Jeśli .gitignore nie istnieje — nie twórz go na potrzeby tego setupu.

═══════════════════════════════════════════════════════════════════
KROK 8 — Weryfikacja
═══════════════════════════════════════════════════════════════════

Po utworzeniu wszystkich plików:

1. Wyświetl drzewo utworzonych plików w formacie:
   TerraLens/
   ├── CLAUDE.md                     [✓ utworzony]
   ├── MEMORY.md                     [✓ utworzony]
   ├── last_session.md               [✓ utworzony]
   └── .claude/
       └── commands/
           ├── start.md              [✓ utworzony]
           ├── save.md               [✓ utworzony]
           ├── end.md                [✓ utworzony]
           └── status.md             [✓ utworzony]

2. Wyświetl krótkie podsumowanie:
   - Ile plików utworzono
   - Co Piotr powinien zrobić teraz (uruchomić /start w nowej sesji)
   - Przypomnienie że CLAUDE.md można doedytować ręcznie gdy TerraLens
     zyska konkretny "cel bieżący"

3. NIE uruchamiaj /start w tej sesji — setup to setup. Pierwszy /start
   Piotr wywoła sam po ponownym uruchomieniu Claude Code.

═══════════════════════════════════════════════════════════════════
KONIEC PROMPTU
===================================================================
PROMPT END
===================================================================
```

---

## Po wykonaniu — co dalej?

Po tym jak Claude Code zakończy setup:

1. **Zamknij sesję Claude Code** (ctrl+C lub exit)
2. **Uruchom ponownie w katalogu TerraLens** — `claude`
3. **Wpisz `/start`** — powinieneś zobaczyć raport startowy
4. **Wypełnij "Cel bieżący"** w CLAUDE.md — to jedyna rzecz której nie mogłem ustalić automatycznie

---

## Tipy i rady dotyczące użytkowania

### 🎯 Dyscyplina komend

**Zawsze kończ przez `/end`**. To jest cały sens systemu. Jeśli zamkniesz terminal bez `/end` — `last_session.md` nie zostanie zaktualizowany i stracisz kontekst. Wyrób nawyk: `/end` → potwierdzenie → dopiero zamknięcie okna.

### 💾 Rób `/save` po każdym większym ukończonym kawałku

Dobrym rytmem jest `/save` po:
- Zakończonej implementacji funkcji
- Rozwiązaniu buga
- Przed eksperymentem który może wysadzić stan
- Przed przerwą >30 min

Traktuj to jak `git commit` — tanie, częste, bez straty.

### 📝 Jakość "następnego kroku" decyduje o wszystkim

Najcenniejsza linia w całym systemie to **NASTĘPNY KROK** w `last_session.md`.

❌ **Zły**: "Kontynuować pracę nad enginem"
❌ **Zły**: "Dokończyć feature X"
✅ **Dobry**: "Zaimplementować metodę `process_batch()` w `src/engines/terra_engine.py` — iteracja po listach > 1000 elementów ma używać chunking co 128"

Jeśli Claude Code przy `/end` wypisze zbyt ogólny następny krok — popraw go ręcznie przed zamknięciem.

### 🧠 MEMORY.md to archiwum, nie notatnik

Nie dopisuj tam wszystkiego. Wpis do MEMORY.md zasługuje na to gdy:
- To **decyzja architektoniczna** (wybór biblioteki, wzorca, struktury)
- To **rozwiązanie problemu który trwał >30 min** (żeby nie szukać ponownie)
- To **odrzucone podejście** (żeby za pół roku nie próbować tego samego)
- To **gotcha środowiska** (specyficzne dla Twojego sprzętu/OS)

Codzienny postęp zostaje w `last_session.md`.

### 🔄 Co jakiś czas — review MEMORY.md

Raz na 2-3 tygodnie przejrzyj MEMORY.md sam. Niektóre wpisy mogą być nieaktualne (bo refactor), inne warto przenieść wyżej. Claude tego nie zrobi za Ciebie — to Twoja długoterminowa pamięć, nie jego.

### 🚫 Nie commituj `last_session.md` na public repo

Może zawierać nazwy plików, fragmenty decyzji biznesowych, otwarte pytania. Jeśli projekt jest publiczny (jak NeuroMosaic na GitHubie) — dodaj do `.gitignore`. MEMORY.md też warto przemyśleć — tam zwykle są rzeczy które MOŻESZ upublicznić (architektura), ale decyzja Twoja.

### 🔗 Integracja z GitNexusem

Jeśli używasz GitNexus w TerraLens — warto w CLAUDE.md dopisać sekcję `## Przed refactorem` z przypomnieniem o `impact` / `detect_changes` / `dry_run`. Claude Code odczyta to automatycznie.

### 📦 Portability — szablon dla kolejnych projektów

Po sprawdzeniu że wszystko działa w TerraLens — skopiuj gotowe pliki do:

```
D:\Programming_Projects\_global\session-template\
├── CLAUDE.md.template        ← z placeholderami zamiast TerraLens
├── MEMORY.md
├── last_session.md
└── .claude/commands/*.md
```

Wtedy w każdym nowym projekcie wystarczy:
```powershell
Copy-Item -Recurse D:\Programming_Projects\_global\session-template\* .
```

### ⚠️ Typowe pułapki

- **`/save` traktowane jak `/end`** — pamiętaj: `/save` nie kończy sesji, `/end` kończy. Po `/save` praca trwa.
- **Edytowanie `last_session.md` ręcznie w trakcie sesji** — Claude nadpisze przy `/end`. Jeśli chcesz coś dopisać trwale, powiedz to Claude i wywołaj `/save`.
- **Zapominanie o `/start`** — bez tego Claude nie wie co było ostatnio. Nawet jeśli "tylko szybki fix" — zacznij od `/start`.
- **Zbyt długi MEMORY.md** — gdy przekroczy ~500 linii, przejrzyj i wywal nieaktualne. Claude czyta go za każdym razem — zbyt długi = marnowanie tokenów.

### 🧪 Test działania po setupie

Po pierwszym `/start` w nowej sesji Claude Code, sprawdź czy:
- Widzisz raport startowy z nazwą "TerraLens"
- Pokazuje się "Następny krok"
- Lista aktywnych plików się wyświetla

Jeśli któryś element nie działa — najprawdopodobniej nazwa pliku komendy jest zła lub plik jest w złej lokalizacji. Claude Code szuka komend w `.claude/commands/*.md` (nie w `.claude-code/` ani `commands/` w roocie).
