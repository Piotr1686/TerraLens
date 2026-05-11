import { useMemo } from 'react'
import { TileLayer } from '@deck.gl/geo-layers'
import { BitmapLayer } from '@deck.gl/layers'
import { COORDINATE_SYSTEM } from '@deck.gl/core'
import type { Layer } from '@deck.gl/core'

export type HeatmapMetric = 'ssim' | 'ndvi' | 'cva'

// Demo: różne warstwy GIBS per metryka (prawdziwe dane NASA, brak auth)
// Produkcja: PMTiles z HF CDN per region + metric
// epsg3857 (GoogleMapsCompatible) — tile scheme zgodny z deck.gl TileLayer (Web Mercator OSM)
// epsg4326 ma niekompatybilne tile dimensions (20×10 przy z=4) → mismatched → zły kontynent
const GIBS_BASE = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best'

// SSIM — zmiany struktury → temperatura powierzchni (gradient niebieski→czerwony)
const GIBS_SSIM = `${GIBS_BASE}/MODIS_Terra_Land_Surface_Temp_Day/default/{date}/GoogleMapsCompatible_Level7/{z}/{y}/{x}.png`
// NDVI — roślinność → NDVI 8-day (gradient brązowy→zielony, wegetacja)
const GIBS_NDVI = `${GIBS_BASE}/MODIS_Terra_NDVI_8Day/default/{date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.png`
// CVA — zmiana koloru → False Color 7-2-1 (czerwony=sucha roślinność, niebiesko=woda)
const GIBS_CVA  = `${GIBS_BASE}/MODIS_Terra_CorrectedReflectance_Bands721/default/{date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`

const DEMO_LAYERS: Record<HeatmapMetric, string> = { ssim: GIBS_SSIM, ndvi: GIBS_NDVI, cva: GIBS_CVA }

// NDVI_8Day dostępny w GIBS tylko od 2025-02-12.
// Lipiec 2025: sucha pora dla Dubaju + dobre pokrycie LST dla Amazonii.
// Arctic LST w lipcu ma pełne nasłonecznienie (brak polar night).
const DEMO_DATE = '2025-07-01'

const HF_BASE = 'https://huggingface.co/datasets/Piotr1686/terralens-data/resolve/main'

function demoUrl(metric: HeatmapMetric): string {
  return DEMO_LAYERS[metric].replace('{date}', DEMO_DATE)
}

function productionUrl(region: string, metric: HeatmapMetric): string {
  return `${HF_BASE}/${region}_${metric}_heatmap/{z}/{x}/{y}.png`
}

export interface HeatmapLayerConfig {
  region: string | null
  metric: HeatmapMetric
  opacity: number
  bbox?: [number, number, number, number]
  pmtilesAvailable?: boolean
}

export function useHeatmapLayer({
  region,
  metric,
  opacity,
  bbox,
  pmtilesAvailable = false,
}: HeatmapLayerConfig): Layer | null {
  return useMemo(() => {
    if (!region || opacity === 0) return null

    const tileUrl = pmtilesAvailable
      ? productionUrl(region, metric)
      : demoUrl(metric)

    return new TileLayer({
      id: `heatmap-${metric}`,
      data: tileUrl,
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
    })
  }, [region, metric, opacity, bbox, pmtilesAvailable])
}
