import { useCallback, useRef, useState } from 'react'
import { Sparkles } from 'lucide-react'

// Para kafli demo per region (raw GIBS HLS ↔ AI Super-Resolution 4× Real-ESRGAN).
// Assety bundlowane w public/sr-demo/. Tylko regiony z gotową parą mają wpis.
const SR_PAIRS: Record<string, { raw: string; sr: string; place: string }> = {
  dubai: {
    raw: '/sr-demo/dubai-raw.jpg',
    sr: '/sr-demo/dubai-sr.webp',
    place: 'Wybrzeże Zatoki Perskiej',
  },
}

interface SuperResPanelProps {
  regionId: string | null
}

// Panel „AI Super-Resolution" po przylocie — suwak before/after raw↔SR.
// Górna warstwa (SR) przycinana clip-path wg pozycji dzielnika; pod spodem raw.
export function SuperResPanel({ regionId }: SuperResPanelProps) {
  const pair = regionId ? SR_PAIRS[regionId] : null
  const [pos, setPos] = useState(50) // pozycja dzielnika w %
  const containerRef = useRef<HTMLDivElement>(null)
  const draggingRef = useRef(false)

  const updateFromClientX = useCallback((clientX: number) => {
    const el = containerRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const pct = ((clientX - rect.left) / rect.width) * 100
    setPos(Math.max(0, Math.min(100, pct)))
  }, [])

  const onPointerDown = useCallback(
    (e: React.PointerEvent) => {
      draggingRef.current = true
      ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
      updateFromClientX(e.clientX)
    },
    [updateFromClientX],
  )

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!draggingRef.current) return
      updateFromClientX(e.clientX)
    },
    [updateFromClientX],
  )

  const onPointerUp = useCallback((e: React.PointerEvent) => {
    draggingRef.current = false
    ;(e.target as HTMLElement).releasePointerCapture?.(e.pointerId)
  }, [])

  if (!pair) return null

  return (
    <div className="absolute left-4 top-4 z-10 w-72 rounded-xl border border-white/10 bg-black/40 p-3 backdrop-blur-md">
      <div className="mb-2 flex items-center gap-2 text-xs font-medium text-white/70">
        <Sparkles className="h-4 w-4 text-cyan-400" />
        AI Super-Resolution
      </div>

      <div
        ref={containerRef}
        className="relative aspect-square w-full cursor-ew-resize select-none overflow-hidden rounded-lg"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
      >
        {/* Spód: RAW */}
        <img
          src={pair.raw}
          alt="RAW (GIBS HLS)"
          draggable={false}
          className="absolute inset-0 h-full w-full object-cover"
        />
        {/* Wierzch: SR — przycięty od lewej do pozycji dzielnika */}
        <img
          src={pair.sr}
          alt="AI Super-Resolution 4×"
          draggable={false}
          className="absolute inset-0 h-full w-full object-cover"
          style={{ clipPath: `inset(0 ${100 - pos}% 0 0)` }}
        />

        {/* Etykiety */}
        <span className="absolute bottom-1.5 left-1.5 rounded bg-black/60 px-1.5 py-0.5 text-[9px] font-semibold tracking-wide text-cyan-300">
          AI SR 4×
        </span>
        <span className="absolute bottom-1.5 right-1.5 rounded bg-black/60 px-1.5 py-0.5 text-[9px] font-semibold tracking-wide text-white/70">
          RAW
        </span>

        {/* Linia dzielnika + uchwyt */}
        <div
          className="pointer-events-none absolute inset-y-0 w-0.5 bg-white/90 shadow-[0_0_8px_rgba(0,0,0,0.6)]"
          style={{ left: `${pos}%` }}
        >
          <div className="absolute top-1/2 left-1/2 flex h-6 w-6 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-white/80 bg-black/50 text-[10px] text-white">
            ⇆
          </div>
        </div>
      </div>

      <div className="mt-2 text-[10px] leading-tight text-white/50">
        Real-ESRGAN 4× · {pair.place}
      </div>
    </div>
  )
}
