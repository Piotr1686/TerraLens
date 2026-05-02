import { useEffect } from 'react'
import type { TourStep } from '@/hooks/useTour'
import { TOUR_STEPS } from '@/hooks/useTour'

// Kroki z regionId (pomijamy krok 0 — widok globalny) do wyświetlenia jako dots
const REGION_STEPS = TOUR_STEPS.filter((s) => s.regionId !== null)

interface Props {
  isRunning: boolean
  isComplete: boolean
  stepIndex: number
  currentStep: TourStep | null
  onStop: () => void
  onReplay: () => void
}

export function GuidedTour({ isRunning, isComplete, stepIndex, onStop, onReplay }: Props) {
  // ESC przerywa tour
  useEffect(() => {
    if (!isRunning) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onStop()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isRunning, onStop])

  if (!isRunning && !isComplete) return null

  return (
    <div className="absolute top-4 left-1/2 z-20 -translate-x-1/2">
      {isRunning && (
        <div className="flex items-center gap-3 rounded-full bg-black/60 px-4 py-2 backdrop-blur">
          {/* Step dots dla kroków z regionami */}
          <div className="flex items-center gap-1.5">
            {REGION_STEPS.map((step, i) => {
              // TOUR_STEPS[0] to widok globalny, więc krok regionu i = TOUR_STEPS[i+1]
              const tourIdx = i + 1
              const isActive = stepIndex === tourIdx
              return (
                <span
                  key={step.regionId}
                  className={[
                    'block rounded-full transition-all duration-300',
                    isActive ? 'h-2 w-6 bg-white' : 'h-2 w-2 bg-white/40',
                  ].join(' ')}
                  title={step.label}
                />
              )
            })}
          </div>

          {/* Aktualny krok */}
          <span className="min-w-16 text-center text-xs font-medium text-white/80">
            {stepIndex === 0
              ? 'Starting...'
              : (TOUR_STEPS[stepIndex]?.label ?? '')}
          </span>

          {/* Przerwij (klik lub ESC) */}
          <button
            onClick={onStop}
            className="rounded-full bg-white/10 px-3 py-0.5 text-xs text-white/60 hover:bg-white/20 hover:text-white transition-colors"
            title="Stop (ESC)"
          >
            ✕ Stop
          </button>
        </div>
      )}

      {isComplete && (
        <button
          onClick={onReplay}
          className="flex items-center gap-1.5 rounded-full bg-black/60 px-4 py-2 text-sm font-medium text-white backdrop-blur hover:bg-black/80 transition-colors"
        >
          <span>↺</span>
          <span>Replay</span>
        </button>
      )}
    </div>
  )
}
