import { useCallback, useEffect, useRef, useState } from 'react'
import DeckGL from '@deck.gl/react'
import { TileLayer } from '@deck.gl/geo-layers'
import { BitmapLayer } from '@deck.gl/layers'
import { _GlobeView as GlobeView, FlyToInterpolator } from '@deck.gl/core'
import type { MapViewState } from '@deck.gl/core'

// BlueMarble_NextGeneration — layer bez daty (time-invariant), ext .jpeg, zoom 0–7
const GIBS_URL =
  'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/' +
  'BlueMarble_NextGeneration/default/' +
  '500m/{z}/{y}/{x}.jpeg'

// Zoom w _GlobeView: 1=cała Ziemia ~55% ekranu, 2=kontynent, 3=duży region
const STOPS = [
  { longitude: 0, latitude: 20, zoom: 1.0, label: 'Glob' },
  { longitude: -60, latitude: -5, zoom: 2.5, label: 'Amazonia' },
  { longitude: 55.3, latitude: 25.2, zoom: 3.5, label: 'Dubai' },
  { longitude: 15, latitude: 68, zoom: 2.0, label: 'Arktyka' },
]

const DWELL_MS = 2500
const FLY_MS = 4000

const GLOBE = new GlobeView({ id: 'globe', nearZMultiplier: 0.1 })
const INITIAL_STATE: MapViewState = STOPS[0]

export function DeckGlobePoC() {
  const [viewState, setViewState] = useState<MapViewState>(INITIAL_STATE)
  const [tourStep, setTourStep] = useState(0)
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([])
  const tourActiveRef = useRef(false)

  const clearTour = useCallback(() => {
    timersRef.current.forEach(clearTimeout)
    timersRef.current = []
    tourActiveRef.current = false
  }, [])

  useEffect(() => clearTour, [clearTour])

  const flyTo = useCallback(
    (step: number) => {
      clearTour()
      setTourStep(step)
      setViewState({
        ...STOPS[step],
        transitionDuration: FLY_MS,
        transitionInterpolator: new FlyToInterpolator({ speed: 1.5 }),
      })
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
        setViewState({
          ...stop,
          transitionDuration: FLY_MS,
          transitionInterpolator: new FlyToInterpolator({ speed: 1.5 }),
        })
      }, delay)
      timersRef.current.push(t)
      delay += FLY_MS + DWELL_MS
    })
    // Po zakończeniu tour: powrót do widoku globalnego
    const tEnd = setTimeout(() => {
      if (!tourActiveRef.current) return
      tourActiveRef.current = false
      setTourStep(0)
      setViewState({
        ...INITIAL_STATE,
        transitionDuration: FLY_MS,
        transitionInterpolator: new FlyToInterpolator({ speed: 1.2 }),
      })
    }, delay)
    timersRef.current.push(tEnd)
  }, [clearTour])

  const tileLayer = new TileLayer({
    id: 'blue-marble',
    data: GIBS_URL,
    minZoom: 0,
    maxZoom: 7,
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

      {/* Debug HUD */}
      <div className="absolute left-4 top-4 space-y-1 text-xs text-white/60">
        <div>T6.2 · Deck.gl GlobeView PoC · Blue Marble</div>
        <div>
          lon: {(viewState.longitude ?? 0).toFixed(2)} &nbsp;
          lat: {(viewState.latitude ?? 0).toFixed(2)} &nbsp;
          zoom: {(viewState.zoom ?? 0).toFixed(2)}
        </div>
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
