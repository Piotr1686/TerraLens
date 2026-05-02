import { useCallback, useEffect, useRef, useState } from 'react'
import DeckGL from '@deck.gl/react'
import { TileLayer } from '@deck.gl/geo-layers'
import { BitmapLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers'
import { _GlobeView as GlobeView } from '@deck.gl/core'
import type { MapViewState, PickingInfo, Layer } from '@deck.gl/core'
import { useCinematicFlight } from '@/hooks/useCinematicFlight'

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
  { id: 'arctic', label: 'Arctic', longitude: 15, latitude: 72, zoom: 3 },
]

interface Props {
  tileUrl?: string
  extraLayers?: Layer[]
  flyTarget?: string | null   // string → leć do regionu, null → reset do widoku globalnego
  onRegionSelect?: (regionId: string | null) => void
  onRegionArrival?: (regionId: string) => void  // wywoływane po wylądowaniu kamery
  fps?: number                                  // target FPS animacji, 30 na mobile
}

export function Globe({ tileUrl = BLUE_MARBLE, extraLayers = [], flyTarget, onRegionSelect, onRegionArrival, fps = 60 }: Props) {
  const [viewState, setViewState] = useState<MapViewState>(INITIAL_VIEW)
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null)

  const { fly: cinematicFly, cancel: cancelFlight, setPosition: setFlightPos } = useCinematicFlight()

  // flyToRegion i handleReset zadeklarowane PRZED useEffect(flyTarget) który ich używa
  const flyToRegion = useCallback(
    (region: Region) => {
      setSelectedRegion(region.id)
      cinematicFly(
        { longitude: region.longitude, latitude: region.latitude, zoom: region.zoom },
        { duration: 2200, fps },
        setViewState,
        () => onRegionArrival?.(region.id),
      )
      onRegionSelect?.(region.id)
    },
    [onRegionSelect, onRegionArrival, cinematicFly, fps],
  )

  const handleReset = useCallback(() => {
    setSelectedRegion(null)
    cinematicFly(INITIAL_VIEW, { duration: 1800, zoomDip: 0.8, fps }, setViewState)
  }, [cinematicFly, fps])

  // Zewnętrzne sterowanie lotem (tour)
  useEffect(() => {
    if (flyTarget === undefined) return
    if (flyTarget === null) {
      handleReset()
      onRegionSelect?.(null)
      return
    }
    const region = REGIONS.find((r) => r.id === flyTarget)
    if (region) flyToRegion(region)
  }, [flyTarget]) // eslint-disable-line react-hooks/exhaustive-deps

  // Cross-fade state
  const [currentUrl, setCurrentUrl] = useState(tileUrl)
  const [prevUrl, setPrevUrl] = useState<string | null>(null)
  const [fadeOpacity, setFadeOpacity] = useState(1)
  const fadeRafRef = useRef<number | null>(null)
  const fadeStartRef = useRef<number>(0)

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
    parameters: { depthCompare: 'always' as const },
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
    parameters: { depthCompare: 'always' as const },
  })

  const layers = [
    ...(prevUrl ? [makeTileLayer(prevUrl, 'tile-prev', 1 - fadeOpacity)] : []),
    makeTileLayer(currentUrl, 'tile-current', fadeOpacity),
    ...extraLayers,
    markerLayer,
    labelLayer,
  ]

  return (
    <div className="relative h-full w-full bg-black">
      <DeckGL
        views={GLOBE}
        viewState={viewState}
        onViewStateChange={({ viewState: vs, interactionState }) => {
          const s = interactionState as { isDragging?: boolean; isZooming?: boolean; isPanning?: boolean; isRotating?: boolean }
          if (s.isDragging || s.isZooming || s.isPanning || s.isRotating) cancelFlight()
          setFlightPos(vs as MapViewState)
          setViewState(vs as MapViewState)
        }}
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
            ← Globe
          </button>
        )}
      </div>

    </div>
  )
}
