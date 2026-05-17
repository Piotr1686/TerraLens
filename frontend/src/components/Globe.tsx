import { useCallback, useEffect, useRef, useState } from 'react'
import DeckGL from '@deck.gl/react'
import { TileLayer } from '@deck.gl/geo-layers'
import { BitmapLayer } from '@deck.gl/layers'
import { _GlobeView as GlobeView, COORDINATE_SYSTEM } from '@deck.gl/core'
import type { MapViewState, Layer } from '@deck.gl/core'
import { useCinematicFlight } from '@/hooks/useCinematicFlight'
import { REGIONS } from '@/data/regions'
import type { Region } from '@/data/regions'

// epsg3857 (GoogleMapsCompatible) — tile scheme zgodny z deck.gl TileLayer (Web Mercator OSM)
const BLUE_MARBLE =
  'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/' +
  'BlueMarble_NextGeneration/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg'

const GLOBE = new GlobeView({ id: 'globe', nearZMultiplier: 0.1 })
const INITIAL_VIEW: MapViewState = { longitude: 0, latitude: 20, zoom: 1.0 }
const FADE_DURATION_MS = 600

interface Props {
  tileUrl?: string
  extraLayers?: Layer[]
  flyTarget?: string | null
  onRegionSelect?: (regionId: string | null) => void
  onRegionArrival?: (regionId: string) => void
  onViewZoomChange?: (zoom: number) => void
  fps?: number
}

export function Globe({ tileUrl = BLUE_MARBLE, extraLayers = [], flyTarget, onRegionSelect, onRegionArrival, onViewZoomChange, fps = 60 }: Props) {
  const [viewState, setViewState] = useState<MapViewState>(INITIAL_VIEW)
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null)
  const lastReportedZoom = useRef(INITIAL_VIEW.zoom)

  const { fly: cinematicFly, cancel: cancelFlight, setPosition: setFlightPos } = useCinematicFlight()

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

  useEffect(() => {
    if (flyTarget === undefined) return
    if (flyTarget === null) { handleReset(); onRegionSelect?.(null); return }
    const region = REGIONS.find((r) => r.id === flyTarget)
    if (region) flyToRegion(region)
  }, [flyTarget]) // eslint-disable-line react-hooks/exhaustive-deps

  // Cross-fade state
  const [currentUrl, setCurrentUrl] = useState(tileUrl)
  const [prevUrl, setPrevUrl] = useState<string | null>(null)
  const [fadeOpacity, setFadeOpacity] = useState(1)
  const fadeRafRef = useRef<number | null>(null)
  const fadeStartRef = useRef<number>(0)

  useEffect(() => {
    if (tileUrl === currentUrl) return
    if (fadeRafRef.current) cancelAnimationFrame(fadeRafRef.current)
    setPrevUrl(currentUrl); setCurrentUrl(tileUrl); setFadeOpacity(0)
    fadeStartRef.current = performance.now()
    const animate = (now: number) => {
      const p = Math.min((now - fadeStartRef.current) / FADE_DURATION_MS, 1)
      setFadeOpacity(p)
      if (p < 1) fadeRafRef.current = requestAnimationFrame(animate)
      else setPrevUrl(null)
    }
    fadeRafRef.current = requestAnimationFrame(animate)
    return () => { if (fadeRafRef.current) cancelAnimationFrame(fadeRafRef.current) }
  }, [tileUrl]) // eslint-disable-line react-hooks/exhaustive-deps

  const makeTileLayer = (url: string, id: string, opacity: number) =>
    new TileLayer({
      id, data: url, minZoom: 0, maxZoom: 8, tileSize: 256,
      extent: [-180, -90, 180, 90], opacity,
      renderSubLayers: (props) => {
        const { boundingBox } = props.tile
        return new BitmapLayer(props, {
          data: undefined, image: props.data,
          bounds: [boundingBox[0][0], boundingBox[0][1], boundingBox[1][0], boundingBox[1][1]],
          _imageCoordinateSystem: COORDINATE_SYSTEM.LNGLAT,
        })
      },
    })

  const layers = [
    ...(prevUrl ? [makeTileLayer(prevUrl, 'tile-prev', 1 - fadeOpacity)] : []),
    makeTileLayer(currentUrl, 'tile-current', fadeOpacity),
    ...extraLayers,
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
          const newZoom = (vs as MapViewState).zoom ?? 0
          if (onViewZoomChange && Math.abs(newZoom - lastReportedZoom.current) >= 0.5) {
            lastReportedZoom.current = newZoom
            onViewZoomChange(newZoom)
          }
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
              selectedRegion === r.id ? 'bg-amber-500/70 ring-1 ring-amber-300' : 'bg-white/10 hover:bg-white/20'
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
            {'<- Globe'}
          </button>
        )}
      </div>
    </div>
  )
}
