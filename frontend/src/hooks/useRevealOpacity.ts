import { useEffect, useRef, useState } from 'react'

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3)
}

// Animuje fraction 0→1 gdy trigger staje się non-null, reset do 0 gdy null
export function useRevealOpacity(trigger: string | null, duration = 600, fps = 60): number {
  const [fraction, setFraction] = useState(0)
  const rafRef = useRef<number | null>(null)
  const fpsRef = useRef(fps)

  // Aktualizacja fps w efekcie (nie podczas renderu) — tick zawsze widzi aktualną wartość
  useEffect(() => {
    fpsRef.current = fps
  }, [fps])

  useEffect(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
    if (!trigger) {
      setFraction(0)
      return
    }
    setFraction(0)
    const startTime = performance.now()
    let lastFrameTime = 0

    const tick = (now: number) => {
      const t = Math.min((now - startTime) / duration, 1)
      const isFinal = t >= 1
      const minFrameMs = 1000 / fpsRef.current
      if (isFinal || now - lastFrameTime >= minFrameMs) {
        lastFrameTime = now
        setFraction(easeOutCubic(t))
      }
      if (!isFinal) rafRef.current = requestAnimationFrame(tick)
      else rafRef.current = null
    }
    rafRef.current = requestAnimationFrame(tick)

    return () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current)
        rafRef.current = null
      }
    }
  }, [trigger, duration])

  return fraction
}
