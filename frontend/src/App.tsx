import { useCallback, useEffect, useState } from 'react'
import { Globe } from '@/components/Globe'
import { Timeline } from '@/components/Timeline'
import { HeatmapControls } from '@/components/HeatmapControls'
import { StatsPanel } from '@/components/StatsPanel'
import { GuidedTour } from '@/components/GuidedTour'
import { Preloader } from '@/components/Preloader'
import { useTimeline } from '@/hooks/useTimeline'
import { useHeatmapLayer } from '@/hooks/useHeatmapLayer'
import { useTour } from '@/hooks/useTour'
import { usePreload } from '@/hooks/usePreload'
import { useRevealOpacity } from '@/hooks/useRevealOpacity'
import { useMediaQuery } from '@/hooks/useMediaQuery'
import type { HeatmapMetric } from '@/hooks/useHeatmapLayer'

function App() {
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null)
  const [arrivedRegion, setArrivedRegion] = useState<string | null>(null)
  const [manifestTimeline, setManifestTimeline] = useState<string[] | undefined>()
  const [heatmapMetric, setHeatmapMetric] = useState<HeatmapMetric>('ndvi')
  const [heatmapOpacity, setHeatmapOpacity] = useState(0.6)

  const isMobile = useMediaQuery('(max-width: 768px)')
  const fps = isMobile ? 30 : 60

  const { progress, label, isReady, manifest, hasPreview } = usePreload()

  // Tour startuje dopiero po zakończeniu preloadera
  const { isRunning, isComplete, stepIndex, currentStep, stop, replay } = useTour({ enabled: isReady })

  // Manifest z usePreload → timeline
  useEffect(() => {
    if (!manifest) return
    const m = manifest as { timeline?: string[] }
    if (Array.isArray(m?.timeline)) setManifestTimeline(m.timeline)
  }, [manifest])

  // Synchronizacja selectedRegion z aktywnym krokiem trasy
  useEffect(() => {
    if (!isRunning) return
    setSelectedRegion(currentStep?.regionId ?? null)
  }, [currentStep, isRunning])

  // Nowy lot (selectedRegion zmienia się) → chowamy heatmapę; pokaże się po arrival
  useEffect(() => {
    setArrivedRegion(null)
  }, [selectedRegion])

  // Kliknięcie markera przez usera przerywa tour
  const handleRegionSelect = useCallback(
    (regionId: string | null) => {
      if (isRunning) stop()
      setSelectedRegion(regionId)
    },
    [isRunning, stop],
  )

  // Globe wywołuje po wylądowaniu kamery → trigger dla reveal animacji
  const handleRegionArrival = useCallback((regionId: string) => {
    setArrivedRegion(regionId)
  }, [])

  const revealFraction = useRevealOpacity(arrivedRegion, 600, fps)

  const { dates, dateIndex, currentDate, tileUrl, setDateIndex } = useTimeline(manifestTimeline)

  const heatmapLayer = useHeatmapLayer({
    region: arrivedRegion,
    metric: heatmapMetric,
    opacity: heatmapOpacity * revealFraction,
    currentDate,
  })

  const flyTarget = isRunning ? (currentStep?.regionId ?? null) : undefined

  return (
    <div className="h-full w-full">
      <Globe
        tileUrl={tileUrl}
        extraLayers={heatmapLayer ? [heatmapLayer] : []}
        flyTarget={flyTarget}
        onRegionSelect={handleRegionSelect}
        onRegionArrival={handleRegionArrival}
        fps={fps}
      />
      <GuidedTour
        isRunning={isRunning}
        isComplete={isComplete}
        stepIndex={stepIndex}
        currentStep={currentStep}
        onStop={stop}
        onReplay={replay}
      />
      <Timeline dates={dates} dateIndex={dateIndex} onDateChange={setDateIndex} />
      <HeatmapControls
        metric={heatmapMetric}
        opacity={heatmapOpacity}
        onMetricChange={setHeatmapMetric}
        onOpacityChange={setHeatmapOpacity}
      />
      <StatsPanel regionId={selectedRegion} dateIndex={dateIndex} />
      <Preloader progress={progress} label={label} isReady={isReady} hasPreview={hasPreview} />
    </div>
  )
}

export default App
