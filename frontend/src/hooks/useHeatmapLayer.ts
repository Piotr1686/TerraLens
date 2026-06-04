import { useEffect, useMemo, useState } from 'react'
import { TileLayer } from '@deck.gl/geo-layers'
import { BitmapLayer } from '@deck.gl/layers'
import { COORDINATE_SYSTEM } from '@deck.gl/core'
import type { Layer } from '@deck.gl/core'

export type HeatmapMetric = 'ssim' | 'ndvi' | 'cva'

// --- Demo GIBS fallback (NDVI/CVA — brak realnych danych z pipeline) ---
// epsg3857 (GoogleMapsCompatible) — tile scheme zgodny z deck.gl TileLayer (Web Mercator OSM).
const GIBS_BASE = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best'
// NDVI — roślinność → NDVI 8-day (gradient brązowy→zielony)
const GIBS_NDVI = `${GIBS_BASE}/MODIS_Terra_NDVI_8Day/default/{date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.png`
// CVA — zmiana koloru → False Color 7-2-1 (czerwony=sucha roślinność, niebiesko=woda)
const GIBS_CVA = `${GIBS_BASE}/MODIS_Terra_CorrectedReflectance_Bands721/default/{date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`
const DEMO_LAYERS: Record<'ndvi' | 'cva', string> = { ndvi: GIBS_NDVI, cva: GIBS_CVA }
// NDVI_8Day dostępny w GIBS dopiero od 2025-02-12; lipiec = dobre pokrycie wszystkich warstw.
const DEMO_DATE = '2025-07-01'

// --- Realne heatmapy SSIM: PNG per tile w siatce GIBS EPSG:4326 (z=7) ---
// Indeksy 4326 NIE są kompatybilne z deck.gl TileLayer (Web Mercator) — dlatego, jak
// usePMTilesLayer, iterujemy ręcznie (x,y) z bbox regionu i renderujemy multi-BitmapLayer
// w natywnych bounds 4.5°×4.5°. Patrz MEMORY [2026-05-12] PMTiles overlay coordinate bridge.
const HF_BASE = 'https://huggingface.co/datasets/Piotr1686/terralens-data/resolve/main'
// Override przez VITE_HEATMAP_BASE (dev/staging); domyślnie HF CDN.
const HEATMAP_BASE = import.meta.env.VITE_HEATMAP_BASE ?? HF_BASE
const SSIM_ZOOM = 7
// GIBS EPSG:4326 TileMatrixSet — wymiary macierzy per poziom zoomu.
const GIBS_MATRIX: Record<number, { w: number; h: number }> = {
  6: { w: 80, h: 40 },
  7: { w: 160, h: 80 },
  8: { w: 320, h: 160 },
}

function ssimTileUrl(region: string, z: number, x: number, y: number): string {
  return `${HEATMAP_BASE}/${region}_ssim_heatmap/${z}/${x}/${y}.png`
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
  const [ssimTiles, setSsimTiles] = useState<TileImage[]>([])
  const isSsim = metric === 'ssim'

  // Realne SSIM: pobierz PNG tile'e w indeksach GIBS 4326 wyliczonych z bbox regionu.
  useEffect(() => {
    if (!isSsim || !region || !bbox) {
      setSsimTiles([])
      return
    }
    let cancelled = false

    const [lngMin, latMin, lngMax, latMax] = bbox
    const { w: mw, h: mh } = GIBS_MATRIX[SSIM_ZOOM]
    const xMin = Math.max(0, Math.floor(((lngMin + 180) / 360) * mw))
    const xMax = Math.min(mw - 1, Math.floor(((lngMax + 180) / 360) * mw))
    const yMin = Math.max(0, Math.floor(((90 - latMax) / 180) * mh))
    const yMax = Math.min(mh - 1, Math.floor(((90 - latMin) / 180) * mh))

    const loadTile = async (x: number, y: number): Promise<TileImage | null> => {
      try {
        const r = await fetch(ssimTileUrl(region, SSIM_ZOOM, x, y))
        if (!r.ok) return null
        const image = await createImageBitmap(await r.blob())
        const tLngMin = (x / mw) * 360 - 180
        const tLngMax = ((x + 1) / mw) * 360 - 180
        const tLatMax = 90 - (y / mh) * 180
        const tLatMin = 90 - ((y + 1) / mh) * 180
        return { key: `${SSIM_ZOOM}-${x}-${y}`, image, bounds: [tLngMin, tLatMin, tLngMax, tLatMax] }
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
      setSsimTiles(results.filter((t): t is TileImage => t !== null))
    })

    return () => {
      cancelled = true
    }
  }, [isSsim, region, bbox])

  return useMemo(() => {
    if (!region || opacity === 0) return []

    // SSIM → realne BitmapLayer w natywnych bounds 4326 (jak usePMTilesLayer).
    if (metric === 'ssim') {
      return ssimTiles.map(
        (t) =>
          new BitmapLayer({
            id: `heatmap-ssim-${region}-${t.key}`,
            image: t.image,
            bounds: t.bounds,
            opacity,
            _imageCoordinateSystem: COORDINATE_SYSTEM.LNGLAT,
          }),
      )
    }

    // NDVI/CVA → demo GIBS (brak realnych danych w pipeline); TileLayer = Web Mercator scheme.
    const url = DEMO_LAYERS[metric].replace('{date}', DEMO_DATE)
    return [
      new TileLayer({
        id: `heatmap-${metric}`,
        data: url,
        minZoom: 1,
        maxZoom: 9,
        tileSize: 256,
        extent: bbox ?? [-180, -90, 180, 90],
        opacity,
        renderSubLayers: (props) => {
          const { boundingBox } = props.tile
          return new BitmapLayer(props, {
            data: undefined,
            image: props.data,
            bounds: [boundingBox[0][0], boundingBox[0][1], boundingBox[1][0], boundingBox[1][1]],
            _imageCoordinateSystem: COORDINATE_SYSTEM.LNGLAT,
          })
        },
      }),
    ]
  }, [region, metric, opacity, bbox, ssimTiles])
}
