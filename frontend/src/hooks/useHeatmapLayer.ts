import { useMemo } from 'react'
import { TileLayer } from '@deck.gl/geo-layers'
import { BitmapLayer } from '@deck.gl/layers'
import type { Layer } from '@deck.gl/core'

export type HeatmapMetric = 'ssim' | 'ndvi' | 'cva'

// Demo: różne warstwy GIBS per metryka (prawdziwe dane NASA, brak auth)
// Produkcja: PMTiles z HF CDN per region + metric
const GIBS_BASE = 'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best'

// SSIM — zmiany struktury → True Color (RGB, widoczne zmiany zabudowy i terenu)
const GIBS_SSIM = `${GIBS_BASE}/MODIS_Terra_CorrectedReflectance_TrueColor/default/{date}/250m/{z}/{y}/{x}.jpg`
// NDVI — roślinność → NDVI 8-day (zielono-brązowa paleta, wegetacja)
const GIBS_NDVI = `${GIBS_BASE}/MODIS_Terra_NDVI_8Day/default/{date}/250m/{z}/{y}/{x}.png`
// CVA — zmiana koloru → False Color 7-2-1 (podkreśla pożary, susze, zalania)
const GIBS_CVA  = `${GIBS_BASE}/MODIS_Terra_CorrectedReflectance_Bands721/default/{date}/250m/{z}/{y}/{x}.jpg`

const DEMO_LAYERS: Record<HeatmapMetric, string> = { ssim: GIBS_SSIM, ndvi: GIBS_NDVI, cva: GIBS_CVA }

const HF_BASE = 'https://huggingface.co/datasets/Piotr1686/terralens-data/resolve/main'

function demoUrl(metric: HeatmapMetric, date: string): string {
  return DEMO_LAYERS[metric].replace('{date}', date)
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
      : demoUrl(metric, currentDate)

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
