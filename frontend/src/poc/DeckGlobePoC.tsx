import { useCallback, useEffect, useRef, useState } from 'react'
import DeckGL from '@deck.gl/react'
import { TileLayer } from '@deck.gl/geo-layers'
import { BitmapLayer } from '@deck.gl/layers'
import { _GlobeView as GlobeView } from '@deck.gl/core'
import type { MapViewState } from '@deck.gl/core'

const GIBS_URL =
  'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/' +
  'BlueMarble_NextGeneration/default/2004-08/' +
  '500m/{z}/{y}/{x}.jpg'

// Wyższe zoom bo _GlobeView skaluje inaczej niż Mercator
const STOPS = [
  { longitude: 0, latitude: 20, zoom: 0.8, label: 'Glob' },
  { longitude: -60, latitude: -5, zoom: 8, label: 'Amazonia' },
  { longitude: 55.3, latitude: 25.2, zoom: 9, label: 'Dubai' },
  { longitude: 15, latitude: 79, zoom: 6, label: 'Arktyka' },
]

const DWELL_MS = 2000
const FLY_MS = 3500

const GLOBE = new GlobeView({ id: 'globe', nearZMultiplier: 0.1 })

export function DeckGlobePoC() {
  const [viewState, setViewState] = useState<MapViewState>(STOPS[0])
  const [tourStep, setTourStep] = useState(0)
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([])
  const tourActiveRef = useRef(false)

  const clearTour = useCallback(() => {
    timersRef.current.forEach(clearTimeout)
    timersRef.current = []
    tourActiveRef.current = false
  }, [])

  useEffect(() => clearTour, [clearTour])

  // Instant jump — bez transition żeby wykluczyć błędy interpolacji
  const flyTo = useCallback(
    (step: number) => {
      clearTour()
      setTourStep(step)
      setViewState({ ...STOPS[step], transitionDuration: 0 })
    },
    [clearTour],
  )

  const startTour = useCallback(() => {
    clearTour()
    tourActiveRef.current = true
    let delay = 0
    STOPS.slice(1).forEach((stop, i) => {
      const step = i + 1
      const t = setTimeout(() => {
        if (!tourActiveRef.current) return
        setTourStep(step)
        setViewState({ ...stop, transitionDuration: FLY_MS })
      }, delay)
      timersRef.current.push(t)
      delay += FLY_MS + DWELL_MS
    })
    const tEnd = setTimeout(() => {
      tourActiveRef.current = false
      setTourStep(0)
    }, delay)
    timersRef.current.push(tEnd)
  }, [clearTour])

  const tileLayer = new TileLayer({
    id: 'blue-marble',
    data: GIBS_URL,
    minZoom: 0,
    maxZoom: 8,
    tileSize: 256,
    extent: [-180, -90, 180, 90],
    renderSubLayers: (props) => {
      const { boundingBox } = props.tile
      return new BitmapLayer(props, {
        data: undefined,
        image: props.data,
        bounds: [
          boundingBox[0][0],
          boundingBox[0][1],
          boundingBox[1][0],
          boundingBox[1][1],
        ],
      })
    },
  })

  return (
    <div className="relative h-full w-full bg-black">
      <DeckGL
        views={GLOBE}
        viewState={viewState}
        onViewStateChange={({ viewState: vs, interactionState }) => {
          if (interactionState.isZooming || interactionState.isPanning || interactionState.isRotating) {
            clearTour()
          }
          setViewState(vs as MapViewState)
        }}
        controller
        layers={[tileLayer]}
      />

      {/* Debug HUD — lat/lon/zoom żeby potwierdzić czy współrzędne są poprawne */}
      <div className="absolute left-4 top-4 space-y-1 text-xs text-white/60">
        <div>T6.2 · Deck.gl GlobeView PoC · Blue Marble</div>
        <div>
          lon: {(viewState.longitude ?? 0).toFixed(2)} &nbsp;
          lat: {(viewState.latitude ?? 0).toFixed(2)} &nbsp;
          zoom: {(viewState.zoom ?? 0).toFixed(2)}
        </div>
      </div>

      {/* Diagnostyczne przyciski — mapowanie lon/lat w _GlobeView */}
      <div className="absolute bottom-16 left-1/2 flex -translate-x-1/2 gap-1 text-xs">
        {[
          { label: '0°E 0°N', lon: 0, lat: 0 },
          { label: '20°E 0°N', lon: 20, lat: 0 },
          { label: '-60°W 0°N', lon: -60, lat: 0 },
          { label: '55°E 25°N', lon: 55, lat: 25 },
          { label: '120°E 30°N', lon: 120, lat: 30 },
        ].map(({ label, lon, lat }) => (
          <button
            key={label}
            className="rounded bg-yellow-500/20 px-2 py-1 text-yellow-200 backdrop-blur hover:bg-yellow-500/40"
            onClick={() => setViewState({ longitude: lon, latitude: lat, zoom: 4 })}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 gap-2">
        <button
          className="rounded bg-white/10 px-4 py-2 text-sm text-white backdrop-blur hover:bg-white/20"
          onClick={startTour}
        >
          ▶ Tour
        </button>
        {STOPS.slice(1).map((stop, i) => (
          <button
            key={stop.label}
            className={`rounded px-3 py-2 text-sm text-white backdrop-blur ${
              tourStep === i + 1 ? 'bg-white/30' : 'bg-white/10 hover:bg-white/20'
            }`}
            onClick={() => flyTo(i + 1)}
          >
            {stop.label}
          </button>
        ))}
      </div>
    </div>
  )
}
