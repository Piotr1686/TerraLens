import { useMemo } from 'react'
import { TileLayer } from '@deck.gl/geo-layers'
import { BitmapLayer } from '@deck.gl/layers'
import type { Layer } from '@deck.gl/core'

export type HeatmapMetric = 'ssim' | 'ndvi' | 'cva'

// Demo: GIBS MODIS NDVI 8-day composite (prawdziwe dane, brak auth)
// Produkcja: PMTiles z HF CDN per region + metric
const GIBS_NDVI =
  'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/' +
  'MODIS_Terra_NDVI_8Day/default/{date}/250m/{z}/{y}/{x}.png'

const HF_BASE = 'https://huggingface.co/datasets/Piotr1686/terralens-data/resolve/main'

function demoUrl(date: string): string {
  // GIBS NDVI wymaga formatu YYYY-MM-DD (8-day composite — GIBS zwróci najbliższy)
  return GIBS_NDVI.replace('{date}', date)
}

function productionUrl(region: string, metric: HeatmapMetric): string {
  return `${HF_BASE}/${region}_${metric}_heatmap/{z}/{x}/{y}.png`
}

export interface HeatmapLayerConfig {
  region: string | null
  metric: HeatmapMetric
  opacity: number
  currentDate: string
  pmtilesAvailable?: boolean
}

export function useHeatmapLayer({
  region,
  metric,
  opacity,
  currentDate,
  pmtilesAvailable = false,
}: HeatmapLayerConfig): Layer | null {
  return useMemo(() => {
    if (!region || opacity === 0) return null

    const tileUrl = pmtilesAvailable
      ? productionUrl(region, metric)
      : demoUrl(currentDate)

    return new TileLayer({
      id: `heatmap-${metric}`,
      data: tileUrl,
      minZoom: 0,
      maxZoom: 7,
      tileSize: 256,
      extent: [-180, -90, 180, 90],
      opacity,
      renderSubLayers: (props) => {
        const { boundingBox } = props.tile
        return new BitmapLayer(props, {
          data: undefined,
          image: props.data,
          bounds: [boundingBox[0][0], boundingBox[0][1], boundingBox[1][0], boundingBox[1][1]],
        })
      },
    })
  }, [region, metric, opacity, currentDate, pmtilesAvailable])
}
