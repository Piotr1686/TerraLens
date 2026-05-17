import { useEffect, useMemo, useState } from 'react'
import { BitmapLayer } from '@deck.gl/layers'
import { COORDINATE_SYSTEM } from '@deck.gl/core'
import type { Layer } from '@deck.gl/core'
import { PMTiles } from 'pmtiles'

const archiveCache = new Map<string, PMTiles>()
function getArchive(url: string): PMTiles {
  if (!archiveCache.has(url)) archiveCache.set(url, new PMTiles(url))
  return archiveCache.get(url)!
}

// HuggingFace /resolve/ URL zwraca 302 → CDN. Range headers gubione po redirect.
const redirectCache = new Map<string, string>()
async function resolveRedirect(url: string): Promise<string> {
  if (redirectCache.has(url)) return redirectCache.get(url)!
  try {
    const r = await fetch(url, { method: 'HEAD', redirect: 'follow' })
    redirectCache.set(url, r.url)
    return r.url
  } catch {
    return url
  }
}

// GIBS EPSG:4326 TileMatrixSet — wymiary macierzy per poziom zoomu.
const GIBS_MATRIX: Record<number, { w: number; h: number }> = {
  6: { w: 80, h: 40 },
  7: { w: 160, h: 80 },
  8: { w: 320, h: 160 },
}

// Mapowanie viewport zoom (deck.gl GlobeView) → poziom zoomu GIBS do załadowania.
export function pickGibsZoom(viewportZoom: number): number {
  if (viewportZoom >= 7.5) return 8
  if (viewportZoom >= 5.5) return 7
  return 6
}

interface TileImage {
  x: number
  y: number
  z: number
  bounds: [number, number, number, number]
  image: ImageBitmap
}

interface Config {
  region: string | null
  pmtilesUrl: string | null
  opacity: number
  bbox?: [number, number, number, number]
  viewportZoom?: number
}

export function usePMTilesLayer({ region, pmtilesUrl, opacity, bbox, viewportZoom }: Config): Layer[] {
  const [resolvedUrl, setResolvedUrl] = useState<string | null>(null)
  const [tiles, setTiles] = useState<TileImage[]>([])

  const gibsZoom = useMemo(() => pickGibsZoom(viewportZoom ?? 4), [viewportZoom])

  useEffect(() => {
    if (!pmtilesUrl) { setResolvedUrl(null); return }
    resolveRedirect(pmtilesUrl).then(setResolvedUrl)
  }, [pmtilesUrl])

  // Czyść tile'y przy zmianie regionu lub źródła — nie przy zmianie gibsZoom (fallback).
  useEffect(() => {
    setTiles([])
  }, [resolvedUrl, region])

  useEffect(() => {
    if (!resolvedUrl || !region || !bbox) return
    let cancelled = false

    const archive = getArchive(resolvedUrl)
    const [lngMin, latMin, lngMax, latMax] = bbox
    const { w: mw, h: mh } = GIBS_MATRIX[gibsZoom] ?? GIBS_MATRIX[6]

    const xMin = Math.max(0, Math.floor((lngMin + 180) / 360 * mw))
    const xMax = Math.min(mw - 1, Math.floor((lngMax + 180) / 360 * mw))
    const yMin = Math.max(0, Math.floor((90 - latMax) / 180 * mh))
    const yMax = Math.min(mh - 1, Math.floor((90 - latMin) / 180 * mh))

    const loadTile = async (x: number, y: number): Promise<TileImage | null> => {
      try {
        const result = await archive.getZxy(gibsZoom, x, y)
        if (!result?.data) return null
        const image = await createImageBitmap(new Blob([result.data], { type: 'image/webp' }))
        const tLngMin = x / mw * 360 - 180
        const tLngMax = (x + 1) / mw * 360 - 180
        const tLatMax = 90 - y / mh * 180
        const tLatMin = 90 - (y + 1) / mh * 180
        return { x, y, z: gibsZoom, image, bounds: [tLngMin, tLatMin, tLngMax, tLatMax] }
      } catch {
        return null
      }
    }

    const promises: Promise<TileImage | null>[] = []
    for (let x = xMin; x <= xMax; x++) {
      for (let y = yMin; y <= yMax; y++) {
        promises.push(loadTile(x, y))
      }
    }

    Promise.all(promises).then((results) => {
      if (cancelled) return
      const fetched = results.filter((t): t is TileImage => t !== null)
      // Gdy archiwum nie ma danego poziomu zoomu — zachowaj poprzednie tile'y (fallback).
      if (fetched.length > 0) setTiles(fetched)
    })

    return () => { cancelled = true }
  }, [resolvedUrl, region, bbox, gibsZoom])

  return useMemo(() => {
    if (!region || tiles.length === 0 || opacity === 0) return []
    return tiles.map((t) => new BitmapLayer({
      id: `pmtiles-${region}-z${t.z}-${t.x}-${t.y}`,
      image: t.image,
      bounds: t.bounds,
      opacity,
      _imageCoordinateSystem: COORDINATE_SYSTEM.LNGLAT,
    }))
  }, [region, tiles, opacity])
}
