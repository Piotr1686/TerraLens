# last_session.md

Sesja: 2026-06-16 · 19:00-22:00
Status: ✓ Zakończona poprawnie
Punkt odniesienia (git): 198db31 @ master

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**S10 Workstream 3 — Frontend Explore Mode (ZERO-BACKEND).** Zacznij od `frontend/src/lib/mpc.ts`:
port logiki scene-pick z `scripts/poc_sentinel2.py` do TS — STAC `POST /api/stac/v1/search`
(`collections=[sentinel-2-l2a]`, filtr `eo:cloud_cover`, wybór min cloud + świeża) → zwróć `itemId`;
plus helper budujący URL kafla `…/api/data/v1/item/tiles/WebMercatorQuad/{z}/{x}/{y}@1x.png?collection=sentinel-2-l2a&item=<id>&assets=visual`.
Potem: `SearchBox.tsx` (Nominatim), `useSentinelLayer.ts` (deck.gl `TileLayer`, mirror `Globe.tsx:85-97`),
tryb Explore w `App.tsx`/`Globe.tsx` (addytywny, cap zoomu street-level). Kandydat na `/sonnet`.

Kontekst: PoC S2 udany (10 m street-level), CORS `*` na STAC + tile endpoint potwierdzony → backend
NIEpotrzebny (front woła MPC bezpośrednio). Architektura w planie:
`C:\Users\plazo\.claude\plans\joyful-twirling-nova.md`.

---

## Co zrobiono w tej sesji

- ✓ **ESRGAN-w-PMTiles WDROŻONY** (commit `1088c52`) — `process` (+`--date`), `export` (+`--sr`).
  Render 52 kafle 2048² SR (amazonia z6+z7, 2023-07-01) → `amazonia_v20260616_190200.pmtiles` (14 MB)
  → deploy HF. Zweryfikowane e2e: kafel z7 z HF = 2048² SR. **Domyka lukę AI/ML dla amazonii.**
- ✓ **Skan zachmurzenia** (commit `198db31`, `scripts/scan_cloud_cover.py`) — 2023-07-01 to obiektywnie
  najczystsza data amazonii (cloud_frac 0.219). Rozpoznano sufit Architektury A (z7 ≈120 m/px); „brak
  różnicy" na prod = lokalny cache przeglądarki (ścieżka HF→SR zweryfikowana jako poprawny SR).
- ✓ **/architect S10 + pivot na Sentinel-2** — architektura zatwierdzona (MPC hostowany tiler).
- ✓ **PoC Sentinel-2 UDANY** (commit `198db31`, `scripts/poc_sentinel2.py`) — scena 0.0% chmur, kafel
  pctiler `assets=visual`, ostrość 10 m (Dubai street-level). SSL: `pystac` hardkoduje `verify=True`
  → fix env `REQUESTS_CA_BUNDLE`=`win-ca-bundle.pem`.
- ✓ **Backend rozstrzygnięty = ZERO-BACKEND** — Cloudflare odpadł (brak konta), ale zbędny: tiler MPC
  publiczny + STAC/data-API `ACAO: *` → front woła MPC bezpośrednio.
- ✓ **MEMORY** zaktualizowany: wpis [2026-06-16] (SR + pivot S2 + zero-backend + niuans SSL pystac).

## Co zostało (backlog sesji)

- ⧗ **S10 WS3 frontend** — `lib/mpc.ts` + `SearchBox` + `useSentinelLayer` + tryb Explore (patrz NASTĘPNY KROK).
- ⧗ **S10 WS4 polish** — picker daty/cloud, atrybucja Sentinel-2/MPC, cap zoomu kamery, stany błędu/empty.
- ⧗ **Formalizacja S10 w MASTER_PLAN.md** — nie ma jeszcze sprintu S10; taksonomia S3 używa starej nazwy
  „Satlas" (pivot na Real-ESRGAN + S2 nieodzwierciedlony). Do uporządkowania przy starcie WS3.
- ⧗ **Follow-up SR dubai+arctic** (opcjonalnie — ten sam wzorzec; arctic = MODIS_Terra dla lat≥70).

## Aktywne pliki

- `scripts/poc_sentinel2.py` — PoC S2 (scene-pick + tile URL); **baza do portu** `frontend/src/lib/mpc.ts`
- `scripts/scan_cloud_cover.py` — ranking dat wg zachmurzenia (reuse dla dubai/arctic)
- `frontend/src/components/Globe.tsx` — `makeTileLayer` (`:85-97`, mirror dla `useSentinelLayer`); `controller` free-zoom
- `frontend/src/App.tsx` — miejsce na tryb Explore (addytywny do hooka 3-regionowego)
- (do powstania) `frontend/src/lib/mpc.ts`, `components/SearchBox.tsx`, `hooks/useSentinelLayer.ts`

## Otwarte pytania

- Geocoder: Nominatim (ToS ≤1 req/s) wystarczy na demo, czy od razu managed (Photon/Mapbox)?
- ESRGAN SR jako opcjonalny dopał na kaflach S2 — czy w ogóle potrzebny przy realnym 10 m?
- Cap zoomu kamery dla street-level — jaki maxZoom GlobeView dla S2 z14?

## Do MEMORY.md (przeniesiono)

- [2026-06-16] SR wdrożony (`1088c52`) + pivot S2/S10 (MPC, PoC udany, params `assets=visual` zapinowane,
  zero-backend bo CORS `*` + tiler publiczny) + niuans SSL `pystac` (`verify=True` → `REQUESTS_CA_BUNDLE`).
  Wpis w projektowym MEMORY.md, sekcja Architektura.
