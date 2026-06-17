# last_session.md

Sesja: 2026-06-17 · 22:00-23:18
Status: ✓ Zakończona poprawnie
Punkt odniesienia (git): 2d05d6f @ master

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**T10.5 — paginacja historii S2 w trybie Explore.** Oś czasu sięga wstecz tylko ~2025
(objaw zgłoszony przez Piotra), bo `listScenes()` w `frontend/src/lib/mpc.ts` ma `limit:250`,
co przy ~2 orbitach na punkt daje <2 lata. Dodać paginację STAC (`token`/`next` link z
odpowiedzi `/search`) ALBO strategię „best-per-month" dla głębszej historii do 2015 bez
pobierania tysięcy scen. Potem smoke wizualny: przejazd suwakiem przez wiele lat.

Kontekst: tryb Explore (kaskada NAIP→S2 + oś czasu + przełącznik źródła) wdrożony i zweryfikowany
e2e dziś; to jedyne znane ograniczenie funkcjonalne. MPC search wrócił do działania po przejściowym
outage (504). Reszta T10.5 (cap kamery per-strefa, ESRGAN-dopał) niżej w backlogu.

---

## Co zrobiono w tej sesji

- ✓ **S10 WS3 — Explore Mode wdrożony** (commit `ccea853`) — `lib/mpc.ts` (scene-pick, port z PoC),
  `lib/geocode.ts` (Nominatim), `useExploreLayer.ts`, `SearchBox.tsx`, prop `flyToCoords`+cap zoomu w
  `Globe.tsx`, tryb addytywny w `App.tsx`. tsc+build czyste; STAC POST + tile endpoint zweryfikowane na żywo.
- ✓ **Kaskada źródeł NAIP→S2** (commit `f9d8fd2`) — `resolveScene` (potem `listScenes`): NAIP 0.6 m (USA, z18,
  `assets=image asset_bidx=image|1,2,3`) → fallback S2 10 m (z14, `assets=visual`). Kafle `@2x` retina.
  Cap kamery per źródło. Decyzja: realne>syntetyczne, ESRGAN odłożony. NAIP @2x z18 zweryfikowany (SF, 0.6 m).
- ✓ **Odporność na awarie MPC** (commit `c4caa09`) — NAIP failure → fallback S2; `stacSearch` timeout per
  próba + retry na 504/503; relaks progu chmur; łagodny komunikat błędu. Zdiagnozowany przejściowy outage MPC
  search (504 ~30 s dla wszystkiego, health 200) — degradacja po stronie Microsoftu, nie nasz bug.
- ✓ **Oś czasu + ręczny przełącznik źródła** (commit `a478603`) — `listScenes()` (NAIP 24 + S2 250, bez
  filtra chmur), `useExploreScenes`/`useExploreLayer` (split), `useExploreSelection`, `ExploreControls.tsx`
  (suwak dat, przełącznik NAIP/S2, toggle „Clear skies only" <20% off domyślnie). Listy zweryfikowane na żywo.
- ✓ **MASTER_PLAN** — sprint S10 sformalizowany (T10.3/T10.4 DONE, T10.5 TODO), taksonomia S3 poprawiona
  (Satlas→Real-ESRGAN). MEMORY projektowy + auto-memory zaktualizowane (`project_explore_source_cascade`).

## Co zostało (backlog sesji)

- ⧗ **T10.5 paginacja S2** — patrz NASTĘPNY KROK (oś czasu tylko do ~2025).
- ⧗ **T10.5 pozostałe** — dokładniejszy cap kamery per-strefa, rozbudowane stany empty/error,
  opcjonalny ESRGAN-dopał na kaflach S2 (świadomie odłożony — `project_explore_source_cascade`).
- ⧗ **Smoke wizualny Explore** — przełączanie źródła/dat/filtra na `npm run dev` (SF/Manhattan dla NAIP,
  Dubai dla S2) — częściowo potwierdzone przez Piotra (działa; objaw daty-do-2025 zgłoszony).
- 🟡 **Push** — `master` 9 commitów przed `origin/master` (niezpushowane); Vercel auto-deploy po pushu.

## Aktywne pliki

- `frontend/src/lib/mpc.ts` — `listScenes()` (kaskada NAIP+S2), `stacSearch` (timeout+retry), `@2x`, `lonLatToTile`
- `frontend/src/hooks/useExploreLayer.ts` — `useExploreScenes` (lista) + `useExploreLayer` (warstwa z wybranej sceny)
- `frontend/src/hooks/useExploreSelection.ts` — stan: źródło/filtr chmur/index daty
- `frontend/src/components/ExploreControls.tsx` — suwak dat + przełącznik źródła + toggle chmur
- `frontend/src/components/SearchBox.tsx`, `frontend/src/lib/geocode.ts` — wyszukiwarka (Nominatim)
- `frontend/src/App.tsx`, `frontend/src/components/Globe.tsx` — wpięcie trybu Explore (addytywne)

## Otwarte pytania

- Paginacja S2 vs best-per-month dla głębi historii (>250 scen) — która strategia (T10.5)?
- ESRGAN-dopał na S2 poza USA — czy w ogóle (świadomie odłożony, real 10 m może wystarczyć)?
- Geocoder: Nominatim wystarczy na demo, czy managed przy większym ruchu?

## Do MEMORY.md (przeniesiono)

- [2026-06-17] S10 Explore FRONTEND wdrożony — kaskada NAIP→S2 + oś czasu + przełącznik źródła, zero-backend,
  `@2x` retina, odporność na 504 MPC, ograniczenie limit:250. Wpis w projektowym MEMORY.md (Architektura).
- `project_explore_source_cascade` (auto-memory) — decyzja: realne źródło per lokalizacja, ESRGAN odłożony.
