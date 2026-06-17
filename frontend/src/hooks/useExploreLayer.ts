import { useEffect, useMemo, useRef, useState } from 'react'
import { TileLayer } from '@deck.gl/geo-layers'
import { BitmapLayer } from '@deck.gl/layers'
import { COORDINATE_SYSTEM } from '@deck.gl/core'
import type { Layer } from '@deck.gl/core'
import { resolveScene } from '@/lib/mpc'
import type { SceneResult } from '@/lib/mpc'

export type ExploreStatus = 'idle' | 'loading' | 'ready' | 'empty' | 'error'

interface Config {
  /** Punkt zainteresowania w trybie Explore; null = tryb wyłączony. */
  target: { lon: number; lat: number } | null
  opacity?: number
}

interface Result {
  layers: Layer[]
  scene: SceneResult | null
  status: ExploreStatus
}

/**
 * Dla punktu (lon, lat) wybiera najlepsze realne źródło (kaskada NAIP→S2 w resolveScene)
 * i buduje deck.gl TileLayer z hostowanego tilera MPC. maxZoom i URL pochodzą ze sceny
 * (NAIP z18/0.6 m, S2 z14/10 m). Mirror makeTileLayer z Globe.tsx — extent = footprint sceny.
 */
export function useExploreLayer({ target, opacity = 1 }: Config): Result {
  const [scene, setScene] = useState<SceneResult | null>(null)
  const [status, setStatus] = useState<ExploreStatus>('idle')
  const reqId = useRef(0)

  useEffect(() => {
    if (!target) {
      setScene(null)
      setStatus('idle')
      return
    }

    const id = ++reqId.current
    const ctrl = new AbortController()
    setStatus('loading')

    resolveScene(target.lon, target.lat, { signal: ctrl.signal })
      .then((result) => {
        if (id !== reqId.current) return // starsze zapytanie — porzuć
        setScene(result)
        setStatus(result ? 'ready' : 'empty')
      })
      .catch((err) => {
        if (ctrl.signal.aborted || id !== reqId.current) return
        console.error('useExploreLayer resolveScene:', err)
        setScene(null)
        setStatus('error')
      })

    return () => ctrl.abort()
  }, [target?.lon, target?.lat]) // eslint-disable-line react-hooks/exhaustive-deps

  return useMemo(() => {
    if (!scene || opacity === 0) return { layers: [], scene, status }

    const layer = new TileLayer({
      id: `explore-${scene.source}-${scene.itemId}`,
      data: scene.tileUrl,
      minZoom: 0,
      maxZoom: scene.maxZoom,
      tileSize: 256,
      extent: scene.bbox,
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

    return { layers: [layer], scene, status }
  }, [scene, opacity, status])
}
