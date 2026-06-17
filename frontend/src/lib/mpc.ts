// Microsoft Planetary Computer (MPC) — resolver najlepszego realnego źródła + builder URL kafla.
// Kaskada: NAIP (0.6 m, tylko USA) → fallback Sentinel-2 L2A (10 m, globalnie).
// Front woła MPC bezpośrednio: STAC + hostowany tiler mają CORS ACAO:* (zero-backend, S10).
//
// Tiler MPC podpisuje URL-e assetów po stronie serwera — przeglądarka nie potrzebuje SAS tokenów.

const STAC_SEARCH = 'https://planetarycomputer.microsoft.com/api/stac/v1/search'
const DATA_API = 'https://planetarycomputer.microsoft.com/api/data/v1'

export type Source = 'naip' | 'sentinel-2'

interface SourceConfig {
  collection: string
  /** Natywny sufit zoomu kafli (NAIP 0.6 m ≈ z18, S2 10 m ≈ z14). */
  maxZoom: number
  /** Etykieta atrybucji w UI. */
  label: string
  /** Czy źródło ma eo:cloud_cover (S2 tak, NAIP nie). */
  hasCloud: boolean
  /** Parametry query tilera po `{z}/{x}/{y}@2x.png?`. */
  tileQuery: (itemId: string) => string
}

const SOURCES: Record<Source, SourceConfig> = {
  naip: {
    collection: 'naip',
    maxZoom: 18,
    label: 'NAIP 0.6 m · USDA / Microsoft Planetary Computer',
    hasCloud: false,
    // NAIP to 4-band RGBN — wybieramy pasma 1,2,3 jako RGB.
    tileQuery: (id) => `collection=naip&item=${encodeURIComponent(id)}&assets=image&asset_bidx=image|1,2,3`,
  },
  'sentinel-2': {
    collection: 'sentinel-2-l2a',
    maxZoom: 14,
    label: 'Sentinel-2 L2A 10 m · Microsoft Planetary Computer',
    hasCloud: true,
    // assets=visual = TCI true-color 8-bit (zapinowane w PoC).
    tileQuery: (id) => `collection=sentinel-2-l2a&item=${encodeURIComponent(id)}&assets=visual`,
  },
}

export interface SceneResult {
  source: Source
  /** STAC item id — parametr `item` dla tilera. */
  itemId: string
  /** ISO datetime sceny. */
  datetime: string
  /** eo:cloud_cover w % (null dla NAIP). */
  cloudCover: number | null
  /** Footprint sceny [west, south, east, north] — do ograniczenia extent warstwy. */
  bbox: [number, number, number, number]
  /** Natywny sufit zoomu kafli dla tego źródła. */
  maxZoom: number
  /** Pełny szablon URL kafla dla deck.gl TileLayer ({z}/{x}/{y} placeholdery, `@2x` retina). */
  tileUrl: string
  /** Etykieta atrybucji. */
  label: string
}

interface StacFeature {
  id: string
  bbox?: number[]
  properties: {
    datetime: string
    'eo:cloud_cover'?: number
  }
}

interface SearchOptions {
  /** Maks. eo:cloud_cover w % (tylko S2, domyślnie 20). */
  maxCloud?: number
  maxItems?: number
  signal?: AbortSignal
}

async function stacSearch(body: object, signal?: AbortSignal): Promise<StacFeature[]> {
  const res = await fetch(STAC_SEARCH, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok) throw new Error(`STAC search HTTP ${res.status}`)
  const data = (await res.json()) as { features?: StacFeature[] }
  return data.features ?? []
}

// STAC bbox bywa 4- lub 6-elementowy (3D) — bierzemy płaskie [w,s,e,n].
function parseBbox(
  b: number[] | undefined,
  fallbackLon: number,
  fallbackLat: number,
): [number, number, number, number] {
  if (b && b.length >= 4) {
    const eastIdx = b.length === 6 ? 3 : 2
    const northIdx = b.length === 6 ? 4 : 3
    return [b[0], b[1], b[eastIdx], b[northIdx]]
  }
  return [fallbackLon, fallbackLat, fallbackLon, fallbackLat]
}

function buildScene(source: Source, f: StacFeature, lon: number, lat: number): SceneResult {
  const cfg = SOURCES[source]
  return {
    source,
    itemId: f.id,
    datetime: f.properties.datetime,
    cloudCover: cfg.hasCloud ? (f.properties['eo:cloud_cover'] ?? 100) : null,
    bbox: parseBbox(f.bbox, lon, lat),
    maxZoom: cfg.maxZoom,
    tileUrl: `${DATA_API}/item/tiles/WebMercatorQuad/{z}/{x}/{y}@2x.png?${cfg.tileQuery(f.id)}`,
    label: cfg.label,
  }
}

/** NAIP nad punktem — najnowsza scena (brak chmur w tym produkcie). null poza USA. */
async function pickNaip(lon: number, lat: number, signal?: AbortSignal): Promise<SceneResult | null> {
  const features = await stacSearch(
    {
      collections: ['naip'],
      intersects: { type: 'Point', coordinates: [lon, lat] },
      sortby: [{ field: 'properties.datetime', direction: 'desc' }],
      limit: 1,
    },
    signal,
  )
  return features.length ? buildScene('naip', features[0], lon, lat) : null
}

/** Sentinel-2 nad punktem — najmniej zachmurzona świeża scena (remis → najnowsza). */
async function pickSentinel(
  lon: number,
  lat: number,
  { maxCloud = 20, maxItems = 40, signal }: SearchOptions = {},
): Promise<SceneResult | null> {
  const features = await stacSearch(
    {
      collections: ['sentinel-2-l2a'],
      intersects: { type: 'Point', coordinates: [lon, lat] },
      query: { 'eo:cloud_cover': { lt: maxCloud } },
      sortby: [{ field: 'properties.datetime', direction: 'desc' }],
      limit: maxItems,
    },
    signal,
  )
  if (!features.length) return null
  // min cloud_cover; lista desc po dacie → reduce zachowuje najnowszą przy remisie.
  const best = features.reduce((acc, f) =>
    (f.properties['eo:cloud_cover'] ?? 100) < (acc.properties['eo:cloud_cover'] ?? 100) ? f : acc,
  )
  return buildScene('sentinel-2', best, lon, lat)
}

/**
 * Wybierz najlepsze realne źródło nad punktem: NAIP (0.6 m, USA) jeśli dostępne,
 * inaczej Sentinel-2 (10 m, globalnie). Zwraca null gdy brak czystej sceny S2.
 */
export async function resolveScene(
  lon: number,
  lat: number,
  opts: SearchOptions = {},
): Promise<SceneResult | null> {
  const naip = await pickNaip(lon, lat, opts.signal)
  if (naip) return naip
  return pickSentinel(lon, lat, opts)
}

/** WebMercator (XYZ) tile (x, y) dla punktu — slippy-map wzór (parytet z PoC). */
export function lonLatToTile(lon: number, lat: number, z: number): { x: number; y: number } {
  const n = 2 ** z
  const x = Math.floor(((lon + 180) / 360) * n)
  const latRad = (lat * Math.PI) / 180
  const y = Math.floor(((1 - Math.asinh(Math.tan(latRad)) / Math.PI) / 2) * n)
  return { x, y }
}
