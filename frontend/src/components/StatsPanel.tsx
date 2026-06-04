import { useEffect, useRef, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

const HF_BASE = 'https://huggingface.co/datasets/Piotr1686/terralens-data/resolve/main'
// Źródło danych konfigurowalne (dev/staging przez VITE_CHANGES_URL); domyślnie HF CDN.
const CHANGES_URL = import.meta.env.VITE_CHANGES_URL ?? `${HF_BASE}/changes.json`

interface RegionStats {
  primary: { value: string; label: string; trend: 'up' | 'down' | 'neutral' }
  secondary: { label: string; value: string; color: string }[]
}

interface RegionPayload {
  primary: RegionStats['primary']
  secondary: RegionStats['secondary']
  chart: { t: string; v: number }[]
  chartMeta: { label: string; color: string }
  period: string
}

interface ChangesPayload {
  [regionId: string]: RegionPayload
}

// Bez MOCK_STATS — panel pokazuje wyłącznie realne dane z changes.json.
// Gdy danych brak (offline / fetch failed) → uczciwy stan "no data", nie zmyślone liczby.

function useChanges() {
  const [payload, setPayload] = useState<ChangesPayload | null>(null)
  const [status, setStatus] = useState<'loading' | 'live' | 'error'>('loading')
  const fetched = useRef(false)

  useEffect(() => {
    if (fetched.current) return
    fetched.current = true
    fetch(CHANGES_URL)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then((data: ChangesPayload) => { setPayload(data); setStatus('live') })
      .catch(() => { setStatus('error') })
  }, [])

  return { payload, status }
}

interface Props {
  regionId: string | null
}

export function StatsPanel({ regionId }: Props) {
  const [mounted, setMounted] = useState(false)
  const [visible, setVisible] = useState(false)
  const { payload, status } = useChanges()

  useEffect(() => {
    // Brama animacji wejścia/wyjścia panelu — synchroniczny setState jest tu zamierzony
    // (mount → slide-in przez rAF; unmount z 300ms opóźnieniem na slide-out).
    if (regionId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMounted(true)
      requestAnimationFrame(() => requestAnimationFrame(() => setVisible(true)))
    } else {
      setVisible(false)
      const t = setTimeout(() => setMounted(false), 300)
      return () => clearTimeout(t)
    }
  }, [regionId])

  if (!mounted || !regionId) return null

  const regionData = payload?.[regionId] ?? null

  const panelClasses = (extra: string) => [
    extra,
    'flex-col gap-3 backdrop-blur transition-all duration-300 ease-out',
  ].join(' ')

  return (
    <>
      {/* Desktop: panel boczny (left-4 top-16) */}
      <div
        className={[
          'absolute left-4 top-16 z-10 hidden sm:flex',
          'rounded-xl bg-black/60 p-4 w-52',
          panelClasses(''),
          visible ? 'translate-x-0 opacity-100' : '-translate-x-4 opacity-0',
        ].join(' ')}
        role="region"
        aria-label="Region statistics"
      >
        <PanelContent data={regionData} status={status} />
      </div>

      {/* Mobile: bottom sheet */}
      <div
        className={[
          'fixed bottom-0 left-0 right-0 z-20 flex sm:hidden',
          'rounded-t-2xl bg-black/80 px-5 py-4',
          panelClasses(''),
          visible ? 'translate-y-0 opacity-100' : 'translate-y-full opacity-0',
        ].join(' ')}
        role="region"
        aria-label="Region statistics"
      >
        <PanelContent data={regionData} status={status} />
      </div>
    </>
  )
}

interface ChartTooltipProps {
  active?: boolean
  payload?: { value: number }[]
  label?: string
}

function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded bg-black/80 px-2 py-1 text-xs text-white">
      {label}: {payload[0].value.toFixed(2)}
    </div>
  )
}

function PanelContent({ data, status }: { data: RegionPayload | null; status: 'loading' | 'live' | 'error' }) {
  // Brak realnych danych → uczciwy komunikat zamiast fikcji
  if (!data) {
    return (
      <>
        <p className="text-xs font-semibold uppercase tracking-wider text-white/50">Change detection</p>
        <p className="text-sm text-white/60">
          {status === 'loading' ? 'Loading data…' : 'Data unavailable'}
        </p>
      </>
    )
  }

  const { primary, secondary, chart, chartMeta, period } = data
  const trendColor =
    primary.trend === 'down' ? 'text-red-400' : primary.trend === 'up' ? 'text-emerald-400' : 'text-white'
  const tickInterval = chart.length > 6 ? Math.floor(chart.length / 5) : 0

  return (
    <>
      <p className="text-xs font-semibold uppercase tracking-wider text-white/50">
        Change{period ? ` · ${period}` : ''}
      </p>

      <div className="flex items-baseline gap-1.5">
        <span className={`text-4xl font-bold tabular-nums leading-none ${trendColor}`}>{primary.value}</span>
        <span className="text-sm text-white/70">{primary.label}</span>
      </div>

      {secondary.length > 0 && (
        <>
          <div className="h-px bg-white/10" />
          <div className="flex flex-col gap-1.5">
            {secondary.map((s) => (
              <div key={s.label} className="flex items-center justify-between text-sm">
                <span className="text-white/60">{s.label}</span>
                <span className={`font-medium tabular-nums ${s.color}`}>{s.value}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {chart && chart.length > 0 && chartMeta && (
        <>
          <div className="h-px bg-white/10" />
          <p className="text-[10px] font-semibold uppercase tracking-wider text-white/40">{chartMeta.label}</p>
          <div className="h-20">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chart} margin={{ top: 2, right: 4, bottom: 0, left: -28 }}>
                <XAxis
                  dataKey="t"
                  tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 9 }}
                  tickLine={false}
                  axisLine={false}
                  interval={tickInterval}
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
                  stroke={chartMeta.color}
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}

      <p className="text-[10px] text-white/30">
        MODIS · HLS · {status === 'live' ? 'live data' : 'no data'}
      </p>
    </>
  )
}
