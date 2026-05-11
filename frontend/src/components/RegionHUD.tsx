import { useEffect, useState } from 'react'
import type { Region } from '@/data/regions'

interface Props {
  region: Region | null
}

export function RegionHUD({ region }: Props) {
  const [mounted, setMounted] = useState(false)
  const [visible, setVisible] = useState(false)
  const [displayRegion, setDisplayRegion] = useState<Region | null>(null)

  useEffect(() => {
    if (region) {
      setDisplayRegion(region)
      setMounted(true)
      requestAnimationFrame(() => requestAnimationFrame(() => setVisible(true)))
    } else {
      setVisible(false)
      const t = setTimeout(() => setMounted(false), 400)
      return () => clearTimeout(t)
    }
  }, [region])

  if (!mounted || !displayRegion) return null

  const { latitude, longitude, label } = displayRegion
  const latStr = latitude >= 0 ? `${latitude}°N` : `${Math.abs(latitude)}°S`
  const lonStr = longitude >= 0 ? `${longitude}°E` : `${Math.abs(longitude)}°W`

  return (
    <div
      className={[
        'pointer-events-none fixed right-6 top-6 z-10',
        'flex flex-col gap-0.5 rounded-xl px-4 py-3',
        'bg-white/10 backdrop-blur',
        'transition-all duration-300 ease-out',
        visible ? 'translate-x-0 opacity-100' : 'translate-x-4 opacity-0',
      ].join(' ')}
      aria-live="polite"
    >
      <span className="text-lg font-bold leading-tight text-white">{label}</span>
      <span className="text-xs tabular-nums text-white/50">{latStr}, {lonStr}</span>
    </div>
  )
}
