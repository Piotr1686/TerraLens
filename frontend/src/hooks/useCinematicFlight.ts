import { useCallback, useRef } from 'react'
import type { MapViewState } from '@deck.gl/core'

function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}

// Lerp dla longitudes z obsługą wrap-around (np. -170 → 170)
function lerpLon(a: number, b: number, t: number): number {
  let delta = b - a
  if (delta > 180) delta -= 360
  if (delta < -180) delta += 360
  return a + delta * t
}

export interface CinematicFlightConfig {
  duration?: number  // ms, domyślnie 2200
  zoomDip?: number   // ile zoom units "zanurzyć" w środku lotu, domyślnie 1.5
}

const INITIAL_POS: MapViewState = { longitude: 0, latitude: 20, zoom: 1.0 }

export function useCinematicFlight() {
  const rafRef = useRef<number | null>(null)
  // Pozycja kamery — trzymana wewnętrznie, aktualizowana przez setPosition i tick
  const posRef = useRef<MapViewState>(INITIAL_POS)

  const cancel = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
  }, [])

  // Synchronizacja pozycji po interakcji usera (wywołaj z onViewStateChange)
  const setPosition = useCallback((vs: MapViewState) => {
    posRef.current = vs
  }, [])

  const fly = useCallback(
    (
      to: MapViewState,
      config: CinematicFlightConfig,
      onFrame: (vs: MapViewState) => void,
      onComplete?: () => void,
    ) => {
      cancel()
      // posRef.current odczytywany tutaj, NIE podczas renderu
      const from = posRef.current
      const { duration = 2200, zoomDip = 1.5 } = config
      const z0 = from.zoom ?? 1
      const z1 = to.zoom ?? 1
      const lon0 = from.longitude ?? 0
      const lon1 = to.longitude ?? 0
      const lat0 = from.latitude ?? 0
      const lat1 = to.latitude ?? 0

      // Punkt kontrolny Beziera — parabola zoom-out w połowie lotu
      const zControl = Math.max(0.5, Math.min(z0, z1) - zoomDip)
      const startTime = performance.now()

      const tick = (now: number) => {
        const elapsed = now - startTime
        if (elapsed >= duration) {
          const final = { longitude: lon1, latitude: lat1, zoom: z1 }
          posRef.current = final
          onFrame(final)
          onComplete?.()
          return
        }
        const t = easeInOutCubic(elapsed / duration)
        const zoom = (1 - t) ** 2 * z0 + 2 * (1 - t) * t * zControl + t ** 2 * z1
        const vs: MapViewState = {
          longitude: lerpLon(lon0, lon1, t),
          latitude: lat0 + (lat1 - lat0) * t,
          zoom,
        }
        posRef.current = vs
        onFrame(vs)
        rafRef.current = requestAnimationFrame(tick)
      }

      rafRef.current = requestAnimationFrame(tick)
    },
    [cancel],
  )

  return { fly, cancel, setPosition }
}
