import { useEffect, useState } from 'react'

interface RegionStats {
  primary: { value: string; label: string; trend: 'up' | 'down' | 'neutral' }
  period: string
  secondary: { label: string; value: string; color: string }[]
}

// Demo dane 2015–2024; docelowo fetch z changes.json per region z HF CDN
const REGION_STATS: Record<string, RegionStats> = {
  amazonia: {
    primary: { value: '−34%', label: 'zieleni', trend: 'down' },
    period: '2015–2024',
    secondary: [
      { label: 'deforestacja', value: '18%', color: 'text-red-400' },
      { label: 'zabudowa', value: '12%', color: 'text-orange-400' },
      { label: 'woda', value: '8%', color: 'text-blue-400' },
    ],
  },
  dubai: {
    primary: { value: '+47%', label: 'zabudowy', trend: 'up' },
    period: '2015–2024',
    secondary: [
      { label: 'urban expansion', value: '23%', color: 'text-orange-400' },
      { label: 'NDVI spadek', value: '−15%', color: 'text-red-400' },
      { label: 'woda', value: '3%', color: 'text-blue-400' },
    ],
  },
  arctic: {
    primary: { value: '−28%', label: 'pokrywy lodowej', trend: 'down' },
    period: '2015–2024',
    secondary: [
      { label: 'lód morski', value: '−28%', color: 'text-cyan-400' },
      { label: 'otwarta woda', value: '+15%', color: 'text-blue-400' },
      { label: 'zabudowa', value: '0%', color: 'text-white/40' },
    ],
  },
}

interface Props {
  regionId: string | null
  dateIndex?: number
}

export function StatsPanel({ regionId }: Props) {
  const [mounted, setMounted] = useState(false)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (regionId) {
      setMounted(true)
      // minimalny tick żeby CSS transition się uruchomił po mount
      requestAnimationFrame(() => requestAnimationFrame(() => setVisible(true)))
    } else {
      setVisible(false)
      const t = setTimeout(() => setMounted(false), 300)
      return () => clearTimeout(t)
    }
  }, [regionId])

  if (!mounted || !regionId) return null

  const stats = REGION_STATS[regionId]
  if (!stats) return null

  const { primary, period, secondary } = stats
  const trendColor =
    primary.trend === 'down' ? 'text-red-400' : primary.trend === 'up' ? 'text-emerald-400' : 'text-white'

  return (
    <>
      {/* Desktop: panel boczny (left-4 top-16) */}
      <div
        className={[
          'absolute left-4 top-16 z-10 hidden sm:flex',
          'flex-col gap-3 rounded-xl bg-black/60 p-4 backdrop-blur w-52',
          'transition-all duration-300 ease-out',
          visible ? 'translate-x-0 opacity-100' : '-translate-x-4 opacity-0',
        ].join(' ')}
        role="region"
        aria-label="Statystyki regionu"
      >
        <PanelContent primary={primary} trendColor={trendColor} period={period} secondary={secondary} />
      </div>

      {/* Mobile: bottom sheet */}
      <div
        className={[
          'fixed bottom-0 left-0 right-0 z-20 flex sm:hidden',
          'flex-col gap-3 rounded-t-2xl bg-black/80 px-5 py-4 backdrop-blur',
          'transition-all duration-300 ease-out',
          visible ? 'translate-y-0 opacity-100' : 'translate-y-full opacity-0',
        ].join(' ')}
        role="region"
        aria-label="Statystyki regionu"
      >
        <PanelContent primary={primary} trendColor={trendColor} period={period} secondary={secondary} />
      </div>
    </>
  )
}

interface PanelContentProps {
  primary: RegionStats['primary']
  trendColor: string
  period: string
  secondary: RegionStats['secondary']
}

function PanelContent({ primary, trendColor, period, secondary }: PanelContentProps) {
  return (
    <>
      <p className="text-xs font-semibold uppercase tracking-wider text-white/50">Zmiana {period}</p>

      {/* Główna liczba */}
      <div className="flex items-baseline gap-1.5">
        <span className={`text-4xl font-bold tabular-nums leading-none ${trendColor}`}>{primary.value}</span>
        <span className="text-sm text-white/70">{primary.label}</span>
      </div>

      {/* Divider */}
      <div className="h-px bg-white/10" />

      {/* Sekundarne statystyki */}
      <div className="flex flex-col gap-1.5">
        {secondary.map((s) => (
          <div key={s.label} className="flex items-center justify-between text-sm">
            <span className="text-white/60">{s.label}</span>
            <span className={`font-medium tabular-nums ${s.color}`}>{s.value}</span>
          </div>
        ))}
      </div>

      {/* Źródło */}
      <p className="text-[10px] text-white/30">MODIS · HLS · CVA · dane demo</p>
    </>
  )
}
