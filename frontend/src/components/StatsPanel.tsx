import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

interface RegionStats {
  primary: { value: string; label: string; trend: 'up' | 'down' | 'neutral' }
  secondary: { label: string; value: string; color: string }[]
}

// Demo dane; docelowo fetch z changes.json per region z HF CDN
const REGION_STATS: Record<string, RegionStats> = {
  amazonia: {
    primary: { value: '−34%', label: 'vegetation', trend: 'down' },
    secondary: [
      { label: 'deforestation', value: '18%', color: 'text-red-400' },
      { label: 'urban area',    value: '12%', color: 'text-orange-400' },
      { label: 'water',         value: '8%',  color: 'text-blue-400' },
    ],
  },
  dubai: {
    primary: { value: '+47%', label: 'urban area', trend: 'up' },
    secondary: [
      { label: 'urban expansion', value: '23%',  color: 'text-orange-400' },
      { label: 'NDVI drop',       value: '−15%', color: 'text-red-400' },
      { label: 'water',           value: '3%',   color: 'text-blue-400' },
    ],
  },
  arctic: {
    primary: { value: '−28%', label: 'ice cover', trend: 'down' },
    secondary: [
      { label: 'sea ice',    value: '−28%', color: 'text-cyan-400' },
      { label: 'open water', value: '+15%', color: 'text-blue-400' },
      { label: 'urban area', value: '0%',   color: 'text-white/40' },
    ],
  },
}

const CHART_DATA: Record<string, { year: number; v: number }[]> = {
  amazonia: [
    { year: 2015, v: 0.72 }, { year: 2017, v: 0.68 }, { year: 2019, v: 0.61 },
    { year: 2021, v: 0.54 }, { year: 2023, v: 0.48 }, { year: 2025, v: 0.42 },
  ],
  dubai: [
    { year: 2015, v: 0.28 }, { year: 2017, v: 0.33 }, { year: 2019, v: 0.38 },
    { year: 2021, v: 0.43 }, { year: 2023, v: 0.48 }, { year: 2025, v: 0.52 },
  ],
  arctic: [
    { year: 2015, v: 6.8 }, { year: 2017, v: 6.2 }, { year: 2019, v: 5.7 },
    { year: 2021, v: 5.1 }, { year: 2023, v: 4.6 }, { year: 2025, v: 4.1 },
  ],
}

const CHART_META: Record<string, { label: string; color: string }> = {
  amazonia: { label: 'NDVI', color: '#4ade80' },
  dubai:    { label: 'Urban index', color: '#fb923c' },
  arctic:   { label: 'Ice extent (M km²)', color: '#67e8f9' },
}

interface Props {
  regionId: string | null
  currentDate?: string
}

export function StatsPanel({ regionId, currentDate }: Props) {
  const [mounted, setMounted] = useState(false)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (regionId) {
      setMounted(true)
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

  const { primary, secondary } = stats
  const endYear = currentDate ? currentDate.slice(0, 4) : new Date().getFullYear().toString()
  const period = `2015–${endYear}`
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
        aria-label="Region statistics"
      >
        <PanelContent
          primary={primary} trendColor={trendColor} period={period}
          secondary={secondary} regionId={regionId}
        />
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
        aria-label="Region statistics"
      >
        <PanelContent
          primary={primary} trendColor={trendColor} period={period}
          secondary={secondary} regionId={regionId}
        />
      </div>
    </>
  )
}

interface ChartTooltipProps {
  active?: boolean
  payload?: { value: number }[]
  label?: number
}

function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded bg-black/80 px-2 py-1 text-xs text-white">
      {label}: {payload[0].value.toFixed(2)}
    </div>
  )
}

interface PanelContentProps {
  primary: RegionStats['primary']
  trendColor: string
  period: string
  secondary: RegionStats['secondary']
  regionId: string
}

function PanelContent({ primary, trendColor, period, secondary, regionId }: PanelContentProps) {
  const chartData = CHART_DATA[regionId]
  const meta = CHART_META[regionId]

  return (
    <>
      <p className="text-xs font-semibold uppercase tracking-wider text-white/50">Change {period}</p>

      <div className="flex items-baseline gap-1.5">
        <span className={`text-4xl font-bold tabular-nums leading-none ${trendColor}`}>{primary.value}</span>
        <span className="text-sm text-white/70">{primary.label}</span>
      </div>

      <div className="h-px bg-white/10" />

      <div className="flex flex-col gap-1.5">
        {secondary.map((s) => (
          <div key={s.label} className="flex items-center justify-between text-sm">
            <span className="text-white/60">{s.label}</span>
            <span className={`font-medium tabular-nums ${s.color}`}>{s.value}</span>
          </div>
        ))}
      </div>

      {chartData && meta && (
        <>
          <div className="h-px bg-white/10" />
          <p className="text-[10px] font-semibold uppercase tracking-wider text-white/40">{meta.label}</p>
          <div className="h-20">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 2, right: 4, bottom: 0, left: -28 }}>
                <XAxis
                  dataKey="year"
                  tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 9 }}
                  tickLine={false}
                  axisLine={false}
                  interval={1}
                />
                <YAxis
                  tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 9 }}
                  tickLine={false}
                  axisLine={false}
                  width={36}
                />
                <Tooltip content={<ChartTooltip />} />
                <Line
                  type="monotone"
                  dataKey="v"
                  stroke={meta.color}
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}

      <p className="text-[10px] text-white/30">MODIS · HLS · CVA · demo data</p>
    </>
  )
}
