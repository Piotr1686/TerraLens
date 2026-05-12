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

// GIBS EPSG:4326 250m TileMatrixSet — pipeline fetchuje tylko zoom 6.
const GIBS_ZOOM = 6
const GIBS_MW = 80
const GIBS_MH = 40

interface TileImage {
  x: number
  y: number
  bounds: [number, number, number, number]
  image: ImageBitmap
}

interface Config {
  region: string | null
  pmtilesUrl: string | null
  opacity: number
  bbox?: [number, number, number, number]
}

export function usePMTilesLayer({ region, pmtilesUrl, opacity, bbox }: Config): Layer[] {
  const [resolvedUrl, setResolvedUrl] = useState<string | null>(null)
  const [tiles, setTiles] = useState<TileImage[]>([])

  useEffect(() => {
    if (!pmtilesUrl) { setResolvedUrl(null); return }
    resolveRedirect(pmtilesUrl).then(setResolvedUrl)
  }, [pmtilesUrl])

  useEffect(() => {
    setTiles([])
    if (!resolvedUrl || !region || !bbox) return
    let cancelled = false
    const archive = getArchive(resolvedUrl)
    const [lngMin, latMin, lngMax, latMax] = bbox
    const xMin = Math.max(0, Math.floor((lngMin + 180) / 360 * GIBS_MW))
    const xMax = Math.min(GIBS_MW - 1, Math.floor((lngMax + 180) / 360 * GIBS_MW))
    const yMin = Math.max(0, Math.floor((90 - latMax) / 180 * GIBS_MH))
    const yMax = Math.min(GIBS_MH - 1, Math.floor((90 - latMin) / 180 * GIBS_MH))

    const loadTile = async (x: number, y: number): Promise<TileImage | null> => {
      try {
        const result = await archive.getZxy(GIBS_ZOOM, x, y)
        if (!result?.data) return null
        const image = await createImageBitmap(new Blob([result.data], { type: 'image/webp' }))
        const tLngMin = x / GIBS_MW * 360 - 180
        const tLngMax = (x + 1) / GIBS_MW * 360 - 180
        const tLatMax = 90 - y / GIBS_MH * 180
        const tLatMin = 90 - (y + 1) / GIBS_MH * 180
        return { x, y, image, bounds: [tLngMin, tLatMin, tLngMax, tLatMax] }
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
      setTiles(results.filter((t): t is TileImage => t !== null))
    })

    return () => { cancelled = true }
  }, [resolvedUrl, region, bbox])

  return useMemo(() => {
    if (!region || tiles.length === 0 || opacity === 0) return []
    return tiles.map((t) => new BitmapLayer({
      id: `pmtiles-${region}-${t.x}-${t.y}`,
      image: t.image,
      bounds: t.bounds,
      opacity,
      _imageCoordinateSystem: COORDINATE_SYSTEM.LNGLAT,
    }))
  }, [region, tiles, opacity])
}
