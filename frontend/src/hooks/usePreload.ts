import { useEffect, useRef, useState } from 'react'

const HF_MANIFEST_URL =
  'https://huggingface.co/datasets/Piotr1686/terralens-data/resolve/main/manifest.json'

// Jeden kafelek Blue Marble (zoom 0) — trafia do cache przeglądarki zanim TileLayer go poprosi
const BLUE_MARBLE_TILE_0 =
  'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_NextGeneration/default/GoogleMapsCompatible_Level8/0/0/0.jpg'

// Statyczny podgląd Amazonii wyświetlany w tle Preloadera podczas ładowania
// Plik: frontend/public/amazonia_preview.jpg — brak pliku = gradient CSS jako fallback
const AMAZONIA_PREVIEW = '/amazonia_preview.jpg'

// Minimalna długość wyświetlania loadera — żeby nie migał przy szybkim połączeniu
const MIN_DISPLAY_MS = 1200

function preloadImage(src: string): Promise<void> {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => resolve()
    img.onerror = () => resolve()  // degradacja — błąd nie blokuje dalszego ładowania
    img.src = src
  })
}

export interface PreloadState {
  progress: number     // 0–100
  label: string        // opis aktualnie ładowanego zasobu
  isReady: boolean     // true gdy wszystko załadowane + minimalny czas minął
  manifest: unknown    // wynik fetch manifest.json lub null
  hasPreview: boolean  // true gdy amazonia_preview.jpg załadował się poprawnie
}

export function usePreload(): PreloadState {
  const [progress, setProgress] = useState(0)
  const [label, setLabel] = useState('Initialising...')
  const [isReady, setIsReady] = useState(false)
  const [manifest, setManifest] = useState<unknown>(null)
  const [hasPreview, setHasPreview] = useState(false)
  const ran = useRef(false)

  useEffect(() => {
    if (ran.current) return
    ran.current = true

    const startTime = Date.now()
    const total = 3
    let done = 0

    const tick = (nextLabel: string) => {
      done++
      setProgress(Math.round((done / total) * 100))
      setLabel(nextLabel)
      if (done === total) {
        // Poczekaj na MIN_DISPLAY_MS zanim ukryjesz loader
        const elapsed = Date.now() - startTime
        const remaining = Math.max(0, MIN_DISPLAY_MS - elapsed)
        setTimeout(() => setIsReady(true), remaining)
      }
    }

    // Krok 1: manifest danych
    setLabel('Data manifest...')
    fetch(HF_MANIFEST_URL)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) setManifest(data)
        tick('Globe textures...')
      })
      .catch(() => tick('Globe textures...'))

    // Krok 2: tekstura Blue Marble (zoom 0)
    preloadImage(BLUE_MARBLE_TILE_0).then(() => tick('Region preview...'))

    // Krok 3: podgląd Amazonii
    new Promise<void>((resolve) => {
      const img = new Image()
      img.onload = () => { setHasPreview(true); resolve() }
      img.onerror = () => resolve()
      img.src = AMAZONIA_PREVIEW
    }).then(() => tick('Ready'))
  }, [])

  return { progress, label, isReady, manifest, hasPreview }
}
