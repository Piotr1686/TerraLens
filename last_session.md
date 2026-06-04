# last_session.md

Sesja: 2026-06-04 · 20:30-21:20
Status: ✓ Zakończona poprawnie

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Dorób realne heatmapy NDVI** (analogicznie do SSIM, które już są realne). Konkretnie:
w `scripts/build_heatmaps.py` dodaj render PNG dla metryki NDVI — różnica NDVI first-vs-last
per tile (reużyj `processors/ndvi.py` + wzorzec `export_heatmap()` jak dla SSIM), colormap
np. RdYlGn z NaN→alpha 0; deploy przez `terralens deploy-heatmaps` jako
`{region}_ndvi_heatmap/{z}/{x}/{y}.png`; w `frontend/src/hooks/useHeatmapLayer.ts` podłącz
gałąź `metric === 'ndvi'` do realnych PNG (multi-BitmapLayer 4326, dokładnie jak istniejąca
ścieżka SSIM, linie ~57-101 i ~107-118) zamiast demo GIBS TileLayer.

Kontekst: SSIM to jedyna realna heatmapa; NDVI/CVA wciąż demo GIBS — to ostatnia widoczna
część luki AI/ML (`project_intelligence_layer_gap`). Ścieżka SSIM jest sprawdzona i działa
na produkcji, więc NDVI to powielenie gotowego wzorca, niskie ryzyko.

---

## Co zrobiono w tej sesji

- ✓ **Zdiagnozowano awarię produkcji dowodami** (konsola + grep bundla + `vercel ls/inspect`),
  nie zgadywaniem: glob rozbity bo produkcja serwowała bundle sprzed 31+ dni.
- ✓ **Znaleziono root cause:** root `.gitignore` wzorzec `data/` (niezakotwiczony) łapał
  `frontend/src/data/` → `regions.ts` nigdy nie w gicie → na Linuxie/Vercel `TS2307` →
  każdy auto-build padał ~31 dni (seria ● Error).
- ✓ **Naprawa natychmiastowa:** vercel CLI prebuilt deploy + przepięcie aliasu `terra-lens-zeta`
  (przez `NODE_EXTRA_CA_CERTS` = bundle certów Windows, bo maszyna przechwytuje TLS).
- ✓ **Naprawa przyczyny:** `.gitignore` `data/` → `/data/`, zacommitowany `regions.ts`.
  Commit `c19e052`, pushed (poszedł też zaległy docs `1c7f530`).
- ✓ **Weryfikacja end-to-end:** push wyzwolił auto-build → ● Ready 14s; prod serwuje poprawny
  bundle (`ssim_heatmap=1`, `epsg4326=0`). Użytkownik potwierdził wizualnie: glob zdrowy.
- ✓ **MEMORY:** wpis projektowy [2026-06-04] (Rozwiązane problemy) + auto-memory
  `bug_vercel_stale_deploy_gitignore` + index.

## Co zostało (backlog sesji)

- 🔭 **NDVI/CVA realne heatmapy** — patrz NASTĘPNY KROK (NDVI) i potem CVA tym samym wzorcem.
- 🔭 **ESRGAN-w-PMTiles** — wdrożone kafle to nadal bezpośredni GIBS, nie SR (reszta luki AI/ML).
- ⧗ **Sprint S10 — Explore Mode** (search Nominatim + free-zoom + Sentinel-2) — wymaga decyzji
  architektonicznej (backend on-demand: Cloudflare Worker vs Vercel Function; źródło S2).
- ⧗ **Więcej historii HLS_RGB** (multi-year) dla głębszego wykresu SSIM.
- 🧹 **Opcjonalnie:** posprzątać sprzeczne `buildCommand`/`outputDirectory` w dashboardzie Vercela
  (nie blokuje — `frontend/vercel.json` nadpisuje).

## Aktywne pliki

- `.gitignore` — `data/` → `/data/` (kluczowa poprawka tej sesji)
- `frontend/src/data/regions.ts` — teraz śledzony przez git (był ignorowany)
- `scripts/build_heatmaps.py` — następny cel: dodać render NDVI
- `frontend/src/hooks/useHeatmapLayer.ts` — następny cel: podłączyć NDVI do realnych PNG
- `processors/ndvi.py` — źródło do reużycia przy render NDVI diff

## Otwarte pytania

- NDVI/CVA: dorobić realne mapy teraz, czy zostawić demo do Sprintu S10? (rekomendacja: NDVI teraz)
- Sprint S10: backend on-demand (Cloudflare Worker vs Vercel Function) + źródło Sentinel-2?
- Posprzątać sprzeczne ustawienia build w dashboardzie Vercela? (opcjonalne)

## Do MEMORY.md (przeniesiono)

- `[2026-06-04]` (sekcja Rozwiązane problemy) — „Vercel stale-deploy 31 dni — `.gitignore data/`
  łykał frontend/src/data/regions.ts": objaw, root cause (TS2307 na Linuxie), diagnoza dowodami,
  fix (`/data/` + commit regions.ts), naprawa natychmiastowa (prebuilt CLI), gotcha TLS
  (`NODE_EXTRA_CA_CERTS`), reguła „weryfikuj hash bundla prod, nie tylko push". Commit `c19e052`.
- Auto-memory `bug_vercel_stale_deploy_gitignore` — ta sama wiedza w pamięci długoterminowej.
