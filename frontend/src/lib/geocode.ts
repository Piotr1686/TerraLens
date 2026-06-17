// Geocoder — OpenStreetMap Nominatim (free, ToS ≤1 req/s, wymaga identyfikacji aplikacji).
// Na demo wystarcza; ewentualny upgrade na managed (Photon/Mapbox) to osobna decyzja.

const NOMINATIM = 'https://nominatim.openstreetmap.org/search'

export interface GeocodeResult {
  label: string
  lon: number
  lat: number
  /** [west, south, east, north] — Nominatim zwraca [south, north, west, east]. */
  bbox?: [number, number, number, number]
}

interface NominatimItem {
  display_name: string
  lon: string
  lat: string
  boundingbox?: [string, string, string, string]
}

/**
 * Zamień zapytanie tekstowe na współrzędne. Zwraca do `limit` trafień (domyślnie 5).
 * Zwraca [] dla pustego zapytania lub braku wyników.
 */
export async function geocode(
  query: string,
  { limit = 5, signal }: { limit?: number; signal?: AbortSignal } = {},
): Promise<GeocodeResult[]> {
  const q = query.trim()
  if (!q) return []

  const url = `${NOMINATIM}?format=jsonv2&limit=${limit}&q=${encodeURIComponent(q)}`
  const res = await fetch(url, { signal })
  if (!res.ok) throw new Error(`Nominatim HTTP ${res.status}`)

  const data = (await res.json()) as NominatimItem[]
  return data.map((it) => {
    const bb = it.boundingbox
    return {
      label: it.display_name,
      lon: Number(it.lon),
      lat: Number(it.lat),
      bbox: bb
        ? [Number(bb[2]), Number(bb[0]), Number(bb[3]), Number(bb[1])]
        : undefined,
    }
  })
}
