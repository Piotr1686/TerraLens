import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { TileLayer } from '@deck.gl/geo-layers'
import { BitmapLayer } from '@deck.gl/layers'
import { COORDINATE_SYSTEM } from '@deck.gl/core'
import type { Layer } from '@deck.gl/core'
import { listScenes } from '@/lib/mpc'
import type { SceneList, SceneResult } from '@/lib/mpc'

export type ExploreStatus = 'idle' | 'loading' | 'ready' | 'empty' | 'error'

/**
 * Dla punktu (lon, lat) pobiera listy dostępnych scen obu źródeł (NAIP + S2).
 * Wybór konkretnej sceny/źródła/daty robi warstwa wyżej (App + useExploreSelection).
 */
export function useExploreScenes(target: { lon: number; lat: number } | null): {
  scenes: SceneList | null
  status: ExploreStatus
  retry: () => void
} {
  const [scenes, setScenes] = useState<SceneList | null>(null)
  const [status, setStatus] = useState<ExploreStatus>('idle')
  // Nonce do ręcznego ponowienia po błędzie (MPC bywa przejściowo 504 — patrz mpc.ts stacSearch).
  const [nonce, setNonce] = useState(0)
  const reqId = useRef(0)

  useEffect(() => {
    if (!target) {
      setScenes(null)
      setStatus('idle')
      return
    }

    const id = ++reqId.current
    const ctrl = new AbortController()
    setStatus('loading')

    listScenes(target.lon, target.lat, { signal: ctrl.signal })
      .then((result) => {
        if (id !== reqId.current) return // starsze zapytanie — porzuć
        setScenes(result)
        const total = result.naip.length + result['sentinel-2'].length
        setStatus(total > 0 ? 'ready' : 'empty')
      })
      .catch((err) => {
        if (ctrl.signal.aborted || id !== reqId.current) return
        console.error('useExploreScenes listScenes:', err)
        setScenes(null)
        setStatus('error')
      })

    return () => ctrl.abort()
  }, [target?.lon, target?.lat, nonce]) // eslint-disable-line react-hooks/exhaustive-deps

  // Wymusza ponowne pobranie dla bieżącego punktu (bez zmiany targetu).
  const retry = useCallback(() => setNonce((n) => n + 1), [])

  return { scenes, status, retry }
}

/**
 * Buduje deck.gl TileLayer dla wybranej sceny (NAIP z18/0.6 m lub S2 z14/10 m).
 * maxZoom i URL pochodzą ze sceny; extent = footprint sceny. Mirror Globe.makeTileLayer.
 */
export function useExploreLayer({
  scene,
  opacity = 1,
}: {
  scene: SceneResult | null
  opacity?: number
}): Layer[] {
  return useMemo(() => {
    if (!scene || opacity === 0) return []

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

    return [layer]
  }, [scene, opacity])
}
