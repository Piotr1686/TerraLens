# /recover — Audyt i naprawa stanu (bezpiecznik przed /end)

Cel: zanim zamkniesz sesję, sprawdź czy to, co faktycznie zostało zmienione, zgadza się
z planem (MASTER_PLAN.md) i czy projekt jest w spójnym stanie. To komenda DIAGNOSTYCZNA —
domyślnie NIE modyfikuje kodu ani plików stanu; proponuje naprawy i czeka na decyzję.

Ustal "punkt odniesienia wstecz" (do którego momentu cofamy analizę), w tej kolejności:
   a) pole "Punkt odniesienia (git)" zapisane w last_session.md (HEAD z końca poprzedniej sesji),
   b) jeśli brak — ostatni checkpoint /save / ostatni wspólny commit,
   c) jeśli brak repo — analizuj pliki zmodyfikowane od daty ostatniej sesji.

Wykonaj:

1. ZMIANY FAKTYCZNE — zbierz co realnie zmieniło się od punktu odniesienia:
   - `git status` (niezacommitowane),
   - `git diff --stat <punkt_odniesienia>..HEAD` oraz diff working tree,
   - lista nowych/usuniętych plików (oddziel backend Python od frontend React/TS).

2. PLAN vs RZECZYWISTOŚĆ — porównaj z "NASTĘPNY KROK", "Co zostało" i MASTER_PLAN.md:
   - Które taski (ID) z planu zostały zrobione? (✓)
   - Co z planu NIE zostało ruszone? (⟳)
   - Co zostało zmienione, a NIE było w planie? (⚠ — możliwy scope creep / przypadek)
   - Czy nie przeskoczono Dependencies (np. ruszono T2.3 bez ukończenia T2.1)?

3. KONTROLA SPÓJNOŚCI (lekka, bez ciężkiego uruchamiania):
   - Czy pliki/taski wspomniane w "następnym kroku" istnieją?
   - Ślady niedokończonej pracy: TODO/FIXME/XXX dodane w tej sesji, zakomentowany kod,
     `pass`/stuby, importy nieużywane.
   - Jeśli zmieniono kod — ZAPROPONUJ uruchomienie pre-commit (ruff) + `pytest`
     (backend) lub `npm run build`/lint (frontend). Nie uruchamiaj automatycznie jeśli
     kosztowne; zapytaj.
   - TerraLens-specyficzne: czy ukończone taski mają zaktualizowany status w MASTER_PLAN.md
     (✓ DONE / ⟳ IN PROGRESS / ✗ BLOCKED)? Czy commity mają format z ID taska
     (`feat(T1.2): ...`)? Jeśli ruszono decyzje AI/ML — czy zgodne z PROJECT_BRIEF.md?
   - Zmiany w `environment.yml`/`pyproject.toml`/`package.json` wymagające reinstalacji?
     Zmiany w pipeline obrazów — czy trzymają się tiled 512×512 / FP16 / @vram_safe?

4. RAPORT NAPRAWCZY:

   🔧 AUDYT STANU (od [punkt_odniesienia] do teraz)

   ✅ Zrobione zgodnie z planem (taski):
      [lista]
   ⟳ Z planu, niezrobione:
      [lista]
   ⚠ Zmiany poza planem / do weryfikacji:
      [lista]
   🩹 Sugerowane naprawy PRZED zamknięciem sesji (priorytetowo):
      1. [konkretna naprawa — plik:linia lub task ID, co zrobić]
      2. ...
   🧪 Weryfikacja zalecana: [testy/lint/build do uruchomienia lub "brak"]

5. Zakończ pytaniem: "Naprawić teraz wskazane punkty, przejść do /end, czy kontynuować pracę?"
   Naprawy wykonuj TYLKO po potwierdzeniu.
