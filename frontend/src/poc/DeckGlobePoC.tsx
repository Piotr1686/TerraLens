import { useCallback, useEffect, useRef, useState } from 'react'
import DeckGL from '@deck.gl/react'
import { TileLayer } from '@deck.gl/geo-layers'
import { BitmapLayer } from '@deck.gl/layers'
import { _GlobeView as GlobeView, FlyToInterpolator } from '@deck.gl/core'
import type { MapViewState } from '@deck.gl/core'

// GIBS MODIS w EPSG:4326 — jedyne co działa z GlobeView (nie GoogleMapsCompatible/WebMercator)
const GIBS_URL =
  'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/' +
  'MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-01-01/' +
  '250m/{z}/{y}/{x}.jpg'

const BASE_STOPS = [
  { longitude: 0, latitude: 20, zoom: 0.8 },
  { longitude: -60, latitude: -5, zoom: 4 },
  { longitude: 55.3, latitude: 25.2, zoom: 5 },
  { longitude: 15, latitude: 79, zoom: 3.5 },
]

const DURATIONS = [0, 3500, 3000, 3500]
const SPEEDS = [1, 1.2, 1.4, 1.2]
const LABELS = ['Amazonia', 'Dubai', 'Arktyka']

const GLOBE = new GlobeView({ id: 'globe', nearZMultiplier: 0.1 })

export function DeckGlobePoC() {
  const [viewState, setViewState] = useState<MapViewState>(BASE_STOPS[0])
  const [tourStep, setTourStep] = useState(0)
  const stepRef = useRef(0)
  const tourActiveRef = useRef(false)
  // Ref umożliwia onTransitionEnd odwołanie do advanceStep bez "accessed before declaration"
  const advanceStepRef = useRef<() => void>(() => {})

  const advanceStep = useCallback(() => {
    if (!tourActiveRef.current) return
    const next = stepRef.current + 1
    if (next >= BASE_STOPS.length) {
      tourActiveRef.current = false
      setTourStep(0)
      return
    }
    stepRef.current = next
    setTourStep(next)
    setViewState({
      ...BASE_STOPS[next],
      transitionDuration: DURATIONS[next],
      transitionInterpolator: new FlyToInterpolator({ speed: SPEEDS[next] }),
      onTransitionEnd: () => advanceStepRef.current?.(),
    })
  }, [])

  useEffect(() => { advanceStepRef.current = advanceStep }, [advanceStep])

  const startTour = useCallback(() => {
    tourActiveRef.current = true
    stepRef.current = 0
    advanceStep()
  }, [advanceStep])

  const flyTo = useCallback((step: number) => {
    tourActiveRef.current = false
    stepRef.current = step
    setTourStep(step)
    setViewState({
      ...BASE_STOPS[step],
      transitionDuration: DURATIONS[step],
      transitionInterpolator: new FlyToInterpolator({ speed: SPEEDS[step] }),
    })
  }, [])

  const tileLayer = new TileLayer({
    id: 'gibs-modis',
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
        onViewStateChange={({ viewState: vs }) =>
          setViewState(vs as MapViewState)
        }
        controller
        layers={[tileLayer]}
      />

      {/* HUD */}
      <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 gap-2">
        <button
          className="rounded bg-white/10 px-4 py-2 text-sm text-white backdrop-blur hover:bg-white/20"
          onClick={startTour}
        >
          ▶ Cinematic Tour
        </button>
        {LABELS.map((label, i) => (
          <button
            key={label}
            className={`rounded px-3 py-2 text-sm text-white backdrop-blur ${
              tourStep === i + 1
                ? 'bg-white/30'
                : 'bg-white/10 hover:bg-white/20'
            }`}
            onClick={() => flyTo(i + 1)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="absolute left-4 top-4 text-xs text-white/50">
        T6.2 · Deck.gl GlobeView PoC · MODIS Terra 2024-01-01
      </div>
    </div>
  )
}
