import { useEffect, useMemo, useRef, useState } from 'react'
import { TileLayer } from '@deck.gl/geo-layers'
import { BitmapLayer } from '@deck.gl/layers'
import { COORDINATE_SYSTEM } from '@deck.gl/core'
import type { Layer } from '@deck.gl/core'
import { pickScene, sentinelTileUrlTemplate } from '@/lib/mpc'
import type { SceneResult } from '@/lib/mpc'

export type SentinelStatus = 'idle' | 'loading' | 'ready' | 'empty' | 'error'

interface Config {
  /** Punkt zainteresowania w trybie Explore; null = tryb wyłączony. */
  target: { lon: number; lat: number } | null
  opacity?: number
  /** Maks. zoom kafli S2 (street-level). */
  maxZoom?: number
}

interface Result {
  layers: Layer[]
  scene: SceneResult | null
  status: SentinelStatus
}

/**
 * Dla punktu (lon, lat) wybiera najczystszą scenę S2 (MPC) i buduje deck.gl TileLayer
 * z hostowanego tilera. Mirror makeTileLayer z Globe.tsx — różnica: maxZoom street-level
 * i extent ograniczony do footprintu sceny (mniej pustych żądań poza MGRS-tile).
 */
export function useSentinelLayer({ target, opacity = 1, maxZoom = 14 }: Config): Result {
  const [scene, setScene] = useState<SceneResult | null>(null)
  const [status, setStatus] = useState<SentinelStatus>('idle')
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

    pickScene(target.lon, target.lat, { signal: ctrl.signal })
      .then((result) => {
        if (id !== reqId.current) return // starsze zapytanie — porzuć
        setScene(result)
        setStatus(result ? 'ready' : 'empty')
      })
      .catch((err) => {
        if (ctrl.signal.aborted || id !== reqId.current) return
        console.error('useSentinelLayer pickScene:', err)
        setScene(null)
        setStatus('error')
      })

    return () => ctrl.abort()
  }, [target?.lon, target?.lat]) // eslint-disable-line react-hooks/exhaustive-deps

  return useMemo(() => {
    if (!scene || opacity === 0) return { layers: [], scene, status }

    const layer = new TileLayer({
      id: `sentinel-${scene.itemId}`,
      data: sentinelTileUrlTemplate(scene.itemId),
      minZoom: 0,
      maxZoom,
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
  }, [scene, opacity, maxZoom, status])
}
