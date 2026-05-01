import { useEffect, useState } from 'react'

interface Props {
  progress: number
  label: string
  isReady: boolean
  hasPreview: boolean
}

export function Preloader({ progress, label, isReady, hasPreview }: Props) {
  const [mounted, setMounted] = useState(true)
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    if (!isReady) return
    setVisible(false)
    const t = setTimeout(() => setMounted(false), 600)
    return () => clearTimeout(t)
  }, [isReady])

  if (!mounted) return null

  return (
    <div
      className={[
        'fixed inset-0 z-50 flex flex-col items-center justify-center',
        'transition-opacity duration-600',
        visible ? 'opacity-100' : 'opacity-0',
      ].join(' ')}
      style={{
        background: hasPreview
          ? 'url(/amazonia_preview.jpg) center/cover no-repeat'
          : 'radial-gradient(ellipse at 40% 60%, #1a2e1a 0%, #0a0f0a 60%, #050805 100%)',
      }}
    >
      {/* Ciemna nakładka nad podglądem */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

      {/* Treść */}
      <div className="relative z-10 flex w-full max-w-sm flex-col items-center gap-8 px-8">
        {/* Logo + tytuł */}
        <div className="flex flex-col items-center gap-2 text-center">
          <div className="text-5xl">🌍</div>
          <h1 className="text-3xl font-bold tracking-tight text-white">TerraLens</h1>
          <p className="text-sm text-white/50">Interaktywny eksplorator zmian powierzchni Ziemi</p>
        </div>

        {/* Progress */}
        <div className="w-full space-y-3">
          {/* Bar */}
          <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-white/10">
            <div
              className="absolute inset-y-0 left-0 rounded-full bg-emerald-400 transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Etykiety */}
          <div className="flex items-center justify-between text-xs">
            <span className="text-white/50">{label}</span>
            <span className="tabular-nums text-white/70">{progress}%</span>
          </div>
        </div>

        {/* Pulsujący punkt ładowania */}
        {!isReady && (
          <div className="flex gap-1.5">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="block h-1.5 w-1.5 animate-pulse rounded-full bg-white/30"
                style={{ animationDelay: `${i * 200}ms` }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
