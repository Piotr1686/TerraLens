import { useCallback, useState } from 'react'
import DeckGL from '@deck.gl/react'
import { TileLayer } from '@deck.gl/geo-layers'
import { BitmapLayer } from '@deck.gl/layers'
import { _GlobeView as GlobeView, FlyToInterpolator } from '@deck.gl/core'
import type { MapViewState } from '@deck.gl/core'

// Trasy kamery — cinematic 10-second hook (Amazonia → Dubai → Arktyka)
const TOUR: MapViewState[] = [
  { longitude: 0, latitude: 20, zoom: 0.8, transitionDuration: 0 },
  {
    longitude: -60,
    latitude: -5,
    zoom: 4,
    transitionDuration: 3500,
    transitionInterpolator: new FlyToInterpolator({ speed: 1.2 }),
  },
  {
    longitude: 55.3,
    latitude: 25.2,
    zoom: 5,
    transitionDuration: 3000,
    transitionInterpolator: new FlyToInterpolator({ speed: 1.4 }),
  },
  {
    longitude: 15,
    latitude: 79,
    zoom: 3.5,
    transitionDuration: 3500,
    transitionInterpolator: new FlyToInterpolator({ speed: 1.2 }),
  },
]

const LABELS = ['Amazonia', 'Dubai', 'Arktyka']

// GIBS MODIS: publiczne, bez auth, EPSG:4326 kompatybilne z GlobeView
const GIBS_URL =
  'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/' +
  'MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-01-01/' +
  'GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg'

export function DeckGlobePoC() {
  const [viewState, setViewState] = useState<MapViewState>(TOUR[0])
  const [tourStep, setTourStep] = useState(0)
  const [autoTour, setAutoTour] = useState(false)

  const flyTo = useCallback((step: number) => {
    if (step >= TOUR.length) return
    setViewState(TOUR[step])
    setTourStep(step)
  }, [])

  const startTour = useCallback(() => {
    setAutoTour(true)
    flyTo(1)
  }, [flyTo])

  const handleTransitionEnd = useCallback(() => {
    if (!autoTour) return
    setTourStep((prev) => {
      const next = prev + 1
      if (next < TOUR.length) {
        setViewState(TOUR[next])
        return next
      }
      setAutoTour(false)
      return prev
    })
  }, [autoTour])

  const tileLayer = new TileLayer({
    id: 'gibs-modis',
    data: GIBS_URL,
    minZoom: 0,
    maxZoom: 9,
    tileSize: 256,
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
        views={new GlobeView({ id: 'globe', nearZMultiplier: 0.1 })}
        viewState={viewState}
        onViewStateChange={({ viewState: vs }) =>
          setViewState(vs as MapViewState)
        }
        controller
        layers={[tileLayer]}
        onAfterRender={handleTransitionEnd}
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
            onClick={() => {
              setAutoTour(false)
              flyTo(i + 1)
            }}
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
