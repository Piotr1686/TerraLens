import { useEffect, useRef, useState } from 'react'
import { Search, X, Loader2 } from 'lucide-react'
import { geocode } from '@/lib/geocode'
import type { GeocodeResult } from '@/lib/geocode'

interface Props {
  /** Wywołane po wyborze trafienia — wejście w tryb Explore nad punktem. */
  onSelect: (result: GeocodeResult) => void
  /** Wyjście z trybu Explore (czyszczenie). */
  onClear: () => void
  /** Czy tryb Explore jest aktywny (steruje przyciskiem zamknięcia). */
  active?: boolean
}

export function SearchBox({ onSelect, onClear, active }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<GeocodeResult[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)

  // Debounce + abort — Nominatim ToS ≤1 req/s, więc 600 ms.
  useEffect(() => {
    const q = query.trim()
    if (q.length < 3) {
      setResults([])
      setLoading(false)
      return
    }
    const ctrl = new AbortController()
    setLoading(true)
    const t = setTimeout(() => {
      geocode(q, { signal: ctrl.signal })
        .then((r) => {
          setResults(r)
          setOpen(true)
        })
        .catch((err) => {
          if (!ctrl.signal.aborted) console.error('geocode:', err)
        })
        .finally(() => {
          if (!ctrl.signal.aborted) setLoading(false)
        })
    }, 600)
    return () => {
      clearTimeout(t)
      ctrl.abort()
    }
  }, [query])

  const inputRef = useRef<HTMLInputElement>(null)

  const handlePick = (r: GeocodeResult) => {
    setQuery(r.label.split(',')[0])
    setResults([])
    setOpen(false)
    inputRef.current?.blur()
    onSelect(r)
  }

  const handleClear = () => {
    setQuery('')
    setResults([])
    setOpen(false)
    onClear()
  }

  return (
    <div className="absolute left-4 top-4 w-72">
      <div className="flex items-center gap-2 rounded-xl bg-black/50 px-3 py-2 backdrop-blur">
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin text-white/50" />
        ) : (
          <Search className="h-4 w-4 text-white/50" />
        )}
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length > 0 && setOpen(true)}
          placeholder="Search any place…"
          className="flex-1 bg-transparent text-sm text-white placeholder:text-white/40 focus:outline-none"
        />
        {(query || active) && (
          <button onClick={handleClear} aria-label="Clear search">
            <X className="h-4 w-4 text-white/50 transition-colors hover:text-white" />
          </button>
        )}
      </div>

      {open && results.length > 0 && (
        <ul className="mt-2 max-h-64 overflow-y-auto rounded-xl bg-black/70 backdrop-blur">
          {results.map((r, i) => (
            <li key={`${r.lon},${r.lat},${i}`}>
              <button
                onClick={() => handlePick(r)}
                className="block w-full px-3 py-2 text-left text-xs text-white/80 transition-colors hover:bg-white/10"
              >
                {r.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
