import { useMemo } from 'react'
import { TileLayer } from '@deck.gl/geo-layers'
import { BitmapLayer } from '@deck.gl/layers'
import { COORDINATE_SYSTEM } from '@deck.gl/core'
import type { Layer } from '@deck.gl/core'
import { PMTiles } from 'pmtiles'

const archiveCache = new Map<string, PMTiles>()
function getArchive(url: string): PMTiles {
  if (!archiveCache.has(url)) archiveCache.set(url, new PMTiles(url))
  return archiveCache.get(url)!
}

interface Config {
  region: string | null
  pmtilesUrl: string | null
  opacity: number
  bbox?: [number, number, number, number]
}

export function usePMTilesLayer({ region, pmtilesUrl, opacity, bbox }: Config): Layer | null {
  return useMemo(() => {
    if (!region || !pmtilesUrl || opacity === 0) return null
    const archive = getArchive(pmtilesUrl)
    return new TileLayer({
      id: `pmtiles-${region}`,
      getTileData: async ({ index: { x, y, z } }: any) => {
        try {
          const result = await archive.getZxy(z, x, y)
          if (!result?.data) return null
          return createImageBitmap(new Blob([result.data], { type: 'image/webp' }))
        } catch {
          return null
        }
      },
      minZoom: 2,
      maxZoom: 8,
      tileSize: 256,
      extent: bbox ?? [-180, -90, 180, 90],
      opacity,
      renderSubLayers: (props: any) => {
        if (!props.data) return null
        const { boundingBox } = props.tile
        return new BitmapLayer(props, {
          data: undefined,
          image: props.data,
          bounds: [boundingBox[0][0], boundingBox[0][1], boundingBox[1][0], boundingBox[1][1]],
          _imageCoordinateSystem: COORDINATE_SYSTEM.LNGLAT,
        })
      },
    })
  }, [region, pmtilesUrl, opacity, bbox])
}
