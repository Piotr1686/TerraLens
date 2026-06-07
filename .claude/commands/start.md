# /start — Inicjalizacja sesji

Wykonaj następujące kroki w podanej kolejności:

1. Odczytaj plik MEMORY.md i przyswój jego zawartość jako kontekst projektu.

2. Odczytaj plik last_session.md. Jeśli plik nie istnieje,
   poinformuj że to pierwsza sesja projektu.

3. SANITY-CHECK (desync): porównaj sekcję "NASTĘPNY KROK" oraz pole
   "Punkt odniesienia (git)" z aktualnym stanem repo. Uruchom `git status`
   oraz `git log --oneline <zapisany_HEAD>..HEAD` i zasygnalizuj jeśli:
   - pliki/taski wskazane w "następnym kroku" zostały już zmienione/usunięte,
   - są commity wykonane po zapisaniu sesji (praca poza Claude Code),
   - są niezacommitowane zmiany, których last_session.md nie odnotowuje,
   - statusy tasków w MASTER_PLAN.md rozjeżdżają się z faktycznym stanem kodu.
   Jeśli wszystko spójne — napisz krótko "Stan spójny z ostatnią sesją".

4. Wyświetl raport startowy w formacie:
   - Projekt: [nazwa z CLAUDE.md]
   - Ostatnia sesja: [data z last_session.md]
   - Punkt odniesienia: [HEAD z last_session.md] → teraz: [aktualny HEAD]
   - Następny krok: [sekcja "NASTĘPNY KROK" z last_session.md]
   - Aktywne pliki: [lista z last_session.md]
   - Otwarte pytania: [jeśli istnieją]
   - Desync: [wynik z kroku 3]

5. Zapytaj: "Czy zaczynamy od następnego kroku, czy jest inne zadanie?"
