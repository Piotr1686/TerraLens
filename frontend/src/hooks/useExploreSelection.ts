import { useEffect, useMemo, useState } from 'react'
import type { SceneList, SceneResult, Source } from '@/lib/mpc'

/** Próg „tylko bezchmurne" — sceny powyżej są ukrywane, gdy filtr aktywny. */
const CLEAR_THRESHOLD = 20

/**
 * Stan wyboru w trybie Explore nad listami scen: źródło (NAIP/S2), filtr chmur
 * i indeks daty. Zwraca przefiltrowaną listę `available` i wybraną `scene`.
 */
export function useExploreSelection(scenes: SceneList | null) {
  const [source, setSource] = useState<Source>('sentinel-2')
  const [clearOnly, setClearOnly] = useState(false)
  const [dateIndex, setDateIndex] = useState(0)

  const hasNaip = (scenes?.naip.length ?? 0) > 0
  const hasSentinel = (scenes?.['sentinel-2'].length ?? 0) > 0

  // Domyślne źródło po załadowaniu list: NAIP jeśli dostępny (lepsza jakość), inaczej S2.
  useEffect(() => {
    if (!scenes) return
    setSource(hasNaip ? 'naip' : 'sentinel-2')
    setDateIndex(0)
  }, [scenes]) // eslint-disable-line react-hooks/exhaustive-deps

  // Filtr chmur — NAIP nie ma chmur (cloudCover null) → zawsze przechodzi.
  const available = useMemo(() => {
    const list = scenes?.[source] ?? []
    if (!clearOnly) return list
    return list.filter((s) => s.cloudCover === null || s.cloudCover < CLEAR_THRESHOLD)
  }, [scenes, source, clearOnly])

  // Zmiana źródła lub filtra → wróć na najnowszą scenę (index 0).
  useEffect(() => {
    setDateIndex(0)
  }, [source, clearOnly])

  const clampedIndex = Math.min(dateIndex, Math.max(0, available.length - 1))
  const scene: SceneResult | null = available[clampedIndex] ?? null

  return {
    source,
    setSource,
    clearOnly,
    setClearOnly,
    dateIndex: clampedIndex,
    setDateIndex,
    available,
    scene,
    hasNaip,
    hasSentinel,
  }
}
