// Microsoft Planetary Computer (MPC) — scene-pick Sentinel-2 L2A + builder URL kafla.
// Port logiki z scripts/poc_sentinel2.py do TS. Front woła MPC bezpośrednio:
// STAC/data-API mają CORS ACAO:* i publiczny tiler (decyzja zero-backend, S10).
//
// Tiler MPC podpisuje URL-e assetów po stronie serwera — przeglądarka nie potrzebuje
// SAS tokenów ani pc.sign (inaczej niż PoC w Pythonie używał pc.sign_inplace tylko
// po to, by samodzielnie czytać COG; tu czytaniem zajmuje się hostowany tiler).

const STAC_SEARCH = 'https://planetarycomputer.microsoft.com/api/stac/v1/search'
const DATA_API = 'https://planetarycomputer.microsoft.com/api/data/v1'
const COLLECTION = 'sentinel-2-l2a'

export interface SceneResult {
  /** STAC item id — parametr `item` dla tilera. */
  itemId: string
  /** ISO datetime sceny (properties.datetime). */
  datetime: string
  /** eo:cloud_cover w procentach. */
  cloudCover: number
  /** Footprint sceny [west, south, east, north] — do ograniczenia extent warstwy. */
  bbox: [number, number, number, number]
}

interface PickSceneOptions {
  /** Maks. eo:cloud_cover w % (domyślnie 20, jak PoC). */
  maxCloud?: number
  /** Ile scen pobrać do rankingu (domyślnie 40, jak PoC). */
  maxItems?: number
  /** Abort do anulowania (np. przy zmianie zapytania w hooku). */
  signal?: AbortSignal
}

interface StacFeature {
  id: string
  bbox?: [number, number, number, number] | number[]
  properties: {
    datetime: string
    'eo:cloud_cover'?: number
  }
}

interface StacResponse {
  features: StacFeature[]
}

/**
 * Znajdź najmniej zachmurzoną świeżą scenę S2 nad punktem (lon, lat).
 * Sortuje serwerowo po dacie desc, lokalnie wybiera min cloud_cover (remis → najnowsza).
 * Zwraca null gdy brak scen poniżej progu chmur.
 */
export async function pickScene(
  lon: number,
  lat: number,
  { maxCloud = 20, maxItems = 40, signal }: PickSceneOptions = {},
): Promise<SceneResult | null> {
  const body = {
    collections: [COLLECTION],
    intersects: { type: 'Point', coordinates: [lon, lat] },
    query: { 'eo:cloud_cover': { lt: maxCloud } },
    sortby: [{ field: 'properties.datetime', direction: 'desc' }],
    limit: maxItems,
  }

  const res = await fetch(STAC_SEARCH, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok) {
    throw new Error(`STAC search HTTP ${res.status}`)
  }

  const data = (await res.json()) as StacResponse
  const features = data.features ?? []
  if (features.length === 0) return null

  // min cloud_cover; lista już desc po dacie, więc reduce zachowuje najnowszą przy remisie.
  const best = features.reduce((acc, f) => {
    const c = f.properties['eo:cloud_cover'] ?? 100
    const accC = acc.properties['eo:cloud_cover'] ?? 100
    return c < accC ? f : acc
  })

  // STAC bbox bywa [w,s,e,n] lub 6-elementowy (3D) — bierzemy pierwsze 4 płaskie.
  const b = best.bbox
  const bbox: [number, number, number, number] =
    b && b.length >= 4 ? [b[0], b[1], b[b.length === 6 ? 3 : 2], b[b.length === 6 ? 4 : 3]] : [lon, lat, lon, lat]

  return {
    itemId: best.id,
    datetime: best.properties.datetime,
    cloudCover: best.properties['eo:cloud_cover'] ?? 100,
    bbox,
  }
}

/**
 * Szablon URL kafla WebMercator dla deck.gl TileLayer (placeholdery {z}/{x}/{y}).
 * `assets=visual` = TCI true-color 8-bit (zapinowane w PoC, ostrość 10 m).
 */
export function sentinelTileUrlTemplate(itemId: string): string {
  return (
    `${DATA_API}/item/tiles/WebMercatorQuad/{z}/{x}/{y}@1x.png` +
    `?collection=${COLLECTION}&item=${encodeURIComponent(itemId)}&assets=visual`
  )
}

/** WebMercator (XYZ) tile (x, y) dla punktu — slippy-map wzór (parytet z PoC). */
export function lonLatToTile(lon: number, lat: number, z: number): { x: number; y: number } {
  const n = 2 ** z
  const x = Math.floor(((lon + 180) / 360) * n)
  const latRad = (lat * Math.PI) / 180
  const y = Math.floor(((1 - Math.asinh(Math.tan(latRad)) / Math.PI) / 2) * n)
  return { x, y }
}
