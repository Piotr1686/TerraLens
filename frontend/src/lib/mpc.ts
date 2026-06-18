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

// STAC paginuje przez link rel=next; MPC zwraca token w `body.token` (POST, merge=true).
interface StacLink {
  rel: string
  body?: { token?: string }
}

interface StacPage {
  features: StacFeature[]
  /** Token następnej strony (undefined = ostatnia strona). */
  nextToken?: string
}

interface ListOptions {
  signal?: AbortSignal
}

/** Listy dostępnych scen per źródło dla danego punktu (posortowane datą desc). */
export type SceneList = Record<Source, SceneResult[]>

// NAIP ma kilka akwizycji (co ~2 lata) → jedna strona wystarcza.
const NAIP_LIMIT = 24

// Podłoga historii S2 (start ~2016 — przed tym akwizycje rzadkie/dziurawe).
const S2_HISTORY_FLOOR = '2016-01-01T00:00:00Z'
// Rozmiar strony przy paginacji S2 oraz bezpiecznik liczby stron (12 × 250 = 3000 scen).
const S2_PAGE_LIMIT = 250
const S2_MAX_PAGES = 12

interface SearchHttpOptions {
  signal?: AbortSignal
  /** Timeout pojedynczej próby (ms). Endpoint MPC potrafi wisieć ~30 s przed 504. */
  timeoutMs?: number
  /** Liczba ponowień przy 504/503/timeout (przejściowe degradacje MPC). */
  retries?: number
}

async function stacSearch(
  body: object,
  { signal, timeoutMs = 12000, retries = 1 }: SearchHttpOptions = {},
): Promise<StacPage> {
  let lastErr: unknown
  for (let attempt = 0; attempt <= retries; attempt++) {
    // Łączymy zewnętrzny abort (nowsze zapytanie) z timeoutem próby.
    const timeout = AbortSignal.timeout(timeoutMs)
    const combined = signal ? AbortSignal.any([signal, timeout]) : timeout
    try {
      const res = await fetch(STAC_SEARCH, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: combined,
      })
      // 504/503 = przejściowa degradacja bramy MPC → traktuj jak błąd do ponowienia.
      if (res.status === 504 || res.status === 503) throw new Error(`STAC ${res.status}`)
      if (!res.ok) throw new Error(`STAC search HTTP ${res.status}`)
      const data = (await res.json()) as { features?: StacFeature[]; links?: StacLink[] }
      const nextToken = data.links?.find((l) => l.rel === 'next')?.body?.token
      return { features: data.features ?? [], nextToken }
    } catch (err) {
      if (signal?.aborted) throw err // anulowanie przez nowsze zapytanie — przerwij
      lastErr = err
    }
  }
  throw lastErr
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

/** Lista akwizycji NAIP nad punktem (datą desc) — jedna strona, kilka scen wystarcza. */
async function listNaip(lon: number, lat: number, http: SearchHttpOptions): Promise<SceneResult[]> {
  const { features } = await stacSearch(
    {
      collections: [SOURCES.naip.collection],
      intersects: { type: 'Point', coordinates: [lon, lat] },
      sortby: [{ field: 'properties.datetime', direction: 'desc' }],
      limit: NAIP_LIMIT,
    },
    http,
  )
  return features.map((f) => buildScene('naip', f, lon, lat))
}

/**
 * Lista scen S2 nad punktem od podłogi {@link S2_HISTORY_FLOOR}, jedna najczystsza na miesiąc.
 * Paginujemy STAC (link rel=next), bucketujemy w locie po YYYY-MM trzymając min cloud_cover —
 * dzięki temu oś czasu sięga ~2016 przy ≤ ~120 scenach (zamiast tysięcy) i bez zachmurzonych przelotów.
 */
async function listSentinelBestPerMonth(
  lon: number,
  lat: number,
  http: SearchHttpOptions,
): Promise<SceneResult[]> {
  const buckets = new Map<string, StacFeature>() // 'YYYY-MM' → najmniej zachmurzona scena
  let token: string | undefined
  for (let page = 0; page < S2_MAX_PAGES; page++) {
    const { features, nextToken } = await stacSearch(
      {
        collections: [SOURCES['sentinel-2'].collection],
        intersects: { type: 'Point', coordinates: [lon, lat] },
        datetime: `${S2_HISTORY_FLOOR}/..`,
        sortby: [{ field: 'properties.datetime', direction: 'desc' }],
        limit: S2_PAGE_LIMIT,
        ...(token ? { token } : {}),
      },
      http,
    )
    for (const f of features) {
      const month = f.properties.datetime.slice(0, 7) // 'YYYY-MM'
      const prev = buckets.get(month)
      const cc = f.properties['eo:cloud_cover'] ?? 100
      const prevCc = prev?.properties['eo:cloud_cover'] ?? 100
      if (!prev || cc < prevCc) buckets.set(month, f)
    }
    if (!nextToken || features.length === 0) break
    token = nextToken
  }
  return [...buckets.values()]
    .map((f) => buildScene('sentinel-2', f, lon, lat))
    .sort((a, b) => b.datetime.localeCompare(a.datetime)) // najnowsze pierwsze (parytet z suwakiem)
}

/**
 * Pobierz listy dostępnych scen dla obu źródeł nad punktem (równolegle).
 * NAIP jest opcjonalny (USA) — jego awaria/pustka nie psuje listy S2.
 * S2 to fallback globalny — jego błąd propagujemy (status error w hooku).
 */
export async function listScenes(lon: number, lat: number, { signal }: ListOptions = {}): Promise<SceneList> {
  const [naip, sentinel] = await Promise.all([
    listNaip(lon, lat, { signal, timeoutMs: 8000, retries: 0 }).catch((err) => {
      if (signal?.aborted) throw err
      console.warn('NAIP niedostępny:', err)
      return [] as SceneResult[]
    }),
    listSentinelBestPerMonth(lon, lat, { signal }),
  ])
  return { naip, 'sentinel-2': sentinel }
}

/** WebMercator (XYZ) tile (x, y) dla punktu — slippy-map wzór (parytet z PoC). */
export function lonLatToTile(lon: number, lat: number, z: number): { x: number; y: number } {
  const n = 2 ** z
  const x = Math.floor(((lon + 180) / 360) * n)
  const latRad = (lat * Math.PI) / 180
  const y = Math.floor(((1 - Math.asinh(Math.tan(latRad)) / Math.PI) / 2) * n)
  return { x, y }
}
