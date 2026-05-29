import { useEffect, useMemo, useState } from 'react'
import { Slider } from '@/components/ui/slider'

interface Props {
  dates: string[]
  dateIndex: number
  onDateChange: (index: number) => void
  showPlay?: boolean
}

function formatDate(dateStr: string): string {
  const [year, month] = dateStr.split('-')
  const monthNames = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
  return `${monthNames[parseInt(month, 10) - 1]} ${year}`
}

const FRAME_MS = 900 // tempo timelapse — ~1.1 klatki/s, daje czas na doczytanie kafli

// Klatki roczne: lipiec każdego roku (najlepsze pokrycie MODIS, brak nocy polarnej),
// fallback na pierwszą dostępną datę roku. Mniej klatek = mniej przeładowań tekstury.
function buildYearlyFrames(dates: string[]): number[] {
  const byYear = new Map<string, { idx: number; july: number | null }>()
  dates.forEach((d, i) => {
    const year = d.slice(0, 4)
    const isJuly = d.slice(5, 7) === '07'
    const cur = byYear.get(year)
    if (!cur) byYear.set(year, { idx: i, july: isJuly ? i : null })
    else if (isJuly && cur.july === null) cur.july = i
  })
  return Array.from(byYear.values()).map((v) => v.july ?? v.idx)
}

export function Timeline({ dates, dateIndex, onDateChange, showPlay = false }: Props) {
  const [playing, setPlaying] = useState(false)
  const playFrames = useMemo(() => buildYearlyFrames(dates), [dates])

  // Powrót do widoku globalnego (znika przycisk) → zatrzymaj odtwarzanie.
  useEffect(() => {
    if (!showPlay) setPlaying(false)
  }, [showPlay])

  // Auto-przewijanie po klatkach rocznych z zapętleniem. Interval re-armowany
  // przy każdej zmianie dateIndex (czyta świeżą pozycję).
  useEffect(() => {
    if (!playing || playFrames.length < 2) return
    const id = setTimeout(() => {
      const next = playFrames.find((i) => i > dateIndex) ?? playFrames[0]
      onDateChange(next)
    }, FRAME_MS)
    return () => clearTimeout(id)
  }, [playing, dateIndex, playFrames, onDateChange])

  if (dates.length === 0) return null

  const firstYear = dates[0].slice(0, 4)
  const lastYear = dates[dates.length - 1].slice(0, 4)

  const togglePlay = () => {
    if (!playing) onDateChange(playFrames[0] ?? 0) // start od pierwszego roku
    setPlaying((p) => !p)
  }

  return (
    <div className="absolute bottom-20 left-1/2 w-[min(600px,90vw)] -translate-x-1/2 rounded-xl bg-black/50 px-5 py-4 backdrop-blur">
      <div className="mb-3 flex items-center justify-between text-xs text-white/50">
        <span>{firstYear}</span>
        <span className="text-base font-semibold text-white">{formatDate(dates[dateIndex])}</span>
        <span>{lastYear}</span>
      </div>
      <div className="flex items-center gap-3">
        {showPlay && (
          <button
            onClick={togglePlay}
            aria-label={playing ? 'Pause timelapse' : 'Play timelapse'}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10 text-white transition-colors hover:bg-amber-500/70"
          >
            {playing ? (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <rect x="6" y="5" width="4" height="14" rx="1" />
                <rect x="14" y="5" width="4" height="14" rx="1" />
              </svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M7 5l12 7-12 7V5z" />
              </svg>
            )}
          </button>
        )}
        <Slider
          min={0}
          max={dates.length - 1}
          step={1}
          value={[dateIndex]}
          onValueChange={(v) => {
            setPlaying(false)
            onDateChange(Array.isArray(v) ? v[0] : (v as number))
          }}
          className="w-full"
        />
      </div>
    </div>
  )
}
