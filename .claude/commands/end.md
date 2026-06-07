# /end — Zamknięcie sesji

Wykonaj następujące kroki:

1. WERYFIKACJA WSTĘPNA: uruchom logikę /recover (kroki 1-4). Jeśli wykryto ⚠ lub
   niedokończone naprawy o wysokim priorytecie — POKAŻ je i zapytaj:
   "Wykryto [N] punktów do uwagi. Zamknąć mimo to, czy najpierw naprawić?"
   Czekaj na decyzję. Nie zamykaj po cichu nad niespójnym stanem.

2. Podsumuj co zostało zrobione w tej sesji (lista bullet points z ✓).

3. Zidentyfikuj JEDEN konkretny następny krok — możliwie szczegółowy
   (konkretny task ID / plik / akcja). Unikaj ogólników typu "kontynuować pracę".

4. Jeśli w tej sesji podjęto decyzje architektoniczne lub znaleziono
   rozwiązanie trudnego problemu — dopisz je do MEMORY.md
   w odpowiedniej sekcji z datą [YYYY-MM-DD]. Zaktualizuj statusy tasków w MASTER_PLAN.md.

5. COMMIT KODU (opcjonalny, ZAWSZE po potwierdzeniu): sprawdź `git status`. Jeśli są
   niezacommitowane zmiany w KODZIE/dokumentach (poza plikami stanu sesji):
   - Zaproponuj treść commitu wg konwencji projektu — conventional commits z ID taska:
     `feat(T1.2): ...`, `fix(T2.3): ...`, `refactor(T4.1): ...`, `docs(S5): ...`,
     `test(T3.2): ...`. Zgrupuj logicznie; rozdziel backend od frontendu jeśli trzeba.
   - Wykonaj commit DOPIERO po akceptacji użytkownika.
   - NIGDY nie rób `git push` automatycznie — co najwyżej zaproponuj jako sugestię.
   Jeśli working tree (poza stanem sesji) jest czyste — pomiń ten krok.

6. Ustal nowy "Punkt odniesienia (git)": aktualny HEAD (skrócony hash) + branch
   (`git rev-parse --short HEAD`, `git rev-parse --abbrev-ref HEAD`) — już PO
   ewentualnym commicie kodu z kroku 5.

7. ARCHIWIZACJA (bezpiecznik): zanim nadpiszesz last_session.md, dopisz jego BIEŻĄCĄ
   zawartość NA POCZĄTEK pliku last_session.archive.md, poprzedzoną separatorem:

       ## ═══ Sesja zarchiwizowana [YYYY-MM-DD HH:MM] ═══

   Jeśli last_session.archive.md nie istnieje — utwórz go. Trzymaj w archiwum
   maksymalnie 5 ostatnich sesji (starsze usuwaj z dołu pliku).

8. Nadpisz last_session.md w całości nową zawartością zgodnie z poniższym formatem:

   # last_session.md

   Sesja: [YYYY-MM-DD] · [HH:MM-HH:MM]
   Status: ✓ Zakończona poprawnie
   Punkt odniesienia (git): [HEAD] @ [branch]

   ---

   ## ▸ NASTĘPNY KROK (zacznij tutaj)

   [JEDEN konkretny następny krok z KROKU 3]

   Kontekst: [2-3 zdania dlaczego to jest następny krok]

   ---

   ## Co zrobiono w tej sesji
   [lista z KROKU 2]

   ## Co zostało (backlog sesji)
   [niedokończone zadania + ⟳ z audytu]

   ## Aktywne pliki
   [pliki z którymi pracowaliśmy]

   ## Otwarte pytania
   [nierozstrzygnięte kwestie + ⚠ z audytu]

   ## Do MEMORY.md (przeniesiono)
   [co dopisano do MEMORY.md w KROKU 4]

9. COMMIT PLIKÓW STANU (opcjonalny, po potwierdzeniu): zaproponuj osobny commit
   obejmujący WYŁĄCZNIE pliki stanu/planu sesji (last_session.md, MEMORY.md,
   MASTER_PLAN.md jeśli zmieniono statusy tasków, ewentualnie archiwa), oddzielony
   od commitu kodu: `chore(session): zapis stanu sesji [YYYY-MM-DD]`. Wykonaj po
   akceptacji. Bez push. Pomiń, jeśli user nie chce commitować stanu.

10. HIGIENA PAMIĘCI (warunkowo): sprawdź liczbę linii MEMORY.md. Jeśli > 400 —
    ZAPROPONUJ (nie wykonuj automatycznie) konsolidację:
    "MEMORY.md ma [N] linii. Przenieść zamknięte TODO i nieaktualne decyzje do
    MEMORY.archive.md? (zostaną tylko aktywne wpisy)" — wykonaj tylko po potwierdzeniu.

11. Potwierdź: "✓ Sesja zapisana ([HH:MM]). Punkt odniesienia: [HEAD].
    Następny krok: [następny krok z KROKU 3]"
