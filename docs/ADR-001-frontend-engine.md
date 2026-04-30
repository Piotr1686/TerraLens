# ADR-001 — Frontend 3D Engine: Deck.gl GlobeView

**Data:** 2026-04-30
**Status:** Accepted
**Decydent:** Piotr Łazowski

---

## Kontekst

TerraLens wymaga renderowania interaktywnego globu 3D z tile'ami satelitarnymi (PMTiles/WMTS), animacją kamery i docelowo warstwą heatmap zmian. Sprint S6 przewidywał PoC dwóch silników: Deck.gl i R3F — z decision gate po ocenie cinematic quality.

## Oceniane opcje

| Kryterium (waga)             | Deck.gl GlobeView | R3F (Three.js) |
|------------------------------|-------------------|----------------|
| Cinematic quality (30%)      | 7/10              | nie testowano  |
| Performance desktop (30%)    | OK (>30 FPS)      | nie testowano  |
| Tile layer out-of-box (15%)  | ✓ TileLayer WMTS  | wymaga custom  |
| PMTiles integration (15%)    | ✓ natywne         | wymaga custom  |
| Maintenance burden (10%)     | niski             | wyższy         |

## Wyniki PoC (T6.2)

- GlobeView z `_GlobeView` + `TileLayer` działa out-of-the-box
- Blue Marble (GIBS WMTS EPSG:4326) renderuje się poprawnie
- Obrót globu myszką: smooth
- `FlyToInterpolator` (speed=1.5) daje płynne przejścia między regionami
- Timer-based tour (setTimeout per stop) działa stabilnie
- Cinematic tour (Amazonia → Dubai → Arktyka) — zaimplementowany, ocena wizualna odłożona do T7.5

## Decyzja

**Wybrano: Deck.gl GlobeView**

R3F PoC pominięty — Deck.gl spełnia wymagania MVP bez potrzeby porównania. Kluczowe czynniki:

1. TileLayer + PMTiles integracja jest natywna (zero custom shaderów na start)
2. EPSG:4326 tile math działa poprawnie z GIBS (zweryfikowane empirycznie)
3. Wystarczający performance na RTX 3050 / desktop
4. Cinematic tour do dopracowania w T7.5 (PoC udowodnił feasibility)

## Konsekwencje

- **Sprint S7** buduje na `DeckGL` + `_GlobeView` (nie R3F)
- DEM displacement: `TerrainLayer` (Deck.gl) zamiast custom shader — do oceny w T7.1
- Tour cinematic quality oceniana w T7.5, nie w S6
- `frontend/src/poc/DeckGlobePoC.tsx` pozostaje jako referencyjna implementacja do S7
