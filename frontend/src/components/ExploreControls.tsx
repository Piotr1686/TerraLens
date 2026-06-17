import { Slider } from '@/components/ui/slider'
import type { SceneResult, Source } from '@/lib/mpc'

interface Props {
  source: Source
  onSourceChange: (s: Source) => void
  hasNaip: boolean
  clearOnly: boolean
  onClearOnlyChange: (v: boolean) => void
  /** Przefiltrowana lista scen (datą desc — index 0 = najnowsza). */
  available: SceneResult[]
  /** Indeks wybranej sceny w `available`. */
  dateIndex: number
  onDateIndexChange: (i: number) => void
}

function fmt(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' })
}

const SOURCE_LABEL: Record<Source, string> = { naip: 'NAIP 0.6 m', 'sentinel-2': 'Sentinel-2 10 m' }

export function ExploreControls({
  source,
  onSourceChange,
  hasNaip,
  clearOnly,
  onClearOnlyChange,
  available,
  dateIndex,
  onDateIndexChange,
}: Props) {
  const count = available.length
  const scene = available[dateIndex] ?? null
  // Suwak: lewo = najstarsze, prawo = najnowsze. Lista jest desc → odwracamy mapowanie.
  const sliderValue = count > 0 ? count - 1 - dateIndex : 0

  const srcBtn = (s: Source, disabled = false) => (
    <button
      onClick={() => !disabled && onSourceChange(s)}
      disabled={disabled}
      title={disabled ? 'Dostępne tylko nad USA' : undefined}
      className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
        source === s
          ? 'bg-amber-500/70 text-white ring-1 ring-amber-300'
          : disabled
            ? 'cursor-not-allowed bg-white/5 text-white/30'
            : 'bg-white/10 text-white hover:bg-white/20'
      }`}
    >
      {SOURCE_LABEL[s]}
    </button>
  )

  return (
    <div className="absolute bottom-24 left-1/2 w-[min(640px,92vw)] -translate-x-1/2 rounded-xl bg-black/50 px-5 py-4 backdrop-blur">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex gap-2">
          {srcBtn('naip', !hasNaip)}
          {srcBtn('sentinel-2')}
        </div>
        <button
          onClick={() => onClearOnlyChange(!clearOnly)}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
            clearOnly ? 'bg-sky-500/70 text-white ring-1 ring-sky-300' : 'bg-white/10 text-white hover:bg-white/20'
          }`}
        >
          {clearOnly ? '☀ Clear skies only' : '☁ All dates'}
        </button>
      </div>

      <div className="mb-2 text-center">
        {scene ? (
          <span className="text-base font-semibold text-white">
            {fmt(scene.datetime)}
            {scene.cloudCover !== null && (
              <span className="ml-2 text-xs font-normal text-white/50">{scene.cloudCover.toFixed(0)}% cloud</span>
            )}
          </span>
        ) : (
          <span className="text-sm text-white/50">No scenes for this filter</span>
        )}
      </div>

      <div className="flex items-center gap-3 text-[10px] text-white/40">
        <span>{count > 0 ? fmt(available[count - 1].datetime).slice(-4) : ''}</span>
        <Slider
          min={0}
          max={Math.max(0, count - 1)}
          step={1}
          value={[sliderValue]}
          onValueChange={(v) => {
            const sv = Array.isArray(v) ? v[0] : (v as number)
            onDateIndexChange(count - 1 - sv)
          }}
          className="w-full"
          disabled={count < 2}
        />
        <span>{count > 0 ? fmt(available[0].datetime).slice(-4) : ''}</span>
      </div>
    </div>
  )
}
