import { useState, useEffect, useRef, useCallback } from 'react'
import DeckGL from '@deck.gl/react'
import { TileLayer } from '@deck.gl/geo-layers'
import { BitmapLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers'
import { _GlobeView as GlobeView, FlyToInterpolator } from '@deck.gl/core'
import type { MapViewState, PickingInfo } from '@deck.gl/core'

const HF_MANIFEST_URL =
  'https://huggingface.co/datasets/Piotr1686/terralens-data/resolve/main/manifest.json'

const BLUE_MARBLE =
  'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/' +
  'BlueMarble_NextGeneration/default/500m/{z}/{y}/{x}.jpeg'

const GLOBE = new GlobeView({ id: 'globe', nearZMultiplier: 0.1 })
const INITIAL_VIEW: MapViewState = { longitude: 0, latitude: 20, zoom: 1.0 }
const FADE_DURATION_MS = 600

export interface Region {
  id: string
  label: string
  longitude: number
  latitude: number
  zoom: number
}

const REGIONS: Region[] = [
  { id: 'amazonia', label: 'Amazonia', longitude: -60, latitude: -5, zoom: 4 },
  { id: 'dubai', label: 'Dubai', longitude: 55.3, latitude: 25.2, zoom: 5 },
  { id: 'arctic', label: 'Arktyka', longitude: 15, latitude: 72, zoom: 3 },
]

interface Props {
  tileUrl?: string
  onRegionSelect?: (regionId: string) => void
  onManifestLoaded?: (manifest: unknown) => void
}

export function Globe({ tileUrl = BLUE_MARBLE, onRegionSelect, onManifestLoaded }: Props) {
  const [viewState, setViewState] = useState<MapViewState>(INITIAL_VIEW)
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null)
  const [manifestError, setManifestError] = useState(false)

  // Cross-fade state
  const [currentUrl, setCurrentUrl] = useState(tileUrl)
  const [prevUrl, setPrevUrl] = useState<string | null>(null)
  const [fadeOpacity, setFadeOpacity] = useState(1)
  const fadeRafRef = useRef<number | null>(null)
  const fadeStartRef = useRef<number>(0)

  useEffect(() => {
    fetch(HF_MANIFEST_URL)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then((m) => onManifestLoaded?.(m))
      .catch(() => setManifestError(true))
  }, [onManifestLoaded])

  // Cross-fade gdy tileUrl się zmienia
  useEffect(() => {
    if (tileUrl === currentUrl) return
    if (fadeRafRef.current) cancelAnimationFrame(fadeRafRef.current)

    setPrevUrl(currentUrl)
    setCurrentUrl(tileUrl)
    setFadeOpacity(0)
    fadeStartRef.current = performance.now()

    const animate = (now: number) => {
      const progress = Math.min((now - fadeStartRef.current) / FADE_DURATION_MS, 1)
      setFadeOpacity(progress)
      if (progress < 1) fadeRafRef.current = requestAnimationFrame(animate)
      else setPrevUrl(null)
    }
    fadeRafRef.current = requestAnimationFrame(animate)
    return () => { if (fadeRafRef.current) cancelAnimationFrame(fadeRafRef.current) }
  }, [tileUrl]) // eslint-disable-line react-hooks/exhaustive-deps

  const flyToRegion = useCallback(
    (region: Region) => {
      setSelectedRegion(region.id)
      setViewState({
        longitude: region.longitude,
        latitude: region.latitude,
        zoom: region.zoom,
        transitionDuration: 2000,
        transitionInterpolator: new FlyToInterpolator({ speed: 1.5 }),
      })
      onRegionSelect?.(region.id)
    },
    [onRegionSelect],
  )

  const handleReset = useCallback(() => {
    setSelectedRegion(null)
    setViewState({
      ...INITIAL_VIEW,
      transitionDuration: 1500,
      transitionInterpolator: new FlyToInterpolator({ speed: 1.2 }),
    })
  }, [])

  const makeTileLayer = (url: string, id: string, opacity: number) =>
    new TileLayer({
      id,
      data: url,
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

  const markerLayer = new ScatterplotLayer<Region>({
    id: 'region-markers',
    data: REGIONS,
    getPosition: (d) => [d.longitude, d.latitude],
    getRadius: 120000,
    getFillColor: (d) =>
      d.id === selectedRegion ? [255, 200, 50, 230] : [255, 255, 255, 180],
    getLineColor: [30, 30, 30, 200],
    lineWidthMinPixels: 1,
    stroked: true,
    pickable: true,
    onClick: (info: PickingInfo<Region>) => {
      if (info.object) flyToRegion(info.object)
    },
  })

  const labelLayer = new TextLayer<Region>({
    id: 'region-labels',
    data: REGIONS,
    getPosition: (d) => [d.longitude, d.latitude + 3],
    getText: (d) => d.label,
    getSize: 14,
    getColor: [255, 255, 255, 220],
    getTextAnchor: 'middle',
    getAlignmentBaseline: 'bottom',
    fontWeight: 600,
    outlineWidth: 2,
    outlineColor: [0, 0, 0, 180],
    fontSettings: { sdf: true },
  })

  const layers = [
    ...(prevUrl ? [makeTileLayer(prevUrl, 'tile-prev', 1 - fadeOpacity)] : []),
    makeTileLayer(currentUrl, 'tile-current', fadeOpacity),
    markerLayer,
    labelLayer,
  ]

  return (
    <div className="relative h-full w-full bg-black">
      <DeckGL
        views={GLOBE}
        viewState={viewState}
        onViewStateChange={({ viewState: vs }) => setViewState(vs as MapViewState)}
        controller
        layers={layers}
        getCursor={({ isHovering }) => (isHovering ? 'pointer' : 'grab')}
      />

      <div className="absolute bottom-6 left-1/2 flex -translate-x-1/2 gap-2">
        {REGIONS.map((r) => (
          <button
            key={r.id}
            onClick={() => flyToRegion(r)}
            className={`rounded-full px-4 py-2 text-sm font-medium text-white backdrop-blur transition-colors ${
              selectedRegion === r.id
                ? 'bg-amber-500/70 ring-1 ring-amber-300'
                : 'bg-white/10 hover:bg-white/20'
            }`}
          >
            {r.label}
          </button>
        ))}
        {selectedRegion && (
          <button
            onClick={handleReset}
            className="rounded-full px-4 py-2 text-sm font-medium text-white/60 backdrop-blur hover:text-white"
          >
            ← Glob
          </button>
        )}
      </div>

      {manifestError && (
        <div className="absolute right-4 top-4 rounded bg-red-900/60 px-3 py-1 text-xs text-red-200 backdrop-blur">
          manifest niedostępny — tryb demo
        </div>
      )}
    </div>
  )
}
