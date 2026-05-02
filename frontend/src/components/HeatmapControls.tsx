import { Slider } from '@/components/ui/slider'
import type { HeatmapMetric } from '@/hooks/useHeatmapLayer'

const METRICS: { id: HeatmapMetric; label: string; color: string }[] = [
  { id: 'ssim', label: 'SSIM', color: 'bg-blue-500/70 ring-blue-400' },
  { id: 'ndvi', label: 'NDVI', color: 'bg-green-500/70 ring-green-400' },
  { id: 'cva', label: 'CVA', color: 'bg-orange-500/70 ring-orange-400' },
]

interface Props {
  metric: HeatmapMetric
  opacity: number
  onMetricChange: (m: HeatmapMetric) => void
  onOpacityChange: (v: number) => void
}

export function HeatmapControls({ metric, opacity, onMetricChange, onOpacityChange }: Props) {
  return (
    <div className="absolute right-4 top-4 flex flex-col gap-3 rounded-xl bg-black/50 p-4 backdrop-blur w-44">
      <p className="text-xs font-semibold uppercase tracking-wider text-white/50">Heatmapa</p>

      <div className="flex flex-col gap-1.5">
        {METRICS.map((m) => (
          <button
            key={m.id}
            onClick={() => onMetricChange(m.id)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium text-white transition-colors ${
              metric === m.id ? `${m.color} ring-1` : 'bg-white/10 hover:bg-white/20'
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      <div className="space-y-1.5">
        <div className="flex justify-between text-xs text-white/50">
          <span>Opacity</span>
          <span>{Math.round(opacity * 100)}%</span>
        </div>
        <Slider
          min={0}
          max={1}
          step={0.05}
          value={[opacity]}
          onValueChange={(v) => onOpacityChange(Array.isArray(v) ? v[0] : (v as number))}
        />
      </div>
    </div>
  )
}
