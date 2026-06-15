import { useEffect, useMemo, useState } from 'react'
import { BitmapLayer } from '@deck.gl/layers'
import { COORDINATE_SYSTEM } from '@deck.gl/core'
import type { Layer } from '@deck.gl/core'

export type HeatmapMetric = 'ssim' | 'ndvi' | 'cva'

// --- Realne heatmapy: PNG per tile w siatce GIBS EPSG:4326 ---
// Indeksy 4326 NIE są kompatybilne z deck.gl TileLayer (Web Mercator) — dlatego, jak
// usePMTilesLayer, iterujemy ręcznie (x,y) z bbox regionu i renderujemy multi-BitmapLayer
// w natywnych bounds. Patrz MEMORY [2026-05-12] PMTiles overlay i [2026-06-04] heatmapy SSIM.
const HF_BASE = 'https://huggingface.co/datasets/Piotr1686/terralens-data/resolve/main'
// Override przez VITE_HEATMAP_BASE (dev/staging); domyślnie HF CDN.
const HEATMAP_BASE = import.meta.env.VITE_HEATMAP_BASE ?? HF_BASE
// GIBS EPSG:4326 TileMatrixSet — wymiary macierzy per poziom zoomu.
const GIBS_MATRIX: Record<number, { w: number; h: number }> = {
  6: { w: 80, h: 40 },
  7: { w: 160, h: 80 },
  8: { w: 320, h: 160 },
}

// Wszystkie metryki mają realne mapy w pipeline → zoom siatki GIBS + sufiks repo HF.
// SSIM i CVA (HLS_RGB) renderowane z=7; NDVI (MODIS_NDVI) z=6.
const REAL_METRICS: Record<HeatmapMetric, { zoom: number; suffix: string }> = {
  ssim: { zoom: 7, suffix: 'ssim_heatmap' },
  cva: { zoom: 7, suffix: 'cva_heatmap' },
  ndvi: { zoom: 6, suffix: 'ndvi_heatmap' },
}

function realTileUrl(region: string, suffix: string, z: number, x: number, y: number): string {
  return `${HEATMAP_BASE}/${region}_${suffix}/${z}/${x}/${y}.png`
}

interface TileImage {
  key: string
  bounds: [number, number, number, number]
  image: ImageBitmap
}

export interface HeatmapLayerConfig {
  region: string | null
  metric: HeatmapMetric
  opacity: number
  bbox?: [number, number, number, number]
}

export function useHeatmapLayer({ region, metric, opacity, bbox }: HeatmapLayerConfig): Layer[] {
  const [realTiles, setRealTiles] = useState<TileImage[]>([])
  const realCfg = REAL_METRICS[metric]

  // Realne metryki (SSIM/CVA/NDVI): pobierz PNG tile'e w indeksach GIBS 4326 wyliczonych z bbox.
  useEffect(() => {
    if (!realCfg || !region || !bbox) {
      setRealTiles([])
      return
    }
    let cancelled = false

    const { zoom, suffix } = realCfg
    const [lngMin, latMin, lngMax, latMax] = bbox
    const { w: mw, h: mh } = GIBS_MATRIX[zoom]
    const xMin = Math.max(0, Math.floor(((lngMin + 180) / 360) * mw))
    const xMax = Math.min(mw - 1, Math.floor(((lngMax + 180) / 360) * mw))
    const yMin = Math.max(0, Math.floor(((90 - latMax) / 180) * mh))
    const yMax = Math.min(mh - 1, Math.floor(((90 - latMin) / 180) * mh))

    const loadTile = async (x: number, y: number): Promise<TileImage | null> => {
      try {
        const r = await fetch(realTileUrl(region, suffix, zoom, x, y))
        if (!r.ok) return null
        const image = await createImageBitmap(await r.blob())
        const tLngMin = (x / mw) * 360 - 180
        const tLngMax = ((x + 1) / mw) * 360 - 180
        const tLatMax = 90 - (y / mh) * 180
        const tLatMin = 90 - ((y + 1) / mh) * 180
        return { key: `${zoom}-${x}-${y}`, image, bounds: [tLngMin, tLatMin, tLngMax, tLatMax] }
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
      setRealTiles(results.filter((t): t is TileImage => t !== null))
    })

    return () => {
      cancelled = true
    }
  }, [metric, region, bbox]) // eslint-disable-line react-hooks/exhaustive-deps

  return useMemo(() => {
    if (!region || opacity === 0) return []

    // Wszystkie metryki → realne BitmapLayer w natywnych bounds 4326 (jak usePMTilesLayer).
    return realTiles.map(
      (t) =>
        new BitmapLayer({
          id: `heatmap-${metric}-${region}-${t.key}`,
          image: t.image,
          bounds: t.bounds,
          opacity,
          _imageCoordinateSystem: COORDINATE_SYSTEM.LNGLAT,
        }),
    )
  }, [region, metric, opacity, realTiles])
}
