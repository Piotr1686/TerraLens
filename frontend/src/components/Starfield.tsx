import { useEffect, useRef } from 'react'

// Pole gwiazd + poświata atmosfery — czysty canvas, bez zależności 3D.
// Renderowane jako tło ZA przezroczystym canvasem deck.gl (obszar poza kulą globu).

interface Star {
  x: number // frakcja 0..1
  y: number // frakcja 0..1
  r: number // promień px
  base: number // bazowa jasność 0..1
  twPhase: number // faza migotania
  twSpeed: number // prędkość migotania
}

const STAR_COUNT = 180

function makeStars(): Star[] {
  const stars: Star[] = []
  for (let i = 0; i < STAR_COUNT; i++) {
    stars.push({
      x: Math.random(),
      y: Math.random(),
      r: Math.random() * 1.2 + 0.3,
      base: Math.random() * 0.5 + 0.4,
      twPhase: Math.random() * Math.PI * 2,
      twSpeed: Math.random() * 1.5 + 0.5,
    })
  }
  return stars
}

export function Starfield() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const starsRef = useRef<Star[]>(makeStars())

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    let rafId = 0
    let w = 0
    let h = 0

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      w = window.innerWidth
      h = window.innerHeight
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    window.addEventListener('resize', resize)

    const draw = (now: number) => {
      ctx.clearRect(0, 0, w, h)
      const t = now / 1000
      for (const s of starsRef.current) {
        // Powolny parallax dryf — gwiazdy lekko wędrują w prawo i zawijają się.
        const driftX = reduceMotion ? 0 : (t * 0.0015) % 1
        const px = ((s.x + driftX) % 1) * w
        const py = s.y * h
        const tw = reduceMotion ? 1 : 0.6 + 0.4 * Math.sin(s.twPhase + t * s.twSpeed)
        const alpha = s.base * tw
        ctx.globalAlpha = alpha
        ctx.fillStyle = '#ffffff'
        ctx.beginPath()
        ctx.arc(px, py, s.r, 0, Math.PI * 2)
        ctx.fill()
      }
      ctx.globalAlpha = 1
      if (!reduceMotion) rafId = requestAnimationFrame(draw)
    }

    rafId = requestAnimationFrame(draw)

    return () => {
      cancelAnimationFrame(rafId)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return (
    <div className="pointer-events-none absolute inset-0 bg-black">
      {/* Gwiazdy */}
      <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" />
      {/* Poświata atmosfery — miękki błękit za kulą globu (widok planetarny) */}
      <div
        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
        style={{
          width: 'min(95vh, 95vw)',
          height: 'min(95vh, 95vw)',
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(80,140,220,0.18) 38%, rgba(60,120,200,0.10) 50%, rgba(40,90,160,0.04) 60%, transparent 68%)',
          filter: 'blur(8px)',
        }}
      />
    </div>
  )
}
