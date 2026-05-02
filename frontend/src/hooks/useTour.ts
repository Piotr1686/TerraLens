import { useCallback, useEffect, useRef, useState } from 'react'

export interface TourStep {
  regionId: string | null  // null = widok globalny
  duration: number         // ms na tym kroku
  label: string
}

// Stała sekwencja trasy — Bezier camera path w useCinematicFlight.ts
export const TOUR_STEPS: TourStep[] = [
  { regionId: null,       duration: 2000, label: 'Widok globalny' },
  { regionId: 'amazonia', duration: 4000, label: 'Amazonia'       },
  { regionId: 'dubai',    duration: 4000, label: 'Dubai'          },
  { regionId: 'arctic',   duration: 4000, label: 'Arktyka'        },
]

export interface UseTourReturn {
  isRunning: boolean
  isComplete: boolean
  stepIndex: number        // -1 gdy nie uruchomiony lub zakończony
  steps: TourStep[]
  currentStep: TourStep | null
  start: () => void
  stop: () => void
  replay: () => void
}

export function useTour({ enabled = true }: { enabled?: boolean } = {}): UseTourReturn {
  const [isRunning, setIsRunning] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [stepIndex, setStepIndex] = useState(-1)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const runStep = useCallback(
    (idx: number) => {
      if (idx >= TOUR_STEPS.length) {
        setIsRunning(false)
        setIsComplete(true)
        setStepIndex(-1)
        return
      }
      setStepIndex(idx)
      timerRef.current = setTimeout(() => runStep(idx + 1), TOUR_STEPS[idx].duration)
    },
    // runStep rekuruje przez timerRef — brak zewnętrznych deps
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  const start = useCallback(() => {
    clearTimer()
    setIsComplete(false)
    setIsRunning(true)
    runStep(0)
  }, [clearTimer, runStep])

  const stop = useCallback(() => {
    clearTimer()
    setIsRunning(false)
    setStepIndex(-1)
  }, [clearTimer])

  const replay = useCallback(() => {
    clearTimer()
    setIsComplete(false)
    setIsRunning(true)
    // jeden RAF żeby React zdążył zaktualizować stan przed runStep
    requestAnimationFrame(() => runStep(0))
  }, [clearTimer, runStep])

  // Start gdy enabled zmieni się na true (po zakończeniu preloadera)
  useEffect(() => {
    if (!enabled) return
    start()
    return clearTimer
  }, [enabled]) // eslint-disable-line react-hooks/exhaustive-deps

  const currentStep = stepIndex >= 0 ? TOUR_STEPS[stepIndex] : null

  return { isRunning, isComplete, stepIndex, steps: TOUR_STEPS, currentStep, start, stop, replay }
}
